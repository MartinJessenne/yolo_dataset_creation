# generate_dataset.py
# Synthetic Dataset Generation script using Omniverse Replicator

import sys
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from isaacsim import SimulationApp
import os

# 1. Start the simulation application headless
simulation_app = SimulationApp({"headless": True})


import sys
import omni.usd
import omni.replicator.core as rep
from omni.isaac.core.utils.semantics import add_update_semantics

# Enable the asset converter extension using Isaac Sim utility
from omni.isaac.core.utils.extensions import enable_extension
enable_extension("omni.kit.asset_converter")
import omni.kit.asset_converter

# 2. Convert DAE cart mesh to USD format
cart_dae_path = os.path.abspath("./meshes/picanolcart.dae")
cart_usd_path = os.path.abspath("./meshes/picanolcart.usd")

if not os.path.exists(cart_dae_path):
    print(f"\nERROR: Cart DAE mesh not found at {cart_dae_path}.")
    print("Please make sure you have picanolcart.dae in the ./meshes/ directory.")
    simulation_app.close()
    exit(1)

# Programmatically run the asset converter
if not os.path.exists(cart_usd_path):
    print(f">>> Converting {cart_dae_path} to USD...")
    converter_manager = omni.kit.asset_converter.get_instance()
    context = omni.kit.asset_converter.AssetConverterContext()
    task = converter_manager.create_converter_task(cart_dae_path, cart_usd_path, None, context)
    
    import asyncio
    # Schedule the task on the event loop and pump the application loop until done
    future = asyncio.ensure_future(task.wait_until_finished())
    while not future.done():
        simulation_app.update()
        
    success = future.result()
    if not success:
        print("ERROR: Mesh conversion to USD failed.")
        simulation_app.close()
        exit(1)
    print(">>> Mesh conversion completed successfully.")

# 3. Open NVIDIA's hosted Simple Warehouse USD scene
warehouse_url = "http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Environments/Simple_Warehouse/warehouse.usd"
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
}

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
            add_update_semantics(prim, label, "class")
            print(f">>> Semantic applied: '{label}' → {prim.GetPath()}")
    
    # ── Create Scene Primitives ────────────────────────────────────────────────
    # Initialize camera, dome (ambient) light, and distant (directional) light.
    # We create them once here and then randomize their attributes every frame.
    domelight = rep.create.light(light_type="dome")
    distantlight = rep.create.light(light_type="distant")
    
    # NOTE: focal_length is derived from the Gazebo simulated D455i color camera HFOV (90°):
    #   f = horizontal_aperture / (2 * tan(HFOV/2))
    #     = 20.955 / (2 * tan(45°)) = 10.4775 mm
    # This matches the simulation camera intrinsics (fx = fy = 639.99768 on 1280x800 resolution)
    camera = rep.create.camera(
        focal_length=10.4775,        # mm – matches Gazebo color 90° HFOV
        horizontal_aperture=20.955,  # mm – standard 1" sensor default
    )
    
    # ── Robot-calibrated camera height parameter ──────────────────────────────
    CAMERA_HEIGHT = 0.304  # metres

    # ── Define Frame Randomizer Function ───────────────────────────────────────
    # Evaluates distributions and updates poses/attributes on every frame trigger.
    def randomize_scene():
        with cart:
            # Cart sits on the floor: Z=0 always.
            # X/Y randomized across a wide area to produce varied viewpoints.
            # Rotation only around Z (yaw) since the cart never tilts on flat floor.
            rep.modify.pose(
                position=rep.distribution.uniform((-4.0, -4.0, 0.0), (4.0, 4.0, 0.0)),
                rotation=rep.distribution.uniform((0, 0, 0), (0, 0, 360)),
            )
        with camera:
            rep.modify.pose(
                # Z is clamped to real robot height; XY sweeps a 9m × 9m arena
                position=rep.distribution.uniform(
                    (-4.5, -4.5, CAMERA_HEIGHT),
                    ( 4.5,  4.5, CAMERA_HEIGHT),
                ),
                look_at=cart,  # auto-computes correct pitch toward cart centroid
            )
        with domelight:
            rep.modify.attribute("inputs:intensity", rep.distribution.uniform(100.0, 2500.0))
            rep.modify.attribute("inputs:color", rep.distribution.uniform((0.5, 0.5, 0.5), (1.0, 1.0, 1.0)))
        with distantlight:
            rep.modify.attribute("inputs:intensity", rep.distribution.uniform(1000.0, 5000.0))
            rep.modify.attribute("inputs:color", rep.distribution.uniform((0.6, 0.6, 0.6), (1.0, 1.0, 1.0)))
            rep.modify.pose(rotation=rep.distribution.uniform((0, 0, 0), (360, 360, 360)))
        return [cart.node, camera.node, domelight.node, distantlight.node]

    # Register the randomizer and connect it to the frame trigger
    rep.randomizer.register(randomize_scene)

    with rep.trigger.on_frame():
        rep.randomizer.randomize_scene()

    render_product = rep.create.render_product(camera, resolution=(1280, 800))
    
    # Configure the output writer (saving RGB images and Semantic Segmentation masks)
    output_directory = os.path.abspath("./_output_dataset")
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
    
    # Run the orchestrator manually using step() to ensure frame-by-frame updates tick synchronously.
    # Standalone headless scripts can fail to advance the timeline with orchestrator.run().
    print(">>> Starting synthetic generation...")
    for frame_idx in range(5):
        print(f">>> Rendering frame {frame_idx + 1}/5...")
        simulation_app.update()
        rep.orchestrator.step()
        
    print(">>> Generation finished. Waiting for disk dispatch...")
    rep.BackendDispatch.wait_until_done()
    print(f">>> Datasets saved successfully to {output_directory}")

# Close the application
simulation_app.close()
