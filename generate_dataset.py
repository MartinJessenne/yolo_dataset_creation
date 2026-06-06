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
with rep.new_layer():
    # Load cart USD. Semantic labels (cart_body / left_handle / right_handle)
    # are pre-baked per-prim by apply_semantics.py – no top-level override needed.
    cart = rep.create.from_usd(cart_usd_path)
    
    with cart:
        # Randomize cart position and orientation on the warehouse floor
        rep.modify.pose(
            position=rep.distribution.uniform((-3.0, -3.0, 0.0), (3.0, 3.0, 0.0)),
            rotation=rep.distribution.uniform((0, 0, 0), (0, 0, 360))
        )
        
    # Create a camera pointing at the cart
    camera = rep.create.camera(position=(0, -6, 2.5), look_at=cart)
    render_product = rep.create.render_product(camera, resolution=(640, 640))
    
    # Configure the output writer (saving RGB images and Semantic Segmentation masks)
    output_directory = os.path.abspath("./_output_dataset")
    print(f">>> Configured dataset output directory: {output_directory}")
    
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        output_dir=output_directory,
        rgb=True,
        semantic_segmentation=True,
        bounding_box_3d=True,    # 3D OBB corners + world transform → 6D pose GT
        camera_params=True,      # Intrinsics K per frame (needed for projection)
    )
    writer.attach([render_product])
    
    # Run the orchestrator to capture 5 frames for validation
    print(">>> Starting synthetic generation...")
    rep.orchestrator.run(num_frames=5)
    
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
