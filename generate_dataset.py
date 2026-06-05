# generate_dataset.py
# Synthetic Dataset Generation script using Omniverse Replicator

from isaacsim import SimulationApp
import os

# 1. Start the simulation application headless
simulation_app = SimulationApp({"headless": True})

import omni.usd
import omni.replicator.core as rep

# 2. Open NVIDIA's hosted Simple Warehouse USD scene
warehouse_url = "http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.0/Isaac/Environments/Simple_Warehouse/warehouse.usd"
print(f">>> Loading warehouse environment from: {warehouse_url}")
omni.usd.get_context().open_stage(warehouse_url)

# 3. Path to the cart mesh inside the repository
cart_mesh_path = os.path.abspath("./meshes/colruyt_cart.stl")
if not os.path.exists(cart_mesh_path):
    print(f"\nERROR: Cart mesh not found at {cart_mesh_path}.")
    print("Please make sure you have copied colruyt_cart.stl to the ./meshes/ directory.")
    simulation_app.close()
    exit(1)

# 4. Set up the Replicator generation pipeline
print(">>> Initializing Replicator pipeline...")
with rep.new_layer():
    # Load cart mesh and assign class semantic for segmentation mask labeling
    cart = rep.create.from_usd(cart_mesh_path, semantics=[("class", "industrial_cart")])
    
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
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        output_dir="_output_dataset",
        rgb=True,
        semantic_segmentation=True
    )
    writer.attach([render_product])
    
    # Run the orchestrator to capture a quick test set of 5 frames
    print(">>> Starting synthetic generation...")
    rep.orchestrator.run(num_frames=5)
    print(">>> Generation finished. Datasets saved to ./_output_dataset")

# Close the application
simulation_app.close()
