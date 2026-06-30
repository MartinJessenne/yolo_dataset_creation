---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html
---

# Writer Examples[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html#writer-examples "Link to this heading")
Within replicator there are multiple off-the-shelf writers. Below are a few examples of the usage of included writers applied on a scene using Replicator APIs.
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html#learning-objectives "Link to this heading")
Through this page you will see some highlighted writers and how to use them. However, for all randomizers available and more information consult the [API documentation](https://docs.omniverse.nvidia.com/py/replicator) .
## Set up[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html#set-up "Link to this heading")
Each of the writers shown below are standalone scripts that can be run following the set up described in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up) and [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running).
## Basic Writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html#basic-writer "Link to this heading")
The basic writer is used in many examples, but for the sake of completeness, here is a simple example script showing its use. In the following code, the default Writer is initialized and is attached to the renderer to produce the output of the images and annotations with 2D bounding boxes. Note the user can specify a specific output directory for the writer to use.

```
writer = rep.WriterRegistry.get("OmniWriter")

writer.initialize(run_id=1, output_dir="_output", rgb=True,   bounding_box_2d_tight=True)

writer.attach([render_product])

```
Copy to clipboard
Below is the entire script which can be copied directly to the script editor.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(0, 0, 1000))

    render_product = rep.create.render_product(camera, (1024, 1024))

    torus = rep.create.torus(semantics=[('class', 'torus')] , position=(0, -200 , 100))

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))

    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(100, -200 , 100) )

    with rep.trigger.on_frame(num_frames=10):
        with rep.create.group([torus, sphere, cube]):
            rep.modify.pose(
                position=rep.distribution.uniform((-100, -100, -100), (200, 200, 200)),
                scale=rep.distribution.uniform(0.1, 2))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")

    writer.initialize( output_dir="_output", rgb=True,   bounding_box_2d_tight=True)

    writer.attach([render_product])

    rep.orchestrator.preview()

```
Copy to clipboard
## KITTI Writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html#kitti-writer "Link to this heading")
Example of usage of the Kitti writer, that writes Kitti format data. Below is the entire script which can be copied directly to the script editor.

```
import omni.replicator.core as rep

sequential_pos = [(0, 100, 500),(500, 100, 500),(-500, 100, 500),]

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    cube = rep.create.cube(position=(200, 0, 0), semantics=[('class', 'cube')])
    sphere = rep.create.sphere(position=(0, 0, 0), semantics=[('class', 'sphere')])
    cone = rep.create.cone(position=(-200, 0, 0), semantics=[('class', 'cone')])

    camera = rep.create.camera(position=sequential_pos[0], look_at=(0,0,0))

    with rep.trigger.on_frame(num_frames=3):
        with camera:
            rep.modify.pose(look_at=(0,0,0), position=rep.distribution.sequence(sequential_pos))

# Will render 512x512 images
render_product = rep.create.render_product(camera, (512, 512))

# Get a Kitti Writer and initialize its defaults
writer = rep.WriterRegistry.get("KittiWriter")
writer.initialize(
    output_dir=f"~/replicator_examples/kitti_writer/",
    bbox_height_threshold=5,
    fully_visible_threshold=0.75,
    omit_semantic_type=True
)
# Attach render_product to the writer
writer.attach([render_product])

# Run the simulation graph
rep.orchestrator.run()

```
Copy to clipboard
