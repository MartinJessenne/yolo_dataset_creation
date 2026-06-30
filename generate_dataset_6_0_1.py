# generate_dataset_6_0_1.py
# Multi-class synthetic dataset generation using Omniverse Replicator
# Generates YOLO26-seg training data with three cart types (picanol, colruyt, leanflow)
# across multiple warehouse scenes with shuffled cross-scene consolidation.
# Updated for Isaac Sim 6.0.1+ (Functional API & isaacsim namespace)

import os
import sys
import math
import json

# ─── Pre-SimulationApp Environment Configuration ───────────────────────────
os.environ["OMNICLIENT_HUB_MODE"] = "disabled"
os.environ["OMNICLIENT_USE_HUB"] = "0"

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Disable RTX driver verification for daman host compatibility
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

# Verbose logging for debugging headless Vulkan/denoiser initialization
sys.argv.append("--/log/level=verbose")
sys.argv.append("--/log/consoleLogLevel=verbose")
sys.argv.append("--/log/fileLogLevel=verbose")

# Force RTX Real-Time 2.0 ray-tracing renderer
sys.argv.append("--/rtx/rendermode=RayTracedLighting")

# ─── Parse CLI Arguments ───────────────────────────────────────────────────
NUM_FRAMES = 5  # default for validation runs
if "--frames" in sys.argv:
    try:
        idx = sys.argv.index("--frames")
        if idx + 1 < len(sys.argv):
            NUM_FRAMES = int(sys.argv[idx + 1])
        sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
    except ValueError:
        pass

# ─── Start SimulationApp ──────────────────────────────────────────────────
# MIGRATION 6.0: omni.isaac.kit -> isaacsim
from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True, "renderer": "RayTracedLighting"})


# ─── Omniverse Imports ────────────────────────────────────────────────────
import omni.usd
import omni.replicator.core as rep

# MIGRATION 6.0: omni.isaac.core.utils -> isaacsim.core.utils
from isaacsim.core.experimental.utils.semantics import add_labels, upgrade_prim_semantics_to_labels
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.storage.native import get_assets_root_path

from isaacsim.sensors.experimental.rtx import RtxCamera, SingleViewDepthCameraSensor

from omni.replicator.core import Writer, WriterRegistry, AnnotatorRegistry
from pxr import Sdf, UsdShade, Usd
import numpy as np
from PIL import Image

# ─── Constants ─────────────────────────────────────────────────────────────

# Cart USD asset paths
CART_USD_PATHS = {
    "picanol":  os.path.abspath("./meshes/picanolcart.usdc"),
    "colruyt":  os.path.abspath("./meshes/colruyt.usdc"),
    "leanflow": os.path.abspath("./meshes/leanflow.usdc"),
}
CART_TYPES = list(CART_USD_PATHS.keys())

# Multi-class mapping: class name -> integer ID
CLASS_MAPPING = {"picanol": 0, "colruyt": 1, "leanflow": 2}

# Semantic mask colors per class (for colorized PNG output)
SEMANTIC_COLORS = {
    0: (220, 50, 50),    # picanol  - red
    1: (50, 200, 50),    # colruyt  - green
    2: (50, 100, 220),   # leanflow - blue
}

# Verify all USD assets exist
for name, path in CART_USD_PATHS.items():
    if not os.path.exists(path):
        print(f"\nERROR: USD model not found: {path}")
        print("Please ensure all cart USD files are in the meshes/ directory.")
        simulation_app.close()
        exit(1)
    print(f">>> Verified USD asset: {name} -> {path}")

# Warehouse environments for scene diversity
assets_root = get_assets_root_path()
ISAAC_ASSETS = f"{assets_root}/Isaac" if assets_root else \
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac"

WAREHOUSE_SCENES = [
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse_with_forklifts.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse_multiple_shelves.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/full_warehouse.usd",
]

# Camera geometry (D455 RealSense matching)
# Render: 1280×800 landscape with 90° roll to match physical sensor rotation.
# Intrinsics target: f_pixel = 639.99768 px on 1280 px width.
CAMERA_HEIGHT = 0.304       # meters (URDF base_link -> camera_link Z offset)
TILT_ANGLE = 30.0           # degrees
HORIZ_APERTURE = 20.955     # mm (standard sensor aperture)
FOCAL_LENGTH = 639.99768 * HORIZ_APERTURE / 1280  # ≈ 10.4775 mm

# Collision geometry
CART_BODY_OFFSET = 0.8      # meters behind front-center to approximate body center
CART_CLEARANCE = 1.2        # meters radius around body center for distractor clearance

# Box appearance: solid diffuse colors for leanflow occlusion props
BOX_COLORS = [
    (0.55, 0.35, 0.17),  # cardboard brown
    (0.65, 0.65, 0.65),  # plastic grey
    (0.72, 0.53, 0.26),  # wood/tan
    (0.4, 0.2, 0.1),     # dark brown
    (0.8, 0.8, 0.75),    # off-white
    (0.3, 0.3, 0.35),    # dark grey
]

# Output directory
OUTPUT_DIR = os.path.abspath("./_output_dataset_multi_cart")


# ═══════════════════════════════════════════════════════════════════════════
# Custom Writer: Multi-Class MultiModalRawWriter
# ═══════════════════════════════════════════════════════════════════════════

class MultiModalRawWriter(Writer):
    def __init__(self, output_dir: str = None, **kwargs):
        super().__init__()
        self._frame_id = 0

        # Register annotators
        self.annotators.append(AnnotatorRegistry.get_annotator("rgb"))
        self.annotators.append(AnnotatorRegistry.get_annotator(
            "semantic_segmentation", init_params={"colorize": False}
        ))
        self.annotators.append(AnnotatorRegistry.get_annotator("distance_to_image_plane"))
        self.annotators.append(AnnotatorRegistry.get_annotator("bounding_box_3d"))
        self.annotators.append(AnnotatorRegistry.get_annotator("camera_params"))

    def initialize(self, output_dir: str, **kwargs):
        self._output_dir = output_dir
        self._frame_id = 0

        self.rgb_dir = os.path.join(output_dir, "rgb")
        self.depth_dir = os.path.join(output_dir, "depth")
        self.sem_dir = os.path.join(output_dir, "semantic")
        self.sem_labels_dir = os.path.join(output_dir, "semantic_labels")
        self.bbox_3d_dir = os.path.join(output_dir, "bbox_3d")
        self.cam_dir = os.path.join(output_dir, "camera")

        for d in [self.rgb_dir, self.depth_dir, self.sem_dir,
                  self.sem_labels_dir, self.bbox_3d_dir, self.cam_dir]:
            os.makedirs(d, exist_ok=True)

        super().initialize(output_dir=output_dir, **kwargs)

    def write(self, data):
        frame_tag = f"frame_{self._frame_id:04d}"

        # Dispatch annotator data by key prefix
        rgb_data = depth_data = sem_data = bbox3d_data = camera_data = None
        for key in data.keys():
            if key.startswith("rgb"):
                rgb_data = data[key]
            elif key.startswith("semantic_segmentation"):
                sem_data = data[key]
            elif key.startswith("distance_to_image_plane"):
                depth_data = data[key]
            elif key.startswith("bounding_box_3d"):
                bbox3d_data = data[key]
            elif key.startswith("camera_params"):
                camera_data = data[key]

        # ── RGB ────────────────────────────────────────────────────────────
        if rgb_data is not None:
            img = Image.fromarray(rgb_data, "RGBA")
            img.save(os.path.join(self.rgb_dir, f"{frame_tag}.png"))

        # ── Depth ──────────────────────────────────────────────────────────
        if depth_data is not None:
            np.save(os.path.join(self.depth_dir, f"{frame_tag}.npy"), depth_data)

        # ── Semantic Segmentation (cart-only filtered mask) ────────────────
        if sem_data is not None:
            raw_ids = np.asarray(sem_data["data"])
            if raw_ids.ndim == 3:
                raw_ids = raw_ids[:, :, 0]
            id_to_labels = sem_data["info"].get("idToLabels", {})

            # Identify which Replicator semantic IDs belong to cart classes
            cart_id_map = {}  # replicator_sem_id -> class_name
            for sem_id_str, label_info in id_to_labels.items():
                class_name = label_info.get("class", "")
                if class_name in CLASS_MAPPING:
                    cart_id_map[int(sem_id_str)] = class_name

            # Build cart-only colorized mask (non-cart pixels = transparent black)
            h, w = raw_ids.shape
            colored = np.zeros((h, w, 4), dtype=np.uint8)
            for sem_id, class_name in cart_id_map.items():
                r, g, b = SEMANTIC_COLORS[CLASS_MAPPING[class_name]]
                mask = raw_ids == sem_id
                colored[mask] = [r, g, b, 255]

            sem_img = Image.fromarray(colored, "RGBA")
            sem_img.save(os.path.join(self.sem_dir, f"{frame_tag}.png"))

            # Save filtered idToLabels (only cart classes, remapped to CLASS_MAPPING IDs)
            filtered_labels = {}
            for class_name in set(cart_id_map.values()):
                mapped_id = CLASS_MAPPING[class_name]
                filtered_labels[str(mapped_id)] = {"class": class_name}

            with open(os.path.join(self.sem_labels_dir, f"{frame_tag}.json"), "w") as f:
                json.dump(filtered_labels, f, indent=4)

        # ── 3D Bounding Boxes (multi-class filtered) ──────────────────────
        if bbox3d_data is not None:
            serializable_bbox = self._make_serializable(bbox3d_data)
            id_to_labels = serializable_bbox.get("info", {}).get("idToLabels", {})
            prim_paths = serializable_bbox.get("info", {}).get("primPaths", [])

            final_data = []
            new_prim_paths = []

            for i, box in enumerate(serializable_bbox.get("data", [])):
                sem_id = box.get("semanticId")
                label_info = id_to_labels.get(str(sem_id), {})
                class_name = label_info.get("class", "")
                prim_path = prim_paths[i] if i < len(prim_paths) else ""

                if class_name in CLASS_MAPPING and prim_path.startswith("/Replicator"):
                    box_copy = box.copy()
                    box_copy["semanticId"] = CLASS_MAPPING[class_name]
                    final_data.append(box_copy)
                    new_prim_paths.append(prim_path)

            filtered_bbox = {
                "data": final_data,
                "info": {
                    "primPaths": new_prim_paths,
                    "idToLabels": {
                        str(v): {"class": k} for k, v in CLASS_MAPPING.items()
                    }
                }
            }

            with open(os.path.join(self.bbox_3d_dir, f"{frame_tag}.json"), "w") as f:
                json.dump(filtered_bbox, f, indent=4)

        # ── Camera Parameters ─────────────────────────────────────────────
        if camera_data is not None:
            serializable_cam = self._make_serializable(camera_data)
            with open(os.path.join(self.cam_dir, f"{frame_tag}.json"), "w") as f:
                json.dump(serializable_cam, f, indent=4)

        self._frame_id += 1

    def _make_serializable(self, obj):
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, np.ndarray):
            if obj.dtype.names is not None:
                return [self._make_serializable(dict(zip(obj.dtype.names, record)))
                        for record in obj]
            else:
                return obj.tolist()
        elif isinstance(obj, (np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.int32, np.int64)):
            return int(obj)
        elif hasattr(obj, "tolist"):
            return obj.tolist()
        else:
            return obj

WriterRegistry.register(MultiModalRawWriter)


# ═══════════════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════════════

def get_path_str(obj):
    if hasattr(obj, 'GetPath'):
        return str(obj.GetPath())
    return str(obj)

def find_child_prim(stage, root_prim_or_path, target_name):
    """Find first descendant prim with the given name under root_prim_or_path."""
    path_str = get_path_str(root_prim_or_path)
    root_prim = stage.GetPrimAtPath(path_str)
    
    print(f">>> find_child_prim called for: {path_str}")
    print(f"    root_prim: {root_prim}")
    if root_prim:
        print(f"    IsValid: {root_prim.IsValid()}")
        print(f"    Children: {[c.GetName() for c in root_prim.GetChildren()]}")

    if not root_prim or not root_prim.IsValid():
        return None
        
    def _search(p):
        if p.GetName() == target_name:
            return p
        for child in p.GetChildren():
            found = _search(child)
            if found:
                return found
        return None
        
    return _search(root_prim)





# ═══════════════════════════════════════════════════════════════════════════
# Frame Distribution Across Scenes
# ═══════════════════════════════════════════════════════════════════════════

num_scenes = len(WAREHOUSE_SCENES)
frames_per_scene = NUM_FRAMES // num_scenes
remaining_frames = NUM_FRAMES % num_scenes

scene_frame_counts = [frames_per_scene] * num_scenes
for i in range(remaining_frames):
    scene_frame_counts[i] += 1

print(f"\n>>> Dataset generation plan: {NUM_FRAMES} total frames across {num_scenes} scenes")
for idx, url in enumerate(WAREHOUSE_SCENES):
    print(f"    Scene {idx+1}: {os.path.basename(url)} -> {scene_frame_counts[idx]} frames")


# ═══════════════════════════════════════════════════════════════════════════
# Main Generation Loop
# ═══════════════════════════════════════════════════════════════════════════

# Seed the randomizer to make sampling reproducible
rng = rep.rng.ReplicatorRNG(seed=42)

# Set Replicator to require explicit step() calls to capture
rep.orchestrator.set_capture_on_play(False)

for scene_idx, warehouse_url in enumerate(WAREHOUSE_SCENES):
    frames_for_this_scene = scene_frame_counts[scene_idx]
    if frames_for_this_scene <= 0:
        continue

    print(f"\n>>> {'═' * 60}")
    print(f">>>  SCENE {scene_idx + 1}/{num_scenes}: {os.path.basename(warehouse_url)}")
    print(f">>>  FRAMES: {frames_for_this_scene}")
    # Load warehouse environment
    omni.usd.get_context().open_stage(warehouse_url)
    
    # Wait for stage to fully load asynchronously
    while omni.usd.get_context().get_stage_state() != omni.usd.StageState.OPENED:
        simulation_app.update()

    stage = omni.usd.get_context().get_stage()

    # ── Setup Scene Assets and Prims ──────────────────────────────────────
    rep.functional.create.xform(name="Replicator")
    rep.functional.create.scope(name="Carts", parent="/Replicator")

    # Load all 3 cart USD models
    cart_handles = {}
    for ct in CART_TYPES:
        cart_handles[ct] = rep.functional.create.reference(
            usd_path="file://" + CART_USD_PATHS[ct],
            parent="/Replicator/Carts",
            name=f"Cart_{ct}"
        )
        print(f">>> Loaded cart USD: {ct}")

    simulation_app.update()

    # Wait for USD references to resolve and populate children
    for ct, cart_prim_path in cart_handles.items():
        prim_path_str = get_path_str(cart_prim_path)
        prim = stage.GetPrimAtPath(prim_path_str)
        attempts = 0
        while not prim.GetChildren() and attempts < 100:
            simulation_app.update()
            attempts += 1
        print(f">>> Cart USD {ct} loaded in {attempts} updates. Children: {[c.GetName() for c in prim.GetChildren()]}")

    # Deactivate rogue cameras and lights exported inside the cart USDs to prevent lighting/camera conflicts
    def _deactivate_rogue_prims(p):
        prim_path = str(p.GetPath())
        if "/Replicator/Carts/Cart_" in prim_path:
            prim_type = p.GetTypeName()
            if prim_type in ["Camera", "DomeLight", "DistantLight", "SphereLight", "RectLight"]:
                p.SetActive(False)
                print(f">>> Deactivated rogue {prim_type} at {prim_path}")
        for child in p.GetChildren():
            _deactivate_rogue_prims(child)
    
    _deactivate_rogue_prims(stage.GetPseudoRoot())

    # Apply per-class semantic labels to CartFrame prims only
    for class_name, cart_prim_path in cart_handles.items():
        frame_prim = find_child_prim(stage, cart_prim_path, "CartFrame")
        if frame_prim:
            upgrade_prim_semantics_to_labels(frame_prim)
            add_labels(frame_prim, labels=[class_name], taxonomy="class")
            print(f">>> Semantic '{class_name}' -> {frame_prim.GetPath()}")
        else:
            print(f"WARNING: CartFrame prim not found under {cart_prim_path}")

    # ── Materials Setup ───────────────────────────────────────────────────
    # We create the material primitives first so we can bind them
    rep.functional.create.scope(name="Materials", parent="/Replicator")

    # Metallic Cart Material
    cart_material = rep.functional.create.material(
        mdl="OmniPBR.mdl",
        diffuse_color_constant=(0.5, 0.5, 0.5), # Will be randomized below
        metallic_constant=0.85,
        reflection_roughness_constant=0.25,
        name="CartMetallic",
        parent="/Replicator/Materials",
    )
    
    # Box Material
    box_material = rep.functional.create.material(
        mdl="OmniPBR.mdl",
        diffuse_color_constant=(0.5, 0.5, 0.5), # Will be randomized below
        metallic_constant=0.0,
        reflection_roughness_constant=0.6,
        name="BoxMaterial",
        parent="/Replicator/Materials",
    )

    cart_mat_shade = UsdShade.Material(stage.GetPrimAtPath(get_path_str(cart_material)))
    box_mat_shade = UsdShade.Material(stage.GetPrimAtPath(get_path_str(box_material)))

    # Bind materials
    for class_name, cart_prim in cart_handles.items():
        if class_name == "leanflow":
            # Bind only to CartFrame (not to Box prims)
            frame_prim = find_child_prim(stage, cart_prim, "CartFrame")
            if frame_prim and frame_prim.IsValid():
                api = UsdShade.MaterialBindingAPI.Apply(frame_prim)
                api.Bind(cart_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
        else:
            prim = stage.GetPrimAtPath(get_path_str(cart_prim))
            if prim and prim.IsValid():
                api = UsdShade.MaterialBindingAPI.Apply(prim)
                api.Bind(cart_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)

    # Box Material Binding for leanflow
    leanflow_root = cart_handles["leanflow"]
    box_prims = {}
    leanflow_root_prim = stage.GetPrimAtPath(get_path_str(leanflow_root))
    if leanflow_root_prim and leanflow_root_prim.IsValid():
        def _find_boxes(p):
            prim_name = p.GetName()
            if prim_name in ["Box_0", "Box_1", "Box_2"]:
                api = UsdShade.MaterialBindingAPI.Apply(p)
                api.Bind(box_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
                box_prims[prim_name] = p
            for child in p.GetChildren():
                _find_boxes(child)
        _find_boxes(leanflow_root_prim)

    # ── Renderer settings (force TAA, disable OptiX denoiser) ─────────
    rep.settings.carb_settings("/rtx/indirectDiffuse/denoiser/enabled", True)
    rep.settings.carb_settings("/rtx/reflections/denoiser/enabled", True)
    rep.settings.carb_settings("/rtx/post/aa/op", 1)
    rep.settings.carb_settings("/rtx/pathtracing/optixDenoiser/enabled", False)
    rep.settings.carb_settings("/omni/replicator/RTSubframes", 12)

    # ── Scene lighting ────────────────────────────────────────────────
    rep.functional.create.scope(name="Lights", parent="/Replicator")
    domelight = rep.functional.create.dome_light(
        intensity=1000.0,
        color=(1.0, 1.0, 1.0),
        name="DomeLight",
        parent="/Replicator/Lights"
    )
    distantlight = rep.functional.create.distant_light(
        intensity=3000.0,
        color=(1.0, 1.0, 1.0),
        rotation=(0, 0, 0),
        name="DistantLight",
        parent="/Replicator/Lights"
    )

    # ── Camera Setup (with Stereo Noise) ───────────
    camera_mount = rep.functional.create.xform(name="camera_mount", parent="/Replicator")
    look_at_target = rep.functional.create.xform(name="look_at_target", parent="/Replicator")
    
    cam_path = "/Replicator/camera_mount/StereoCamera"
    rtx_cam = RtxCamera(
        path=cam_path,
    )
    
    rtx_cam.camera.set_focal_lengths([FOCAL_LENGTH])
    rtx_cam.camera.set_apertures(horizontal_apertures=[HORIZ_APERTURE])
    rtx_cam.camera.set_clipping_ranges(near_distances=[0.1], far_distances=[10000.0])
    
    stereo_sensor = SingleViewDepthCameraSensor(
        path=rtx_cam,
        resolution=(1280, 800),
        annotators=["distance_to_image_plane"]
    )
    
    rep.settings.carb_settings("/rtx/post/depthSensor/enabled", True)
    rep.settings.carb_settings("/rtx/post/depthSensor/baseline", 0.095)
    rep.settings.carb_settings("/rtx/post/depthSensor/rgbDepthOutputMode", 0) 
    
    camera = stage.GetPrimAtPath(cam_path)
    
    # ── Warehouse clutter props (distractors, no semantics) ───────────
    PROPS_BASE = f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/Props"
    prop_urls = [
        f"{PROPS_BASE}/SM_PaletteA_01.usd",
        f"{PROPS_BASE}/SM_CardBoxD_04.usd",
        f"{PROPS_BASE}/S_TrafficCone.usd",
    ]
    rep.functional.create.scope(name="Distractors", parent="/Replicator")
    clutter_prims = []
    for idx, url in enumerate(prop_urls):
        for sub_idx in range(2):
            clutter_prims.append(rep.functional.create.reference(
                usd_path=url,
                parent="/Replicator/Distractors",
                name=f"Distractor_{idx}_{sub_idx}"
            ))

    # Setup scatter plane for distractors
    scatter_plane = rep.create.plane(scale=(20.0, 20.0, 1.0), position=(0, 0, 0), visible=False, parent="/Replicator/Distractors")
    
    with rep.trigger.on_custom_event(event_name="scatter_distractors"):
        with rep.get.prims(path_pattern="/Replicator/Distractors/Distractor_[^/]+$"):
            rep.randomizer.scatter_2d(surface_prims=[scatter_plane], check_for_collisions=False)
            rep.modify.pose(rotation=rep.distribution.uniform((0, 0, 0), (0, 0, 360)))

    # ── Render product at 1280×800 landscape ──────────────────────────
    render_product = rep.create.render_product(camera, resolution=(1280, 800))
    # Warm up renderer to compile RTX shaders and load textures
    for _ in range(50):
        simulation_app.update()

    # Optimize by disabling continuous rendering
    render_product.hydra_texture.set_updates_enabled(False)

    # ── Writer attachment ─────────────────────────────────────────────
    scene_output = os.path.abspath(f"{OUTPUT_DIR}_temp_scene_{scene_idx}")
    print(f">>> Scene temp output: {scene_output}")

    writer = rep.WriterRegistry.get("MultiModalRawWriter")
    writer.initialize(output_dir=scene_output)
    writer.attach([render_product])

    simulation_app.update()

    # ── Generation Loop for this scene ─────────────────────────────────────
    print(f">>> Generating {frames_for_this_scene} frames...")
    
    num_distractors = len(clutter_prims)

    for frame_i in range(frames_for_this_scene):
        print(f">>>   Frame {frame_i + 1}/{frames_for_this_scene}")
        
        # Randomize materials
        grey_tint = float(rng.generator.uniform(0.4, 0.7))
        rep.functional.modify.attribute(cart_material, "inputs:diffuse_color_constant", (grey_tint, grey_tint, grey_tint))
        rep.functional.modify.attribute(cart_material, "inputs:metallic_constant", float(rng.generator.uniform(0.7, 1.0)))
        rep.functional.modify.attribute(cart_material, "inputs:reflection_roughness_constant", float(rng.generator.uniform(0.1, 0.45)))

        box_color = BOX_COLORS[int(rng.generator.integers(0, len(BOX_COLORS)))]
        rep.functional.modify.attribute(box_material, "inputs:diffuse_color_constant", tuple(float(c) for c in box_color))
        rep.functional.modify.attribute(box_material, "inputs:reflection_roughness_constant", float(rng.generator.uniform(0.4, 0.9)))
        
        # Randomize lighting
        rep.functional.modify.attribute(domelight, "inputs:intensity", float(rng.generator.uniform(100.0, 2500.0)))
        rep.functional.modify.attribute(domelight, "inputs:color", tuple(float(c) for c in rng.generator.uniform((0.5, 0.5, 0.5), (1.0, 1.0, 1.0))))
        rep.functional.modify.attribute(distantlight, "inputs:intensity", float(rng.generator.uniform(1000.0, 5000.0)))
        rep.functional.modify.attribute(distantlight, "inputs:color", tuple(float(c) for c in rng.generator.uniform((0.6, 0.6, 0.6), (1.0, 1.0, 1.0))))
        rep.functional.modify.pose(distantlight, rotation_value=tuple(float(r) for r in rng.generator.uniform((0, 0, 0), (360, 360, 360))))

        # 1. Random cart selection
        chosen_cart = CART_TYPES[int(rng.generator.integers(0, len(CART_TYPES)))]
        
        # 2. Box visibility (leanflow)
        if chosen_cart == "leanflow":
            num_boxes = int(rng.generator.integers(0, 4)) # 0 to 3 inclusive
            visible_boxes_indices = rng.generator.choice(3, size=num_boxes, replace=False) if num_boxes > 0 else []
        else:
            visible_boxes_indices = []

        # 3. Corridor-based Position and Yaw Selection
        corridor_x = float(rng.generator.choice([-3.5, 0.0, 3.5]))
        cx = corridor_x + float(rng.generator.uniform(-0.2, 0.2))
        cy = float(rng.generator.uniform(-4.0, 4.0))
        cyaw = float(rng.generator.choice([90.0, 270.0])) + float(rng.generator.uniform(-10.0, 10.0))
        cyaw_rad = math.radians(cyaw)
        
        # 4. Camera position
        d = float(rng.generator.uniform(1.2, 1.8))
        alpha = float(rng.generator.uniform(-15.0, 15.0))
        alpha_rad = math.radians(alpha)
        
        local_x = d * math.cos(alpha_rad)
        local_y = d * math.sin(alpha_rad)
        wx = cx + local_x * math.cos(cyaw_rad) - local_y * math.sin(cyaw_rad)
        wy = cy + local_x * math.sin(cyaw_rad) + local_y * math.cos(cyaw_rad)
        
        target_z = CAMERA_HEIGHT + d * math.tan(math.radians(TILT_ANGLE))
        
        # Trigger scatter distractor event
        rep.utils.send_og_event(event_name="scatter_distractors")

        # ── Apply everything ──────────────────────────────────────────────
        # Carts
        for ct, cart_path in cart_handles.items():
            if ct == chosen_cart:
                rep.functional.modify.pose(cart_path, position_value=(cx, cy, 0.0), rotation_value=(0.0, 0.0, cyaw))
                rep.functional.modify.visibility(cart_path, True)
            else:
                rep.functional.modify.pose(cart_path, position_value=(cx, cy, -1000.0), rotation_value=(0.0, 0.0, 0.0))
                rep.functional.modify.visibility(cart_path, False)

        # Boxes
        for bi in range(3):
            box_path = box_prims[f"Box_{bi}"]
            rep.functional.modify.visibility(box_path, bool(bi in visible_boxes_indices))

        # Camera and Look At
        rep.functional.modify.pose(look_at_target, position_value=(cx, cy, target_z))
        rep.functional.modify.pose(camera_mount, position_value=(wx, wy, CAMERA_HEIGHT), look_at_value=look_at_target)
        rep.functional.modify.pose(camera, rotation_value=(0, 0, -90)) # physical sensor rotation



        # Enable updates just for the capture to save GPU resources
        render_product.hydra_texture.set_updates_enabled(True)
        rep.orchestrator.step(rt_subframes=12, delta_time=0.0)
        render_product.hydra_texture.set_updates_enabled(False)

    print(">>> Waiting for disk dispatch...")
    rep.orchestrator.wait_until_complete()

    writer.detach()
    render_product.destroy()


print(f"\n>>> Generation complete. Temp scenes are in {OUTPUT_DIR}_temp_scene_*")
print(">>> Run `python consolidate_dataset.py` to merge and shuffle them.")
simulation_app.close()
