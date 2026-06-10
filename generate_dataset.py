# generate_dataset.py
# Synthetic Dataset Generation script using Omniverse Replicator

import os
import sys

# Disable Omniverse Hub (OmniHub) daemon to prevent connection loops in container
os.environ["OMNICLIENT_HUB_MODE"] = "disabled"
os.environ["OMNICLIENT_USE_HUB"] = "0"

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Disable RTX driver verification check for driver compatibility on daman host
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

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

from isaacsim import SimulationApp
import os

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


import sys
import omni.usd
import omni.replicator.core as rep
from isaacsim.core.utils.semantics import add_labels

# Enable the asset converter extension using Isaac Sim utility
from isaacsim.core.utils.extensions import enable_extension
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

# 3. Open NVIDIA's hosted Simple Warehouse USD scene
from isaacsim.storage.native import get_assets_root_path
assets_root_path = get_assets_root_path()
if assets_root_path:
    ISAAC_ASSETS = f"{assets_root_path}/Isaac"
else:
    # Fallback to public S3 bucket for version 6.0
    ISAAC_ASSETS = "http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac"

warehouse_url = f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/warehouse.usd"
print(f">>> Loading warehouse environment from: {warehouse_url}")
omni.usd.get_context().open_stage(warehouse_url)

# 4. Set up the Replicator generation pipeline
print(">>> Initializing Replicator pipeline...")
# Part name → semantic class label mapping
# Must match the Blender object names used in the USD export.
CART_SEMANTIC_MAP = {
    "cart_body":    "cart_body",
    "left_handle":  "left_handle",
    "right_handle": "right_handle",
    "colruyt_cart": "cart_body",
}

# Define output directory at module scope (needed after new_layer block exits)
output_directory = os.path.abspath(f"./_output_dataset_{CART_TYPE}")

# Generate constrained camera/cart coordinates for the sequences
import random
import math

# Camera geometry constants
CAMERA_HEIGHT = 0.304  # meters
TILT_ANGLE = 30.0      # degrees (pitch tilt upward)
L_HALF = 0.761 if CART_TYPE == "colruyt" else 0.88

cart_positions = []
cart_rotations = []
camera_positions = []
look_at_positions = []

for _ in range(NUM_FRAMES):
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
    
    # Look-at target coordinates relative to the cart's front center in local frame: (L_HALF + offset_x, offset_y)
    local_tx = L_HALF + offset_x
    local_ty = offset_y
    
    tx = cx + local_tx * math.cos(cyaw_rad) - local_ty * math.sin(cyaw_rad)
    ty = cy + local_tx * math.sin(cyaw_rad) + local_ty * math.cos(cyaw_rad)
    tz = target_z + offset_z
    look_at_positions.append((float(tx), float(ty), float(tz)))

with rep.new_layer():
    # Load cart USD (no top-level semantics – applied per-prim below)
    cart = rep.create.from_usd(cart_usd_path)

    # Pump the app once so the USD reference is fully resolved in the stage
    simulation_app.update()

    # Apply per-prim semantics as local stage opinions (required by the
    # Replicator annotator – pre-baked USD attributes are not sufficient).
    stage = omni.usd.get_context().get_stage()
    for prim in stage.Traverse():
        label = CART_SEMANTIC_MAP.get(prim.GetName())
        if label:
            add_labels(prim, [label], "class")
            print(f">>> Semantic applied: '{label}' → {prim.GetPath()}")
    
    # ── Force real-time compute denoisers since NGX (DLSS/OptiX) fails headlessly ──
    rep.settings.carb_settings("/rtx/indirectDiffuse/denoiser/enabled", True)
    rep.settings.carb_settings("/rtx/reflections/denoiser/enabled", True)
    rep.settings.carb_settings("/rtx/post/aa/op", 1)  # Force TAA (1) instead of DLSS (3)
    rep.settings.carb_settings("/rtx/pathtracing/optixDenoiser/enabled", False)
    rep.settings.carb_settings("/omni/replicator/RTSubframes", 4)

    # ── Create Scene Primitives ────────────────────────────────────────────────
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

    # ── Load warehouse clutter props (distractors, no semantics) ──────────────
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
    clutter_group = rep.create.group(clutter_prims)

    # ── Define Frame Randomizer Function (Updates all poses & lighting) ────────
    def randomize_scene():
        # Update sequences (must be evaluated inside the trigger to advance)
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
        with clutter_group:
            rep.modify.pose(
                position=rep.distribution.uniform((-5.0, -5.0, 0.0), (5.0, 5.0, 0.0)),
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

    # Register the randomizer and connect it to the frame trigger
    rep.randomizer.register(randomize_scene)

    with rep.trigger.on_frame(max_execs=NUM_FRAMES):
        rep.randomizer.randomize_scene()

    render_product = rep.create.render_product(camera, resolution=(800, 1280))
    
    # Configure the output writer (saving RGB images and Semantic Segmentation masks)
    print(f">>> Configured dataset output directory: {output_directory}")
    
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        output_dir=output_directory,
        rgb=True,
        semantic_segmentation=True,
        distance_to_image_plane=True, # Enable depth map generation (meters, float32, .npy)
        bounding_box_3d=True,    # 3D OBB corners + world transform → 6D pose GT
        camera_params=True,      # Intrinsics K per frame (needed for projection)
    )
    writer.attach([render_product])

# ── Execute generation OUTSIDE the new_layer block ────────────────────────────
# The graph must be fully defined (layer sealed) before the orchestrator runs.
# num_frames is controlled solely by on_frame(num_frames=5) above;
# orchestrator.run() with no args stops when all triggers are exhausted.

# ── Renderer diagnostics (identify active render backend and dump settings) ───
import carb
_settings = carb.settings.get_settings()

print(">>> ═══════════════════════════════════════════════════════")
print(">>>  RENDERER DIAGNOSTICS & SETTINGS DUMP")
print(">>> ═══════════════════════════════════════════════════════")
print(f">>> [DIAG] Render mode:                    {_settings.get('/rtx/rendermode')}")
print(f">>> [DIAG] RT Subframes:                    {_settings.get('/omni/replicator/RTSubframes')}")

keys_to_query = [
    "/rtx/rendermode",
    "/rtx/pathtracing/enabled",
    "/rtx/pathtracing/optixDenoiser/enabled",
    "/rtx/pathtracing/optixDenoiser/execMode",
    "/rtx/post/aa/op",
    "/rtx/post/dlss/enabled",
    "/rtx/post/dlss/execMode",
    "/rtx/post/dlss/rayReconstruction",
    "/rtx/post/dlss/rayReconstructionEnabled",
    "/rtx/post/denoiser/enabled",
    "/rtx/post/denoiser/execMode",
    "/rtx/post/spatialDenoiser/enabled",
    "/rtx/post/temporalDenoiser/enabled",
    "/rtx/directLighting/denoiser/enabled",
    "/rtx/indirectDiffuse/denoiser/enabled",
    "/rtx/indirectSpecular/denoiser/enabled",
    "/rtx/post/tonemap/denoiser/enabled",
    "/rtx/post/rtxdlss/enabled",
    "/rtx/reflections/denoiser/enabled",
    "/rtx/shadows/denoiser/enabled",
    "/rtx/ambientOcclusion/denoiser/enabled",
    "/rtx/globalIllumination/denoiser/enabled"
]

print(">>> ───────────────────────────────────────────────────────")
print(">>>  SETTINGS DUMP (denois, dlss, spp, rendermode)")
print(">>> ───────────────────────────────────────────────────────")
for k in keys_to_query:
    val = _settings.get(k)
    if val is not None:
        print(f">>> [DUMP] {k} = {val}")
print(">>> ═══════════════════════════════════════════════════════")

print(">>> Starting synthetic generation...")
rep.orchestrator.run()

# Wait until orchestrator starts and finishes
while not rep.orchestrator.get_is_started():
    simulation_app.update()
while rep.orchestrator.get_is_started():
    simulation_app.update()

print(">>> Generation finished. Waiting for disk dispatch...")
rep.BackendDispatch.wait_until_done()
print(f">>> Datasets saved successfully to {output_directory}")

# Close the application
simulation_app.close()
