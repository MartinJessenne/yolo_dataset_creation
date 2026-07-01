# test_d455_ros2.py
import os
import sys

# Disable OmniHub cache connection completely
os.environ["OMNICLIENT_HUB_MODE"] = "disabled"
os.environ["OMNICLIENT_USE_HUB"] = "0"

# Disable RTX driver verification
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

from isaacsim import SimulationApp

# Enable ROS2 extension and cameras in headless mode
config = {
    "headless": True,
    "enable_cameras": True, 
    "renderer": "RayTracedLighting"
}
simulation_app = SimulationApp(config)

# Enable the ROS2 bridge extension programmatically
from isaacsim.core.utils.extensions import enable_extension
enable_extension("isaacsim.ros2.bridge")

import numpy as np
from isaacsim.core.api import World
import isaacsim.core.utils.prims as prim_utils
import omni.replicator.core as rep
import omni.client
from isaacsim.storage.native import get_assets_root_path

# Set omni.client log level to ERROR to suppress warning spam
omni.client.set_log_level(omni.client.LogLevel.ERROR)

# 1. Initialize World & Spawn your D455
world = World(stage_units_in_meters=1.0)
world.scene.add_default_ground_plane()

root = get_assets_root_path()
d455_usd_path = f"{root}/Isaac/Sensors/RealSense/D455/rsd455.usd"
prim_path = "/World/RealSense_D455"
rgb_camera_path = f"{prim_path}/RSD455/Camera_OmniVision_OV9782_Color"

print(f"Spawning D455 from: {d455_usd_path}")
prim_utils.create_prim(prim_path=prim_path, usd_path=d455_usd_path, position=np.array([0.0, 0.0, 1.0]))

# Wait for reference to load and renderer to initialize
for _ in range(50):
    simulation_app.update()

# 2. In Isaac Sim 6.0+, control rate via OmniSensorAPI instead of deprecated frameSkipCount
# (Optional: define rate here if you want to cap the topic frequency)

# 3. Create a Single Render Product for both sensors to guarantee flawless alignment
# We target the specific D455 resolution of 1280 x 800
print(f"Creating render product for camera: {rgb_camera_path} at 1280x800")
render_product = rep.create.render_product(rgb_camera_path, resolution=(1280, 800))

# 4. Initialize the ROS2 Bridge and link the synchronized streams
# 'rgb' publishes sensor_msgs/msg/Image
rgb_writer = rep.writers.get("LdrColorSDROS2PublishImage")
rgb_writer.initialize(
    topicName="camera/color/image_raw",
    frameId="camera_color_optical_frame",
    nodeNamespace=""
)
rgb_writer.attach([render_product])

# 'depth' automatically maps to sensor_msgs/msg/Image (32FC1 float depth in meters)
# Because it relies on the same render_product, it maps perfectly 1:1 to the RGB pixels
depth_writer = rep.writers.get("DistanceToImagePlaneSDROS2PublishImage")
depth_writer.initialize(
    topicName="camera/aligned_depth_to_color/image_raw",
    frameId="camera_color_optical_frame",  # Use the identical frame ID to reflect alignment
    nodeNamespace=""
)
depth_writer.attach([render_product])

# 5. Spin up the simulation
world.reset()

print("ROS2 Aligned Depth & RGB Topics active. Running loop for 20 frames...")
try:
    for frame in range(20):
        print(f"Stepping frame {frame+1}/20")
        # You must step with render=True to compute frames for the ROS bridge
        world.step(render=True)
except KeyboardInterrupt:
    pass

simulation_app.close()
print("Done.")
