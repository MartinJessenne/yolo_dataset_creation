# generate_dataset_6_0_1.py
# Multi-class synthetic dataset generation using Omniverse Replicator
# Generates YOLO26-seg training data with three cart types (picanol, colruyt, leanflow)
# across multiple warehouse scenes with shuffled cross-scene consolidation.
# Updated for Isaac Sim 6.0.1+ (Functional API & isaacsim namespace)

import os
import sys
import math
import json
import random
import shutil


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

SCENE_IDX = None
if "--scene_idx" in sys.argv:
    try:
        idx = sys.argv.index("--scene_idx")
        if idx + 1 < len(sys.argv):
            SCENE_IDX = int(sys.argv[idx + 1])
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
import omni.client

# Set omni.client log level to ERROR to suppress warning spam
omni.client.set_log_level(omni.client.LogLevel.ERROR)

# MIGRATION 6.0: omni.isaac.core.utils -> isaacsim.core.utils
try:
    from isaacsim.core.experimental.utils.semantics import add_labels, upgrade_prim_semantics_to_labels
except ImportError:
    from isaacsim.core.utils.semantics import add_labels, upgrade_prim_semantics_to_labels
from isaacsim.storage.native import get_assets_root_path
import isaacsim.core.utils.prims as prim_utils
from isaacsim.sensors.experimental.rtx import RtxCamera, SingleViewDepthCameraSensor

from omni.replicator.core import Writer, WriterRegistry, AnnotatorRegistry
from pxr import Sdf, UsdShade, Usd, UsdGeom, Gf
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
if not assets_root:
    print("\nERROR: get_assets_root_path() returned None. Cannot resolve Isaac assets "
          "(warehouse scenes, D455 sensor USD). Check Nucleus/asset server connectivity.")
    simulation_app.close()
    exit(1)
ISAAC_ASSETS = f"{assets_root}/Isaac"

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
CAMERA_ROLL_DEG = -90.0     # roll about the optical axis (physically rotated D455, portrait mount)

# DepthSensorDistance (SingleViewDepthCameraSensor) outputs RealSense-style depth units of
# 100 um, not meters: validated against distance_to_image_plane on this D455 config
# (median ratio 9.99e3 vs meters, pixel correlation 0.998). Converted before writing so
# depth/ and the ground-truth fallback share the same unit (meters).
DEPTH_SENSOR_UNIT_M = 1.0e-4
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
        # NOTE: depth is captured separately by DepthSensorWriter (see below), driven by
        # SingleViewDepthCameraSensor's noisy depth annotator instead of the ground-truth
        # distance_to_image_plane annotator, to better match real D455 sim2real noise.
        # Assign (not append): Writer.initialize() re-runs __init__ on the same instance,
        # so appending would duplicate annotators on every per-scene re-initialization.
        self.annotators = [
            AnnotatorRegistry.get_annotator("rgb"),
            AnnotatorRegistry.get_annotator(
                "semantic_segmentation", init_params={"colorize": False}
            ),
            AnnotatorRegistry.get_annotator("bounding_box_3d"),
            AnnotatorRegistry.get_annotator("camera_params"),
        ]

    def initialize(self, output_dir: str, **kwargs):
        self._output_dir = output_dir
        self._frame_id = 0
        self._skipped_frames = 0

        self.rgb_dir = os.path.join(output_dir, "rgb")
        self.sem_dir = os.path.join(output_dir, "semantic")
        self.sem_labels_dir = os.path.join(output_dir, "semantic_labels")
        self.bbox_3d_dir = os.path.join(output_dir, "bbox_3d")
        self.cam_dir = os.path.join(output_dir, "camera")

        for d in [self.rgb_dir, self.sem_dir,
                  self.sem_labels_dir, self.bbox_3d_dir, self.cam_dir]:
            os.makedirs(d, exist_ok=True)

        super().initialize(output_dir=output_dir, **kwargs)

    def write(self, data):
        print(f"\n>>> MultiModalRawWriter.write called! keys: {list(data.keys())}", flush=True)
        try:
            self._write_impl(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f">>> Exception in MultiModalRawWriter.write: {e}", flush=True)
            raise e

    def _write_impl(self, data):
        frame_tag = f"frame_{self._frame_id:06d}"

        # Dispatch annotator data by key prefix
        rgb_data = sem_data = bbox3d_data = camera_data = None
        for key in data.keys():
            if key.startswith("rgb"):
                rgb_data = data[key]
            elif key.startswith("semantic_segmentation"):
                sem_data = data[key]
            elif key.startswith("bounding_box_3d"):
                bbox3d_data = data[key]
            elif key.startswith("camera_params"):
                camera_data = data[key]

        # ── Semantic Segmentation (cart-only filtered mask) ────────────────
        # Computed before any disk writes: this frame is only kept if it has
        # a visible cart, so RGB/bbox/camera decisions below depend on it.
        colored = filtered_labels = None
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

            # Filtered idToLabels (only cart classes, remapped to CLASS_MAPPING IDs)
            filtered_labels = {}
            for class_name in set(cart_id_map.values()):
                mapped_id = CLASS_MAPPING[class_name]
                filtered_labels[str(mapped_id)] = {"class": class_name}

        # ── 3D Bounding Boxes (multi-class filtered) ──────────────────────
        filtered_bbox = None
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
                    # Skip carts hidden by teleporting below the floor (z = -1000); their
                    # visibility stays 'inherited' so they still appear in bbox_3d output.
                    transform = box.get("transform")
                    if transform is not None and len(transform) == 4 and transform[3][2] < -100.0:
                        continue
                    box_copy = box.copy()
                    box_copy["semanticId"] = CLASS_MAPPING[class_name]
                    box_copy["className"] = class_name
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

        # ── Unlabeled-frame guard ────────────────────────────────────────
        # A frame is only usable if the chosen cart both (a) has a bbox_3d entry
        # (its origin is within the camera frustum) and (b) is actually visible in
        # the rendered mask (not fully occluded by a distractor or clipped out).
        # Isaac Sim's bounding_box_3d annotator only returns entries for objects at
        # least partially in-frustum, so at close range (camera-to-cart distance can
        # now go down to 0.5m) or extreme approach angles, the chosen cart can end up
        # with zero pixels or no box at all -- skip writing anything for that frame
        # rather than shipping an unlabeled positive into the training set.
        has_bbox = bool(filtered_bbox is not None and filtered_bbox["data"])
        has_mask_pixels = bool(colored is not None and colored[:, :, 3].any())
        if not (has_bbox and has_mask_pixels):
            self._skipped_frames += 1
            print(f">>> Skipping {frame_tag}: no visible cart in frame "
                  f"(has_bbox={has_bbox}, has_mask_pixels={has_mask_pixels})", flush=True)
            self._frame_id += 1
            return

        # ── RGB ────────────────────────────────────────────────────────────
        if rgb_data is not None:
            img = Image.fromarray(rgb_data, "RGBA")
            img.save(os.path.join(self.rgb_dir, f"{frame_tag}.png"))

        # ── Semantic Segmentation (write) ───────────────────────────────────
        sem_img = Image.fromarray(colored, "RGBA")
        sem_img.save(os.path.join(self.sem_dir, f"{frame_tag}.png"))

        with open(os.path.join(self.sem_labels_dir, f"{frame_tag}.json"), "w") as f:
            json.dump(filtered_labels, f, indent=4)

        # ── 3D Bounding Boxes (write) ────────────────────────────────────
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
# Custom Writer: DepthSensorWriter (native depth, registered to the RGB view)
# ═══════════════════════════════════════════════════════════════════════════
# Captures the noisy, sim2real-realistic "depth_sensor_distance" annotator driven by
# SingleViewDepthCameraSensor. Also captures the ground-truth "distance_to_image_plane"
# annotator side-by-side into a diagnostic folder, since the depth_sensor_distance wiring
# for the D455 is unverified until tested on a rented GPU. Drop the diagnostic capture
# (and the fallback below) once depth_sensor_distance is confirmed to produce sane output.
class DepthSensorWriter(Writer):
    def __init__(self, output_dir: str = None, **kwargs):
        super().__init__()
        self._frame_id = 0
        # "depth_sensor_distance" is SingleViewDepthCameraSensor's friendly alias, not a
        # Replicator registry name -- the registry entry is the raw render var
        # "DepthSensorDistance". It must be fetched on the host (cpu): the GPU buffer node
        # logs "corrupted input renderVar" every frame for DepthSensor* vars (see
        # isaacsim.sensors.experimental.rtx camera_sensor.py _CPU_ANNOTATORS).
        self.annotators = [
            AnnotatorRegistry.get_annotator("DepthSensorDistance", device="cpu"),
            AnnotatorRegistry.get_annotator("distance_to_image_plane"),
        ]

    def initialize(self, output_dir: str, **kwargs):
        self._output_dir = output_dir
        self._frame_id = 0

        self.depth_dir = os.path.join(output_dir, "depth")
        self.depth_gt_diag_dir = os.path.join(output_dir, "depth_ground_truth_diagnostic")

        for d in [self.depth_dir, self.depth_gt_diag_dir]:
            os.makedirs(d, exist_ok=True)

        super().initialize(output_dir=output_dir, **kwargs)

    def write(self, data):
        try:
            self._write_impl(data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f">>> Exception in DepthSensorWriter.write: {e}", flush=True)
            raise e

    def _write_impl(self, data):
        frame_tag = f"frame_{self._frame_id:06d}"

        noisy_depth = gt_depth = None
        for key in data.keys():
            if key.startswith("DepthSensorDistance") or key.startswith("depth_sensor_distance"):
                noisy_depth = data[key]
            elif key.startswith("distance_to_image_plane"):
                gt_depth = data[key]

        noisy_depth = self._normalize_depth(noisy_depth)
        gt_depth = self._normalize_depth(gt_depth)

        if gt_depth is not None:
            np.save(os.path.join(self.depth_gt_diag_dir, f"{frame_tag}.npy"), gt_depth)

        if noisy_depth is not None:
            noisy_depth = noisy_depth * DEPTH_SENSOR_UNIT_M  # 100 um units -> meters
            if gt_depth is not None:
                valid = (noisy_depth > 0) & (gt_depth > 0)
                if valid.any():
                    ratio = float(np.median(noisy_depth[valid] / gt_depth[valid]))
                    if not 0.5 < ratio < 2.0:
                        print(f">>> WARNING: noisy/gt depth median ratio {ratio:.3f} for "
                              f"{frame_tag} -- DEPTH_SENSOR_UNIT_M may be wrong for this "
                              f"sensor config; depth/ units are suspect.", flush=True)
            np.save(os.path.join(self.depth_dir, f"{frame_tag}.npy"), noisy_depth)
        elif gt_depth is not None:
            print(f">>> WARNING: depth_sensor_distance produced no data for {frame_tag}; "
                  f"falling back to ground-truth distance_to_image_plane in depth/. "
                  f"Verify SingleViewDepthCameraSensor wiring before trusting this dataset "
                  f"for sim2real noise realism.", flush=True)
            np.save(os.path.join(self.depth_dir, f"{frame_tag}.npy"), gt_depth)
        else:
            print(f">>> ERROR: no depth data at all for {frame_tag} "
                  f"(both depth_sensor_distance and distance_to_image_plane were empty).", flush=True)

        self._frame_id += 1

    @staticmethod
    def _normalize_depth(payload):
        """Coerce annotator payloads (dict-with-data, warp/flat buffers) to a (H, W) float32
        numpy array; returns None for missing/empty data so the fallback logic can react."""
        if payload is None:
            return None
        if isinstance(payload, dict):
            payload = payload.get("data")
            if payload is None:
                return None
        if hasattr(payload, "numpy"):  # warp array
            payload = payload.numpy()
        arr = np.asarray(payload)
        if arr.size == 0:
            return None
        if arr.ndim == 1:
            # Raw render var arrives flat; recover the known render resolution (800x1280)
            if arr.size % 1280 == 0:
                arr = arr.reshape(-1, 1280)
            else:
                return None
        elif arr.ndim == 3 and arr.shape[-1] == 1:
            arr = arr[:, :, 0]
        return arr.astype(np.float32, copy=False)


WriterRegistry.register(DepthSensorWriter)


# ═══════════════════════════════════════════════════════════════════════════
# Utility Functions
# ═══════════════════════════════════════════════════════════════════════════

def get_path_str(obj):
    if hasattr(obj, 'GetPath'):
        return str(obj.GetPath())
    return str(obj)

def find_child_prim(stage, root, target_name):
    root_path = get_path_str(root)
    root_prim = stage.GetPrimAtPath(root_path)
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
# Main Persistent USD Stage Setup
# ═══════════════════════════════════════════════════════════════════════════

# Create new stage that persists across the entire generation process
omni.usd.get_context().new_stage()
stage = omni.usd.get_context().get_stage()

# Define the environment group scope to load warehouses as references
env_prim = stage.DefinePrim("/World/Environment", "Xform")

# Seed the randomizer to make sampling reproducible. NOTE: rep.rng.ReplicatorRNG resets its
# generator back to the seeded state whenever it receives Replicator's "initialize"
# orchestrator event -- which arrives with a one-frame lag after the first step() call, so
# it lands mid-loop and silently re-plays frame 0's random draws on frame 1 (duplicate
# frames). A plain seeded numpy Generator isn't coupled to orchestrator events, so it just
# advances normally; wrapped in a tiny shim so the `rng.generator.<dist>(...)` call sites
# below don't need to change.
class _PlainRNG:
    def __init__(self, seed):
        self.generator = np.random.default_rng(seed)

rng = _PlainRNG(seed=42)

# Set Replicator to require explicit step() calls to capture
rep.orchestrator.set_capture_on_play(False)

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
        print(f"\nERROR: CartFrame prim not found under {cart_prim_path}. "
              f"'{class_name}' would be generated with no semantic label, silently "
              f"corrupting the dataset. Aborting instead of continuing.")
        simulation_app.close()
        exit(1)

# ── Materials Setup ───────────────────────────────────────────────────
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
rep.settings.carb_settings("/omni/replicator/RTSubframes", 6)

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
spherelight = rep.functional.create.sphere_light(
    intensity=100000.0,
    radius=0.5,
    color=(1.0, 1.0, 1.0),
    name="SphereLight",
    parent="/Replicator/Lights"
)

# ── Camera Setup (RealSense D455 USD Integration) ───────────
camera_mount = rep.functional.create.xform(name="camera_mount", parent="/Replicator")
look_at_target = rep.functional.create.xform(name="look_at_target", parent="/Replicator")

d455_usd_path = f"{assets_root}/Isaac/Sensors/RealSense/D455/rsd455.usd"
prim_path = "/Replicator/camera_mount/RealSense_D455"
print(f"Spawning official RealSense D455 USD from: {d455_usd_path}")
prim_utils.create_prim(prim_path=prim_path, usd_path=d455_usd_path)

# Wait for reference to load and renderer to initialize
for _ in range(50):
    simulation_app.update()

rgb_camera_path = "/Replicator/camera_mount/RealSense_D455/RSD455/Camera_OmniVision_OV9782_Color"
camera = stage.GetPrimAtPath(rgb_camera_path)

# The D455 asset's cameras look along the asset's +X axis with image-up +Z (robotics
# convention), not along the USD-camera -Z. Rather than hardcode that offset, measure the
# color camera's rest orientation while the mount is identity, and solve the mount rotation
# from it each frame (mount_rot = rest_rot^-1 * desired_camera_rot, row-vector convention).
mount_prim = stage.GetPrimAtPath("/Replicator/camera_mount")
_mount_xform = UsdGeom.Xformable(mount_prim)
_mount_xform.ClearXformOpOrder()
mount_matrix_op = _mount_xform.MakeMatrixXform()
_cam_rest = UsdGeom.Xformable(camera).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
_cam_rest_rot = _cam_rest.ExtractRotationMatrix().GetOrthonormalized()
CAM_REST_ROT_INV = Gf.Matrix4d().SetRotate(_cam_rest_rot.ExtractRotation()).GetInverse()
print(f">>> D455 color camera rest optical axis (world, mount=identity): "
      f"{[round(v, 4) for v in _cam_rest.TransformDir(Gf.Vec3d(0, 0, -1))]}")

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

# ── Create the Render Product ──────────────────────────────────────
print(f"Creating render product for camera: {rgb_camera_path} at 1280x800")
render_product = rep.create.render_product(rgb_camera_path, resolution=(1280, 800))

# Warm up renderer to compile RTX shaders and load textures
for _ in range(50):
    simulation_app.update()

# Writer instantiation only. WriterRegistry.get() creates the writer via __new__ WITHOUT
# running __init__, so the annotator list is empty until initialize() runs -- attaching here
# would build a writer graph with no annotators and silently produce empty frames.
# initialize() + attach() happen per scene inside the generation loop instead.
writer = rep.WriterRegistry.get("MultiModalRawWriter")

# ── Depth Sensor Setup (SingleViewDepthCameraSensor: noisy, sim2real-realistic depth) ──
# Wraps the RGB camera prim itself, so depth comes out already registered to the RGB
# view/resolution (single-view depth estimation, no separate baseline reprojection needed).
# resolution follows the OpenCV/NumPy convention (height, width), i.e. 800x1280 landscape.
depth_rtx_camera = RtxCamera(rgb_camera_path)
depth_sensor = SingleViewDepthCameraSensor(
    depth_rtx_camera,
    resolution=(800, 1280),
    annotators=["depth_sensor_distance"],
)
depth_sensor.set_enabled_post_processing(True)
# NOTE: depth_sensor.render_product is a pxr.UsdRender.Product (USD schema wrapper over the
# already-created hydra texture prim), unlike rep.create.render_product's return value above
# (a Replicator handle with a plain .path string) -- use GetPath() here instead of .path.
depth_render_product_path = str(depth_sensor.render_product.GetPath())

# The sensor's own asset-template auto-detection (_populate_from_asset_template) is a no-op
# when wrapping an existing prim by path (only works via RtxCamera.create(usd_path=...)), so
# replicate it here: find a RenderProduct with OmniSensorDepthSensorSingleViewAPI embedded in
# the loaded rsd455.usd and copy its omni:rtx:post:depthSensor:* config (baseline, noise, ...)
# onto our render product. Best-effort -- defaults are used if the asset carries no template.
_d455_root = stage.GetPrimAtPath("/Replicator/camera_mount/RealSense_D455")
_template_found = False
if _d455_root and _d455_root.IsValid():
    for _p in Usd.PrimRange(_d455_root):
        if _p.GetTypeName() == "RenderProduct" and _p.HasAPI("OmniSensorDepthSensorSingleViewAPI"):
            _dst = stage.GetPrimAtPath(depth_render_product_path)
            _copied = 0
            for _attr in _p.GetAttributes():
                _name = _attr.GetName()
                if _name.startswith("omni:rtx:post:depthSensor:") and _name != "omni:rtx:post:depthSensor:enabled":
                    if _dst.HasAttribute(_name) and _attr.Get() is not None:
                        _dst.GetAttribute(_name).Set(_attr.Get())
                        _copied += 1
            print(f">>> Copied {_copied} depth sensor template attrs from {_p.GetPath()}")
            _template_found = True
            break
if not _template_found:
    print(">>> No OmniSensorDepthSensorSingleViewAPI template found in rsd455.usd; "
          "using SingleViewDepthCameraSensor defaults for baseline/noise.")

# Instantiation only -- initialize() + attach() happen per scene (see note on writer above).
depth_writer = rep.WriterRegistry.get("DepthSensorWriter")


# ═══════════════════════════════════════════════════════════════════════════
# Main Generation Loop (Sequential over environments on a single stage)
# ═══════════════════════════════════════════════════════════════════════════

for scene_idx, warehouse_url in enumerate(WAREHOUSE_SCENES):
    if SCENE_IDX is not None and scene_idx != SCENE_IDX:
        continue
    frames_for_this_scene = scene_frame_counts[scene_idx]
    if frames_for_this_scene <= 0:
        continue

    print(f"\n>>> {'═' * 60}")
    print(f">>>  SCENE {scene_idx + 1}/{num_scenes}: {os.path.basename(warehouse_url)}")
    print(f">>>  FRAMES: {frames_for_this_scene}")
    
    # Load warehouse environment dynamically via reference
    env_prim.GetReferences().ClearReferences()
    env_prim.GetReferences().AddReference(warehouse_url)
    
    # Wait for stage to fully load and compile referenced USD components
    for _ in range(100):
        simulation_app.update()

    # Re-initialize writer output folder for this scene, then attach. initialize() must
    # precede attach(): it runs __init__ (via Writer.initialize) which populates the
    # annotator list the attach-time writer graph is built from.
    scene_output = os.path.abspath(f"{OUTPUT_DIR}_temp_scene_{scene_idx}")
    print(f">>> Scene temp output: {scene_output}")
    writer.initialize(output_dir=scene_output)
    depth_writer.initialize(output_dir=scene_output)
    writer.attach([render_product.path])
    depth_writer.attach([depth_render_product_path])

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
        if "full_warehouse" in warehouse_url:
            corridor_x = float(rng.generator.choice([-12.0, -10.0, -8.0]))
            cx = corridor_x + float(rng.generator.uniform(-0.2, 0.2))
            cy = float(rng.generator.uniform(-8.0, 4.0))
        else:
            corridor_x = float(rng.generator.choice([-3.5, 0.0, 3.5]))
            cx = corridor_x + float(rng.generator.uniform(-0.2, 0.2))
            cy = float(rng.generator.uniform(-4.0, 4.0))
        cyaw = float(rng.generator.choice([90.0, 270.0])) + float(rng.generator.uniform(-10.0, 10.0))
        cyaw_rad = math.radians(cyaw)
        
        # 4. Camera position (robot approaches cart in a 2D horizontal yaw cone)
        # Distance d is from the front-center of the cart (0.8m to 3.0m)
        # Horizontal deviation alpha is in [-45.0, 45.0] degrees
        d = float(rng.generator.uniform(0.8, 3.0))
        alpha = float(rng.generator.uniform(-45.0, 45.0))
        alpha_rad = math.radians(alpha)
        
        local_x = d * math.cos(alpha_rad)
        local_y = d * math.sin(alpha_rad)
        wx = cx + local_x * math.cos(cyaw_rad) - local_y * math.sin(cyaw_rad)
        wy = cy + local_x * math.sin(cyaw_rad) + local_y * math.cos(cyaw_rad)
        
        # Camera height is physically fixed on the robot at CAMERA_HEIGHT = 0.304m
        # Camera inclination is physically fixed at TILT_ANGLE = 30.0 degrees upward
        target_z = CAMERA_HEIGHT + d * math.tan(math.radians(TILT_ANGLE))

        # ── Apply everything via USD Stage API ──────────────────────────────
        # Carts
        for ct, cart_path in cart_handles.items():
            prim_path = get_path_str(cart_path)
            cart_prim = stage.GetPrimAtPath(prim_path)
            xform = UsdGeom.XformCommonAPI(cart_prim)
            # Hide non-chosen carts by teleporting far below the floor instead of toggling
            # visibility: prims switched invisible->visible drop out of the semantic instance
            # mapping and render as UNLABELLED. Teleported carts stay in bounding_box_3d
            # output, so the writer filters boxes at z < -100 (see _write_impl).
            if ct == chosen_cart:
                xform.SetTranslate((cx, cy, 0.0))
                xform.SetRotate((0.0, 0.0, cyaw))
            else:
                xform.SetTranslate((cx, cy, -1000.0))
                xform.SetRotate((0.0, 0.0, 0.0))
            cart_prim.GetAttribute("visibility").Set("inherited")

        # Boxes
        for bi in range(3):
            box_key = f"Box_{bi}"
            if box_key in box_prims:
                box_path = box_prims[box_key]
                box_prim = stage.GetPrimAtPath(get_path_str(box_path))
                if box_prim and box_prim.IsValid():
                    if bi in visible_boxes_indices:
                        box_prim.GetAttribute("visibility").Set("inherited")
                    else:
                        box_prim.GetAttribute("visibility").Set("invisible")

        # Camera and Look At target translations and rotation calculation
        target_prim = stage.GetPrimAtPath("/Replicator/look_at_target")
        UsdGeom.XformCommonAPI(target_prim).SetTranslate((cx, cy, target_z))

        # Aim the D455: desired camera orientation puts the optical axis (-Z, USD camera
        # convention) on the eye->target ray, then rolls CAMERA_ROLL_DEG about the optical
        # axis (physically rotated sensor). The mount matrix compensates for the camera's
        # rest orientation inside the asset (measured at setup as CAM_REST_ROT_INV).
        eye = Gf.Vec3d(wx, wy, CAMERA_HEIGHT)
        target = Gf.Vec3d(cx, cy, target_z)
        cam_to_world = Gf.Matrix4d().SetLookAt(eye, target, Gf.Vec3d(0.0, 0.0, 1.0)).GetInverse()
        lookat_rot = Gf.Matrix4d().SetRotate(
            cam_to_world.ExtractRotationMatrix().GetOrthonormalized().ExtractRotation()
        )
        roll = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), CAMERA_ROLL_DEG))
        desired_cam_rot = roll * lookat_rot
        mount_mat = CAM_REST_ROT_INV * desired_cam_rot
        mount_mat.SetTranslateOnly(eye)
        mount_matrix_op.Set(mount_mat)

        # Local SphereLight illumination (positioned above the physical cart center)
        cy_actual = cy - 1.214 * math.sin(cyaw_rad)
        light_prim = stage.GetPrimAtPath("/Replicator/Lights/SphereLight")
        UsdGeom.XformCommonAPI(light_prim).SetTranslate((cx, cy_actual, 3.0))
        rep.functional.modify.attribute(spherelight, "inputs:intensity", float(rng.generator.uniform(80000.0, 300000.0)))
        rep.functional.modify.attribute(spherelight, "inputs:color", tuple(float(c) for c in rng.generator.uniform((0.7, 0.7, 0.7), (1.0, 1.0, 1.0))))

        # Distractor placement (collision-free)
        body_cx = cx - CART_BODY_OFFSET * math.cos(cyaw_rad)
        body_cy = cy - CART_BODY_OFFSET * math.sin(cyaw_rad)
        
        placed_props = []
        for j, clutter_prim in enumerate(clutter_prims):
            placed = False
            for _ in range(100):
                px = float(rng.generator.uniform(-5.0, 5.0))
                py = float(rng.generator.uniform(-5.0, 5.0))
                
                # Rule A: Line-of-sight clearance (camera <-> cart front)
                if get_distance_to_segment((px, py), (wx, wy), (cx, cy)) < 0.6:
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
                    
                placed_props.append((px, py))
                placed = True
                break
            
            prim_path = get_path_str(clutter_prim)
            prim = stage.GetPrimAtPath(prim_path)
            xform = UsdGeom.XformCommonAPI(prim)
            if placed:
                xform.SetTranslate((px, py, 0.0))
                rand_rot_z = float(rng.generator.uniform(0.0, 360.0))
                xform.SetRotate((0.0, 0.0, rand_rot_z))
            else:
                xform.SetTranslate((10.0 + j * 2.0, 10.0, -1000.0))
                xform.SetRotate((0.0, 0.0, 0.0))

        # Flush this frame's USD edits to the renderer before capturing: without an app
        # update, edits reach the render one step late (first frame duplicated, per-frame
        # data trailing the randomization by one, last frame never rendered).
        simulation_app.update()

        # Capture frame (hydra texture updates stay enabled)
        rep.orchestrator.step(rt_subframes=6, delta_time=0.0)

    print(">>> Waiting for disk dispatch...")
    rep.orchestrator.wait_until_complete()

    written = writer._frame_id - writer._skipped_frames
    print(f">>> Scene {scene_idx + 1}: wrote {written}/{writer._frame_id} frames with a "
          f"visible cart ({writer._skipped_frames} skipped as unlabeled)")

    # Detach per scene; the next scene re-initializes and re-attaches with fresh output dirs.
    writer.detach()
    depth_writer.detach()

# Clean up render products at the end (writers are detached per scene above)
# NOTE: depth_sensor's underlying hydra texture is torn down by SingleViewDepthCameraSensor's
# own __del__ (there's no UsdRender.Product.destroy() to call -- see depth_render_product_path
# above), so only the RGB render_product needs an explicit .destroy() here.
for name, cleanup in [
    ("render_product", render_product.destroy),
]:
    try:
        cleanup()
    except Exception as e:
        print(f">>> WARNING: cleanup of {name} failed (likely never attached): {e}", flush=True)

print(f"\n>>> Generation complete. Temp scenes are in {OUTPUT_DIR}_temp_scene_*")
print(">>> Starting shuffled consolidation...")
try:
    from consolidate_dataset import consolidate_datasets
    consolidate_datasets(OUTPUT_DIR, num_scenes)
except Exception as e:
    print(f"ERROR during consolidation: {e}")
simulation_app.close()
