# generate_dataset_6_0_1.py
# Multi-class synthetic dataset generation using Omniverse Replicator
# Generates YOLO26-seg training data with three cart types (picanol, colruyt, leanflow)
# across multiple warehouse scenes with shuffled cross-scene consolidation.
# Updated for Isaac Sim 6.0.1+ (Functional API & isaacsim namespace)

import os
import sys
import random
import math
import shutil
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

# Force RTX Real-Time 2.0 path-tracing renderer
sys.argv.append("--/rtx/rendermode=RealTimePathTracing")

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

simulation_app = SimulationApp({"headless": True, "renderer": "RealTimePathTracing"})


# ─── Omniverse Imports ────────────────────────────────────────────────────
import omni.usd
import omni.replicator.core as rep

# MIGRATION 6.0: omni.isaac.core.utils -> isaacsim.core.utils
from isaacsim.core.utils.semantics import add_labels, upgrade_prim_semantics_to_labels
from isaacsim.core.utils.extensions import enable_extension
from isaacsim.core.utils.nucleus import get_assets_root_path

from isaacsim.sensors.experimental.rtx import RtxCamera, SingleViewDepthCameraSensor

from omni.replicator.core import Writer, WriterRegistry, AnnotatorRegistry
from pxr import Sdf, UsdShade, Usd
import numpy as np
from PIL import Image

enable_extension("omni.kit.asset_converter")
import omni.kit.asset_converter

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

def find_child_prim(stage, root_path, target_name):
    """Find first descendant prim with the given name under root_path."""
    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim:
        return None
    for prim in Usd.PrimRange(root_prim):
        if prim.GetName() == target_name:
            return prim
    return None


def get_distance_to_segment(p, a, b):
    """Compute minimum distance from point p to line segment AB (2D)."""
    ax, ay = a
    bx, by = b
    px, py = p

    ab_x, ab_y = bx - ax, by - ay
    ab_len_sq = ab_x**2 + ab_y**2
    if ab_len_sq == 0:
        return math.sqrt((px - ax)**2 + (py - ay)**2)

    t = max(0.0, min(1.0, ((px - ax) * ab_x + (py - ay) * ab_y) / ab_len_sq))
    proj_x = ax + t * ab_x
    proj_y = ay + t * ab_y
    return math.sqrt((px - proj_x)**2 + (py - proj_y)**2)





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

for scene_idx, warehouse_url in enumerate(WAREHOUSE_SCENES):
    frames_for_this_scene = scene_frame_counts[scene_idx]
    if frames_for_this_scene <= 0:
        continue

    print(f"\n>>> {'═' * 60}")
    print(f">>>  SCENE {scene_idx + 1}/{num_scenes}: {os.path.basename(warehouse_url)}")
    print(f">>>  FRAMES: {frames_for_this_scene}")
    print(f">>> {'═' * 60}")

    omni.usd.get_context().open_stage(warehouse_url)

    # ── Generate per-frame sequences ──────────────────────────────────────

    cart_positions = []
    cart_rotations = []
    camera_positions = []
    look_at_positions = []

    # Cart type selection and visibility sequences
    cart_choices = []
    visibility_seqs = {ct: [] for ct in CART_TYPES}

    # Box visibility sequences (leanflow only)
    box_viz_seqs = {"Box_0": [], "Box_1": [], "Box_2": []}

    # Distractor positions (6 props: 3 types × 2 instances)
    num_distractors = 6
    clutter_positions = [[] for _ in range(num_distractors)]

    for _ in range(frames_for_this_scene):
        # 1. Random cart selection (uniform across 3 types)
        chosen = random.choice(CART_TYPES)
        cart_choices.append(chosen)
        for ct in CART_TYPES:
            visibility_seqs[ct].append(ct == chosen)

        # 2. Box visibility (uniform: 0, 1, 2, or 3 boxes visible)
        if chosen == "leanflow":
            num_boxes = random.randint(0, 3)
            visible_boxes = random.sample(range(3), num_boxes)
        else:
            visible_boxes = []
        for bi in range(3):
            box_viz_seqs[f"Box_{bi}"].append(bi in visible_boxes)

        # 3. Cart position and yaw on warehouse floor
        cx = random.uniform(-4.0, 4.0)
        cy = random.uniform(-4.0, 4.0)
        cart_positions.append((cx, cy, 0.0))

        cyaw = random.uniform(0.0, 360.0)
        cart_rotations.append((0.0, 0.0, cyaw))
        cyaw_rad = math.radians(cyaw)

        # 4. Camera position (polar offset from cart front-center origin)
        d = random.uniform(1.0, 2.0)
        alpha = random.uniform(-45.0, 45.0)
        alpha_rad = math.radians(alpha)

        local_x = d * math.cos(alpha_rad)
        local_y = d * math.sin(alpha_rad)
        wx = cx + local_x * math.cos(cyaw_rad) - local_y * math.sin(cyaw_rad)
        wy = cy + local_x * math.sin(cyaw_rad) + local_y * math.cos(cyaw_rad)
        camera_positions.append((float(wx), float(wy), float(CAMERA_HEIGHT)))

        # 5. Look-at target (front-center of cart with small de-centering offsets)
        target_z = CAMERA_HEIGHT + d * math.tan(math.radians(TILT_ANGLE))
        offset_x = random.uniform(-0.1, 0.1)
        offset_y = random.uniform(-0.1, 0.1)
        offset_z = random.uniform(-0.05, 0.05)

        tx = cx + offset_x * math.cos(cyaw_rad) - offset_y * math.sin(cyaw_rad)
        ty = cy + offset_x * math.sin(cyaw_rad) + offset_y * math.cos(cyaw_rad)
        look_at_positions.append((float(tx), float(ty), float(target_z + offset_z)))

        # 6. Collision-free distractor positions
        # Cart body center ≈ 0.8m behind front-center along cart's forward axis
        body_cx = cx - CART_BODY_OFFSET * math.cos(cyaw_rad)
        body_cy = cy - CART_BODY_OFFSET * math.sin(cyaw_rad)

        placed_props = []
        for j in range(num_distractors):
            placed = False
            for _ in range(100):
                px = random.uniform(-5.0, 5.0)
                py = random.uniform(-5.0, 5.0)

                # Rule A: Line-of-sight clearance (camera <-> cart front)
                if get_distance_to_segment((px, py), (wx, wy), (tx, ty)) < 0.6:
                    continue
                # Rule B: Cart body clearance
                if math.sqrt((px - body_cx)**2 + (py - body_cy)**2) < CART_CLEARANCE:
                    continue
                # Rule C: Camera lens clearance
                if math.sqrt((px - wx)**2 + (py - wy)**2) < 0.6:
                    continue
                # Rule D: Inter-distractor clearance
                if any(math.sqrt((px - ox)**2 + (py - oy)**2) < 0.6 for ox, oy in placed_props):
                    continue

                clutter_positions[j].append((float(px), float(py), 0.0))
                placed_props.append((px, py))
                placed = True
                break
            if not placed:
                clutter_positions[j].append((10.0 + j * 2.0, 10.0, 0.0))

    # ── Setup Replicator Pipeline ─────────────────────────────────────────

    with rep.new_layer():
        # Load all 3 cart USD models simultaneously
        cart_handles = {}
        for ct in CART_TYPES:
            cart_handles[ct] = rep.create.from_usd(CART_USD_PATHS[ct])
            print(f">>> Loaded cart USD: {ct}")

        simulation_app.update()
        stage = omni.usd.get_context().get_stage()

        # Apply per-class semantic labels to CartFrame prims only
        # MIGRATION 6.0: Upgrade and apply new LabelsAPI
        for class_name, cart_handle in cart_handles.items():
            root_path = str(cart_handle.get_outputs()["prims"][0])
            frame_prim = find_child_prim(stage, root_path, "CartFrame")
            if frame_prim:
                upgrade_prim_semantics_to_labels(frame_prim)
                add_labels(frame_prim, labels=[class_name], instance_name="class")
                print(f">>> Semantic '{class_name}' -> {frame_prim.GetPath()}")
            else:
                print(f"WARNING: CartFrame prim not found under {root_path}")

        # ── Metallic cart material (randomized grey tints) ────────────────
        greys = [(float(g), float(g), float(g)) for g in np.linspace(0.4, 0.7, 50)]
        cart_material = rep.create.material_omnipbr(
            diffuse=rep.distribution.choice(greys),
            metallic=rep.distribution.uniform(0.7, 1.0),
            roughness=rep.distribution.uniform(0.1, 0.45),
        )
        cart_mat_path = Sdf.Path(str(cart_material.get_outputs()["prims"][0]))
        cart_mat_shade = UsdShade.Material(stage.GetPrimAtPath(cart_mat_path))

        # Bind metallic material: to root for picanol/colruyt, to CartFrame for leanflow
        for class_name, cart_handle in cart_handles.items():
            root_path = str(cart_handle.get_outputs()["prims"][0])
            if class_name == "leanflow":
                # Bind only to CartFrame (not to Box prims)
                frame_prim = find_child_prim(stage, root_path, "CartFrame")
                if frame_prim:
                    api = UsdShade.MaterialBindingAPI.Apply(frame_prim)
                    api.Bind(cart_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
                    print(f">>> Metallic material -> {frame_prim.GetPath()} (leanflow frame)")
            else:
                for prim_path in cart_handle.get_outputs()["prims"]:
                    prim = stage.GetPrimAtPath(Sdf.Path(str(prim_path)))
                    if prim:
                        api = UsdShade.MaterialBindingAPI.Apply(prim)
                        api.Bind(cart_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
                        print(f">>> Metallic material -> {prim.GetPath()}")

        # ── Box material (randomized solid colors) ────────────────────────
        box_material = rep.create.material_omnipbr(
            diffuse=rep.distribution.choice(BOX_COLORS),
            roughness=rep.distribution.uniform(0.4, 0.9),
            metallic=0.0,
        )
        box_mat_path = Sdf.Path(str(box_material.get_outputs()["prims"][0]))
        box_mat_shade = UsdShade.Material(stage.GetPrimAtPath(box_mat_path))

        # Find box prims in leanflow, bind material and get Replicator handles
        leanflow_root = str(cart_handles["leanflow"].get_outputs()["prims"][0])
        box_rep_handles = {}
        for prim in Usd.PrimRange(stage.GetPrimAtPath(leanflow_root)):
            prim_name = prim.GetName()
            if prim_name in ["Box_0", "Box_1", "Box_2"]:
                api = UsdShade.MaterialBindingAPI.Apply(prim)
                api.Bind(box_mat_shade, bindingStrength=UsdShade.Tokens.strongerThanDescendants)
                prim_path = str(prim.GetPath())
                box_rep_handles[prim_name] = rep.get.prims(
                    path_pattern=f"{prim_path}$", ignore_case=False
                )
                print(f">>> Box material + handle: {prim_path}")

        # ── Renderer settings (force TAA, disable OptiX denoiser) ─────────
        rep.settings.carb_settings("/rtx/indirectDiffuse/denoiser/enabled", True)
        rep.settings.carb_settings("/rtx/reflections/denoiser/enabled", True)
        rep.settings.carb_settings("/rtx/post/aa/op", 1)
        rep.settings.carb_settings("/rtx/pathtracing/optixDenoiser/enabled", False)
        rep.settings.carb_settings("/omni/replicator/RTSubframes", 4)

        # ── Scene lighting ────────────────────────────────────────────────
        domelight = rep.create.light(light_type="dome")
        distantlight = rep.create.light(light_type="distant")

        # ── Camera mount + camera hierarchy (with Stereo Noise) ───────────
        camera_mount = rep.create.xform(name="camera_mount")
        
        # 1. Authoring: Create physical RtxCamera
        cam_path = "/Replicator/camera_mount/StereoCamera"
        rtx_cam = RtxCamera(
            prim_path=cam_path,
            focal_length=FOCAL_LENGTH,
            horizontal_aperture=HORIZ_APERTURE,
            clipping_range=(0.1, 10000.0)
        )
        
        # 2. Runtime: Wrap in SingleViewDepthCameraSensor for stereo disparity/noise
        stereo_sensor = SingleViewDepthCameraSensor(prim_path=cam_path)
        
        # 3. Configure D455 stereo baseline (95mm) and enable post-processing noise
        rep.settings.carb_settings("/rtx/post/depthSensor/enabled", True)
        rep.settings.carb_settings("/rtx/post/depthSensor/baseline", 0.095)
        # 1 = Disparity mode, forcing stereo calculation failures on reflective materials
        rep.settings.carb_settings("/rtx/post/depthSensor/rgbDepthOutputMode", 1) 
        
        # Replicator needs a handle to the camera prim
        camera = rep.get.prims(path_pattern=cam_path)
        
        # Parent the camera under the mount
        with camera_mount:
            rep.modify.pose(look_at=None) # Ensure mount acts as parent

        look_at_target = rep.create.xform(name="look_at_target")

        # ── Warehouse clutter props (distractors, no semantics) ───────────
        PROPS_BASE = f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/Props"
        prop_urls = [
            f"{PROPS_BASE}/SM_PaletteA_01.usd",
            f"{PROPS_BASE}/SM_CardBoxD_04.usd",
            f"{PROPS_BASE}/S_TrafficCone.usd",
        ]
        clutter_prims = []
        for url in prop_urls:
            for _ in range(2):
                clutter_prims.append(rep.create.from_usd(url))

        # ── Frame Trigger ─────────────────────────────────────────────────
        with rep.trigger.on_frame(max_execs=frames_for_this_scene):
            # All 3 carts share the same pose sequence (only one visible per frame)
            for ct in CART_TYPES:
                with cart_handles[ct]:
                    rep.modify.pose(
                        position=rep.distribution.sequence(cart_positions),
                        rotation=rep.distribution.sequence(cart_rotations),
                    )

            # Per-cart visibility
            for ct in CART_TYPES:
                with cart_handles[ct]:
                    rep.modify.visibility(rep.distribution.sequence(visibility_seqs[ct]))

            # Box visibility (leanflow boxes)
            for box_name, box_handle in box_rep_handles.items():
                with box_handle:
                    rep.modify.visibility(rep.distribution.sequence(box_viz_seqs[box_name]))

            # Camera mount: position + look-at aiming
            with look_at_target:
                rep.modify.pose(position=rep.distribution.sequence(look_at_positions))
            with camera_mount:
                rep.modify.pose(
                    position=rep.distribution.sequence(camera_positions),
                    look_at=look_at_target,
                )
            # Camera: static 90° roll for D455 physical sensor rotation
            with camera:
                rep.modify.pose(rotation=(0, 0, 90))

            # Distractor placement
            for j, clutter_prim in enumerate(clutter_prims):
                with clutter_prim:
                    rep.modify.pose(
                        position=rep.distribution.sequence(clutter_positions[j]),
                        rotation=rep.distribution.uniform((0, 0, 0), (0, 0, 360)),
                    )

            # Lighting randomization
            with domelight:
                rep.modify.attribute("inputs:intensity", rep.distribution.uniform(100.0, 2500.0))
                rep.modify.attribute("inputs:color",
                                     rep.distribution.uniform((0.5, 0.5, 0.5), (1.0, 1.0, 1.0)))
            with distantlight:
                rep.modify.attribute("inputs:intensity", rep.distribution.uniform(1000.0, 5000.0))
                rep.modify.attribute("inputs:color",
                                     rep.distribution.uniform((0.6, 0.6, 0.6), (1.0, 1.0, 1.0)))
                rep.modify.pose(rotation=rep.distribution.uniform((0, 0, 0), (360, 360, 360)))

        # ── Render product at 1280×800 landscape ──────────────────────────
        render_product = rep.create.render_product(camera, resolution=(1280, 800))

        # ── Writer attachment ─────────────────────────────────────────────
        scene_output = os.path.abspath(f"{OUTPUT_DIR}_temp_scene_{scene_idx}")
        print(f">>> Scene temp output: {scene_output}")

        writer = rep.WriterRegistry.get("MultiModalRawWriter")
        writer.initialize(output_dir=scene_output)
        writer.attach([render_product])

    # ── Run generation for this scene ─────────────────────────────────────
    rep.orchestrator.set_capture_on_play(False)

    for _ in range(5):
        simulation_app.update()

    print(f">>> Generating {frames_for_this_scene} frames...")
    for frame_i in range(frames_for_this_scene):
        print(f">>>   Frame {frame_i + 1}/{frames_for_this_scene}")
        rep.orchestrator.step(rt_subframes=4, delta_time=0.0)

    print(">>> Waiting for disk dispatch...")
    rep.orchestrator.wait_until_complete()

    writer.detach()
    render_product.destroy()


print(f"\n>>> Generation complete. Temp scenes are in {OUTPUT_DIR}_temp_scene_*")
print(">>> Run `python consolidate_dataset.py` to merge and shuffle them.")
simulation_app.close()
