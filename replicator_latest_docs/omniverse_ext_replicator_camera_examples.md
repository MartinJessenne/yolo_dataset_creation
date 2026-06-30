---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html
---

# Camera Examples[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#camera-examples "Link to this heading")
The goal of this tutorial is to provide examples of common use cases for cameras in Omniverse Replicator. Below are a few examples of camera useage applied within a scene using Replicator APIs.
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#learning-objectives "Link to this heading")
Through this page you will see some highlighted camera examples and how to use them. However, for all information about replicator camera use consult the [API documentation](https://docs.omniverse.nvidia.com/py/replicator) .
## Set up[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#set-up "Link to this heading")
Each of the camera examples shown below are standalone scripts that can be run following the set up described in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up) and [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running).
## Creating a Camera and Setting Properties[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#creating-a-camera-and-setting-properties "Link to this heading")
Creating a camera and initializing its properties is straightforward. Below is a small snippet as an example, but the API documents all available options.

```
import omni.replicator.core as rep

# Create camera
camera = rep.create.camera(
    position=rep.distribution.uniform((0,0,0), (100, 100, 100)),
    rotation=(45, 45, 0),
    focus_distance=rep.distribution.normal(400.0, 100),
    f_stop=1.8,
)

```
Copy to clipboard
## Randomizing a camera’s position uniformly[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#randomizing-a-camera-s-position-uniformly "Link to this heading")
An example showing how to move a camera to random location within an area, chosen by a uniform distribution.

```
import omni.replicator.core as rep

# Randomize the camera position using basic uniform distribution

with rep.new_layer():

    # Create camera
    # https://docs.omniverse.nvidia.com/py/replicator/source/extensions/omni.replicator.core/docs/API.html#omni.replicator.core.create.camera
    camera = rep.create.camera(focus_distance=200,f_stop=0.5)

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(0, 0, 0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_output_camera_uniformpos", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    with rep.trigger.on_frame(num_frames=10):
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-500, 200, -500), (500, 500, 500)), look_at=(0,0,0))

```
Copy to clipboard
## Randomizing a camera’s position using a list[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#randomizing-a-camera-s-position-using-a-list "Link to this heading")
An example showing how to move a camera to random location chosen from a list, using the choice distribution.

```
import omni.replicator.core as rep

# Pick a random camera location each frame, from a list

with rep.new_layer():

    # Create camera
    # https://docs.omniverse.nvidia.com/py/replicator/source/extensions/omni.replicator.core/docs/API.html#omni.replicator.core.create.camera
    camera_positions = [(-500, 200, -500), (500, 500, 500)]

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(focus_distance=200,f_stop=0.5)

    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(0, 0, 0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_output_camera_posfromlist", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    with rep.trigger.on_frame(num_frames=10):
        with camera:
            rep.modify.pose(position=rep.distribution.choice(camera_positions), look_at=(0,0,0))

```
Copy to clipboard
## Multiple Cameras with Basic Writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html#multiple-cameras-with-basic-writer "Link to this heading")
Multiple cameras are supported in Replicator. Below is a small example of the basic writer with two cameras in the scene, writing outputs for each per frame.

```
import omni.replicator.core as rep

camera1_pos = [(0, 100, 500),(500, 100, 500),(-500, 100, 500),]
camera2_pos = [(0, 500, 0),(500, 500, 0),(-500, 500, 0),]

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    cube = rep.create.cube(position=(200, 0, 0), semantics=[('class', 'cube')])
    sphere = rep.create.sphere(position=(0, 0, 0), semantics=[('class', 'sphere')])
    cone = rep.create.cone(position=(-200, 0, 0), semantics=[('class', 'cone')])

    camera = rep.create.camera(position=camera1_pos[0], look_at=(0,0,0))
    camera2 = rep.create.camera(position=camera2_pos[0], look_at=(0,0,0))

    with rep.trigger.on_frame(num_frames=3):
        with camera:
            rep.modify.pose(look_at=(0,0,0), position=rep.distribution.sequence(camera1_pos))
        with camera2:
            rep.modify.pose(look_at=(0,0,0), position=rep.distribution.sequence(camera2_pos))

# Will render 512x512 images and 320x240 images
render_product = rep.create.render_product(camera, (512, 512))
render_product2 = rep.create.render_product(camera2, (320, 240))

basic_writer = rep.WriterRegistry.get("BasicWriter")
basic_writer.initialize(
    output_dir=f"~/replicator_examples/multi_render_product/basic",
    rgb=True,
    bounding_box_2d_loose=True,
    bounding_box_2d_tight=True,
    bounding_box_3d=True,
    distance_to_camera=True,
    distance_to_image_plane=True,
    instance_segmentation=True,
    normals=True,
    semantic_segmentation=True,
)
# Attach render_product to the writer
basic_writer.attach([render_product, render_product2])
# Run the simulation graph
rep.orchestrator.run()

```
Copy to clipboard
