# generate_dataset.py
# Synthetic Dataset Generation script using Omniverse Replicator

import os
import sys
import random
import math
import shutil

# Disable Omniverse Hub (OmniHub) daemon to prevent connection loops in container
os.environ["OMNICLIENT_HUB_MODE"] = "disabled"
os.environ["OMNICLIENT_USE_HUB"] = "0"

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Disable RTX driver verification check for driver compatibility on daman host
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

# Enable full verbose engine logging for debugging headless Vulkan/denoiser initialization
sys.argv.append("--/log/level=verbose")
sys.argv.append("--/log/consoleLogLevel=verbose")
sys.argv.append("--/log/fileLogLevel=verbose")

# Force RTX Real-Time 2.0 (path-tracing based) renderer before SimulationApp initializes.
# Isaac Sim 6.0 no longer supports traditional rasterization (RaytracedLighting).
# Both Real-Time 2.0 and Interactive modes use a path-tracing based core.
sys.argv.append("--/rtx/rendermode=RealTimePathTracing")

# Parse custom command-line arguments before SimulationApp consumes them
CART_TYPE = "picanol"
if "--cart" in sys.argv:
    try:
        idx = sys.argv.index("--cart")
        if idx + 1 < len(sys.argv):
            CART_TYPE = sys.argv[idx + 1].lower()
        sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
    except ValueError:
        pass

NUM_FRAMES = 5  # default/validation run
if "--frames" in sys.argv:
    try:
        idx = sys.argv.index("--frames")
        if idx + 1 < len(sys.argv):
            NUM_FRAMES = int(sys.argv[idx + 1])
        sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
    except ValueError:
        pass

from omni.isaac.kit import SimulationApp

# 1. Start the simulation application headless
simulation_app = SimulationApp({"headless": True, "renderer": "RealTimePathTracing"})

# Inject compatibility shim for Warp 1.15+ (required by Replicator in older configurations)
import types
try:
    import warp
    if not hasattr(warp, "context"):
        context_module = types.ModuleType("warp.context")
        context_module.Kernel = warp.Kernel
        sys.modules["warp.context"] = context_module
        warp.context = context_module
        print(">>> Warp context compatibility shim successfully applied.")
except Exception as e:
    print(f">>> Warp context check: {e}")


import omni.usd
import omni.replicator.core as rep
from omni.isaac.core.utils.semantics import add_update_semantics

# Enable the asset converter extension using Isaac Sim utility
from omni.isaac.core.utils.extensions import enable_extension
enable_extension("omni.kit.asset_converter")
import omni.kit.asset_converter

# 2. Resolve target USD cart model path
if CART_TYPE == "colruyt":
    cart_usd_path = os.path.abspath("./meshes/colruyt.usd")
else:
    cart_usd_path = os.path.abspath("./meshes/picanolcart.usd")

if not os.path.exists(cart_usd_path):
    print(f"\nERROR: Pre-processed USD model not found at {cart_usd_path}.")
    print("Please run 'apply_semantics.py' first to generate the labeled USD files.")
    simulation_app.close()
    exit(1)
print(f">>> Loaded target USD model: {cart_usd_path}")

# 3. Open NVIDIA's hosted Simple Warehouse USD scenes list
from omni.isaac.core.utils.nucleus import get_assets_root_path
assets_root_path = get_assets_root_path()
if assets_root_path:
    ISAAC_ASSETS = f"{assets_root_path}/Isaac"
else:
    ISAAC_ASSETS = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac"

# Multiple warehouse scenes for diversity
WAREHOUSE_SCENES = [
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse_with_forklifts.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse_multiple_shelves.usd",
    f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/full_warehouse.usd",
]

# Part name → semantic class label mapping
# Must match the Blender object names used in the USD export.
CART_SEMANTIC_MAP = {
    "cart_body":    "cart_body",
    "left_handle":  "left_handle",
    "right_handle": "right_handle",
    "colruyt_cart": "cart_body",
}

# Define output directory
output_directory = os.path.abspath(f"./_output_dataset_{CART_TYPE}")

# Camera geometry constants
CAMERA_HEIGHT = 0.304  # meters
TILT_ANGLE = 30.0      # degrees (pitch tilt upward)
L_HALF = 0.761 if CART_TYPE == "colruyt" else 0.88

# Helper function to compute distance between a point P and line segment AB
def get_distance_to_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    
    ab_x = bx - ax
    ab_y = by - ay
    ab_len_sq = ab_x**2 + ab_y**2
    if ab_len_sq == 0:
        return math.sqrt((px - ax)**2 + (py - ay)**2)
        
    ap_x = px - ax
    ap_y = py - ay
    
    t = (ap_x * ab_x + ap_y * ab_y) / ab_len_sq
    t = max(0.0, min(1.0, t))
    
    cx = ax + t * ab_x
    cy = ay + t * ab_y
    
    return math.sqrt((px - cx)**2 + (py - cy)**2)

# Helper function to consolidate files from temp scene directories
def consolidate_datasets(output_dir, num_scenes):
    os.makedirs(output_dir, exist_ok=True)
    global_frame_idx = 0
    
    for scene_idx in range(num_scenes):
        temp_dir = os.path.abspath(f"{output_dir}_temp_scene_{scene_idx}")
        if not os.path.exists(temp_dir):
            continue
            
        print(f">>> Consolidating temporary files from: {temp_dir}")
        for root, dirs, files in os.walk(temp_dir):
            print(f">>> Found {len(files)} files in: {root}")
            frame_files = {}
            for file in files:
                name, ext = os.path.splitext(file)
                parts = name.split('_')
                if len(parts) > 0 and parts[-1].isdigit():
                    idx = int(parts[-1])
                    prefix = '_'.join(parts[:-1])
                else:
                    idx = 0
                    prefix = name
                if idx not in frame_files:
                    frame_files[idx] = []
                frame_files[idx].append((prefix, ext, file, os.path.join(root, file)))
            
            for local_idx in sorted(frame_files.keys()):
                for prefix, file_ext, original_file, src_path in frame_files[local_idx]:
                    new_filename = f"{prefix}_{global_frame_idx:04d}{file_ext}"
                    rel_path = os.path.relpath(src_path, temp_dir)
                    rel_dir = os.path.dirname(rel_path)
                    
                    dest_dir = os.path.join(output_dir, rel_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    dest_path = os.path.join(dest_dir, new_filename)
                    shutil.move(src_path, dest_path)
                global_frame_idx += 1
                
        # Clean up temp folder
        try:
            shutil.rmtree(temp_dir)
            print(f">>> Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"WARNING: Could not remove {temp_dir}: {e}")
            
    print(f"\n>>> Consolidated dataset containing {global_frame_idx} frames successfully written to {output_dir}")

# Divide NUM_FRAMES among available scenes
num_scenes = len(WAREHOUSE_SCENES)
frames_per_scene = NUM_FRAMES // num_scenes
remaining_frames = NUM_FRAMES % num_scenes

scene_frame_counts = [frames_per_scene] * num_scenes
for i in range(remaining_frames):
    scene_frame_counts[i] += 1

print(f">>> Configured total generation: {NUM_FRAMES} frames across {num_scenes} environments.")
for idx, url in enumerate(WAREHOUSE_SCENES):
    print(f"  - Scene {idx+1}: {os.path.basename(url)} -> {scene_frame_counts[idx]} frames")

# Execute generation loop across multiple USD environments
for scene_idx, warehouse_url in enumerate(WAREHOUSE_SCENES):
    frames_for_this_scene = scene_frame_counts[scene_idx]
    if frames_for_this_scene <= 0:
        continue
        
    print(f"\n>>> ═══════════════════════════════════════════════════════")
    print(f">>>  GENERATING IN SCENE {scene_idx + 1}/{num_scenes}: {os.path.basename(warehouse_url)}")
    print(f">>>  FRAMES FOR THIS SCENE: {frames_for_this_scene}")
    print(f">>> ═══════════════════════════════════════════════════════")
    
    print(f">>> Loading environment from: {warehouse_url}")
    omni.usd.get_context().open_stage(warehouse_url)
    
    # 4. Generate sequences for the current scene
    cart_positions = []
    cart_rotations = []
    camera_positions = []
    look_at_positions = []
    
    num_distractors = 6  # 3 props * 2 instances each
    clutter_positions = [[] for _ in range(num_distractors)]
    
    for _ in range(frames_for_this_scene):
        # 1. Randomize cart position on warehouse floor
        cx = random.uniform(-4.0, 4.0)
        cy = random.uniform(-4.0, 4.0)
        cz = 0.0
        cart_positions.append((cx, cy, cz))
        
        # 2. Randomize cart yaw (0 to 360 degrees)
        cyaw = random.uniform(0.0, 360.0)
        cart_rotations.append((0.0, 0.0, cyaw))
        
        # 3. Camera position relative to the front surface of the cart (1.0m to 2.0m, +/- 45 deg)
        d = random.uniform(1.0, 2.0)
        alpha = random.uniform(-45.0, 45.0)
        
        alpha_rad = math.radians(alpha)
        # Camera coordinates in the cart's local frame
        local_x = L_HALF + d * math.cos(alpha_rad)
        local_y = d * math.sin(alpha_rad)
        
        # Rotate local offset by cart yaw:
        cyaw_rad = math.radians(cyaw)
        wx = cx + local_x * math.cos(cyaw_rad) - local_y * math.sin(cyaw_rad)
        wy = cy + local_x * math.sin(cyaw_rad) + local_y * math.cos(cyaw_rad)
        wz = CAMERA_HEIGHT
        camera_positions.append((float(wx), float(wy), float(wz)))
        
        # 4. Look-at target (centered at the front surface, Z height matching the 30-degree camera tilt)
        target_z = CAMERA_HEIGHT + d * math.tan(math.radians(TILT_ANGLE))
        
        # Add small random offsets (de-centering) for robustness
        offset_x = random.uniform(-0.1, 0.1)
        offset_y = random.uniform(-0.1, 0.1)
        offset_z = random.uniform(-0.05, 0.05)
        
        # Look-at target coordinates relative to the cart's front center in local frame
        local_tx = L_HALF + offset_x
        local_ty = offset_y
        
        tx = cx + local_tx * math.cos(cyaw_rad) - local_ty * math.sin(cyaw_rad)
        ty = cy + local_tx * math.sin(cyaw_rad) + local_ty * math.cos(cyaw_rad)
        tz = target_z + offset_z
        look_at_positions.append((float(tx), float(ty), float(tz)))
        
        # 5. Generate collision-free and occlusion-free distractor positions
        placed_props = []
        for j in range(num_distractors):
            placed = False
            for attempt in range(100):
                px = random.uniform(-5.0, 5.0)
                py = random.uniform(-5.0, 5.0)
                
                # Rule A: Enforce clearance corridor between camera (wx, wy) and cart front (tx, ty)
                d_los = get_distance_to_segment((px, py), (wx, wy), (tx, ty))
                if d_los < 0.6:
                    continue  # Too close to view line-of-sight
                    
                # Rule B: Prevent mesh intersection with the cart body
                d_cart = math.sqrt((px - cx)**2 + (py - cy)**2)
                if d_cart < (L_HALF + 0.4):
                    continue  # Colliding with the cart
                    
                # Rule C: Prevent distractor from clipping through the camera
                d_cam = math.sqrt((px - wx)**2 + (py - wy)**2)
                if d_cam < 0.6:
                    continue  # Too close to the camera lens
                    
                # Rule D: Prevent distractors from overlapping each other
                overlap = False
                for ox, oy in placed_props:
                    if math.sqrt((px - ox)**2 + (py - oy)**2) < 0.6:
                        overlap = True
                        break
                if overlap:
                    continue
                    
                # Location satisfies all rules
                clutter_positions[j].append((float(px), float(py), 0.0))
                placed_props.append((px, py))
                placed = True
                break
                
            if not placed:
                # Fallback: place prop far away if no safe spot was resolved after 100 attempts
                clutter_positions[j].append((10.0 + j * 2.0, 10.0, 0.0))

    # 5. Setup the Replicator generation pipeline for this scene
    with rep.new_layer():
        # Load cart USD (no top-level semantics – applied per-prim below)
        cart = rep.create.from_usd(cart_usd_path)

        # Pump the app once so the USD reference is fully resolved in the stage
        simulation_app.update()

        # Apply per-prim semantics as local stage opinions
        stage = omni.usd.get_context().get_stage()
        for prim in stage.Traverse():
            label = CART_SEMANTIC_MAP.get(prim.GetName())
            if label:
                add_update_semantics(prim, semantic_label=label, type_label="class")
                print(f">>> Semantic applied: '{label}' → {prim.GetPath()}")
        
        # Force real-time compute denoisers since NGX (DLSS/OptiX) fails headlessly
        rep.settings.carb_settings("/rtx/indirectDiffuse/denoiser/enabled", True)
        rep.settings.carb_settings("/rtx/reflections/denoiser/enabled", True)
        rep.settings.carb_settings("/rtx/post/aa/op", 1)  # Force TAA (1) instead of DLSS (3)
        rep.settings.carb_settings("/rtx/pathtracing/optixDenoiser/enabled", False)
        rep.settings.carb_settings("/omni/replicator/RTSubframes", 4)

        # Create Scene Primitives
        domelight = rep.create.light(light_type="dome")
        distantlight = rep.create.light(light_type="distant")
        
        # Camera matching physical RealSense D455i rotated 90 degrees (portrait)
        camera = rep.create.camera(
            focal_length=16.764,         # mm – keeping pixel focal length = 640.0 on 800px width
            horizontal_aperture=20.955,  # mm – standard 1" sensor default
            clipping_range=(0.1, 10000.0),  # near=10cm prevents floor-clipping
        )
        
        # Look-at target xform (invisible) for de-centering and camera targeting
        look_at_target = rep.create.xform(name="look_at_target")

        # Load warehouse clutter props (distractors, no semantics)
        PROPS_BASE = f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/Props"
        prop_urls = [
            f"{PROPS_BASE}/SM_PaletteA_01.usd",
            f"{PROPS_BASE}/SM_CardBoxD_04.usd",
            f"{PROPS_BASE}/S_TrafficCone.usd",
        ]
        print(">>> Loading warehouse clutter props...")
        clutter_prims = []
        for url in prop_urls:
            for i in range(2):
                prim = rep.create.from_usd(url)
                clutter_prims.append(prim)
                print(f">>> Loaded clutter prop: {url} (instance {i})")

        # Define Frame Randomizer Function (Updates all poses & lighting)
        def randomize_scene():
            with cart:
                rep.modify.pose(
                    position=rep.distribution.sequence(cart_positions),
                    rotation=rep.distribution.sequence(cart_rotations),
                )
            with look_at_target:
                rep.modify.pose(
                    position=rep.distribution.sequence(look_at_positions),
                )
            with camera:
                rep.modify.pose(
                    position=rep.distribution.sequence(camera_positions),
                    look_at=look_at_target,
                )
            for j, prim in enumerate(clutter_prims):
                with prim:
                    rep.modify.pose(
                        position=rep.distribution.sequence(clutter_positions[j]),
                        rotation=rep.distribution.uniform((0, 0, 0), (0, 0, 360)),
                    )
            with domelight:
                rep.modify.attribute("inputs:intensity", rep.distribution.uniform(100.0, 2500.0))
                rep.modify.attribute("inputs:color", rep.distribution.uniform((0.5, 0.5, 0.5), (1.0, 1.0, 1.0)))
            with distantlight:
                rep.modify.attribute("inputs:intensity", rep.distribution.uniform(1000.0, 5000.0))
                rep.modify.attribute("inputs:color", rep.distribution.uniform((0.6, 0.6, 0.6), (1.0, 1.0, 1.0)))
                rep.modify.pose(rotation=rep.distribution.uniform((0, 0, 0), (360, 360, 360)))
            return cart.node

        # Register the randomizer (triggered explicitly via orchestrator.step())
        rep.randomizer.register(randomize_scene)

        with rep.trigger.on_frame(num_frames=1):
            rep.randomizer.randomize_scene()

        render_product = rep.create.render_product(camera, resolution=(800, 1280))
        
        # Configure output directory for the current scene (temporary directory)
        scene_output_directory = os.path.abspath(f"{output_directory}_temp_scene_{scene_idx}")
        print(f">>> Configured scene temporary output directory: {scene_output_directory}")
        
        writer = rep.writers.get("BasicWriter")
        writer.initialize(
            output_dir=scene_output_directory,
            rgb=True,
            semantic_segmentation=True,
            distance_to_image_plane=True,  # Enable depth map generation (meters, float32, .npy)
            bounding_box_3d=True,          # 3D OBB corners + world transform → 6D pose GT
            camera_params=True,            # Intrinsics K per frame (needed for projection)
        )
        writer.attach([render_product])

    # Disable automatic capture-on-play (we control capture via step())
    rep.orchestrator.set_capture_on_play(False)

    # Warm up the renderer so annotator buffers are initialized
    for _ in range(5):
        simulation_app.update()

    print(">>> Starting synthetic generation for this scene...")
    for frame_i in range(frames_for_this_scene):
        print(f">>>   Capturing frame {frame_i + 1}/{frames_for_this_scene}...")
        rep.orchestrator.step(rt_subframes=4, delta_time=0.0)

    print(">>> Generation finished for this scene. Waiting for disk dispatch...")
    rep.orchestrator.wait_until_complete()

# 6. Consolidate and clean up the temporary directories
consolidate_datasets(output_directory, num_scenes)

# Close the application
simulation_app.close()
