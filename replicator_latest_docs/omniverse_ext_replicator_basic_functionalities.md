---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html
---

# Core Functions - “Hello World” of Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#core-functions-hello-world-of-replicator "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#learning-objectives "Link to this heading")
The goal of this tutorial is to provide an introduction to the basic Omniverse Replicator functionalities such as creating a simple scene with a few predefined 3D assets, applying randomizations and then writing the generated images to the disk for further processing.
## Using the Replicator APIs[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#using-the-replicator-apis "Link to this heading")
To run the script follow set up instructions in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up).
First, let’s create a new [USD layer](https://docs.omniverse.nvidia.com/extensions/latest/ext_core/ext_layers.html) using `rep.new_layer()` in the USD file which will be used to place and randomize the assets. Now let’s create a camera in the scene at the desired position. This enables a viewport for which the frames are generated. In order to do this, the camera is attached to a renderer at a preferred resolution. In this case we are using a default renderer with 1024x1024 resolution.

```
import omni.replicator.core as rep

with rep.new_layer():

    camera = rep.create.camera(position=(0, 0, 1000))

    render_product = rep.create.render_product(camera, (1024, 1024))

```
Copy to clipboard
Now, let’s create basic 3D shapes for our simple scene. Users can also bring any custom 3D objects they may have already created. The tutorial [Using the Replicator with a fully developed scene](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html#existing-assets) demonstrates the process to bring user generated assets within the scene. Notice when creating the assets, we add semantics, using the flag `semantics`. These semantics labels are added to the 3D shapes and used while generating annotations for the data.

```
torus = rep.create.torus(semantics=[('class', 'torus')] , position=(0, -200 , 100))

sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))

cube = rep.create.cube(semantics=[('class', 'cube')],  position=(100, -200 , 100))

```
Copy to clipboard
We have created a camera, attached it to a renderer, brought in 3D assets. At this point, we are ready to define randomizers with specified distributions (uniform random in this case). In this tutorial, we randomize the position and scale of these assets within the scene.
Notice that these randomizations are triggered at every frame event. We generate 10 frames with randomizations in this example.

```
with rep.trigger.on_frame(num_frames=10):
    with rep.create.group([torus, sphere, cube]):
        rep.modify.pose(
            position=rep.distribution.uniform((-100, -100, -100), (200, 200, 200)),
            scale=rep.distribution.uniform(0.1, 2))

```
Copy to clipboard
Lastly, data generated for each frame is then written to the disk. For this purpose, Replicator provides a default Writer that can be used as demonstrated in this example. In addition to the default writer, users can also create their own custom writer. This is demonstrated in one of the subsequent tutorials.
In the following code, the default Writer is initialized and is attached to the renderer to produce the output of the images and annotations with 2D bounding boxes. Note the user can specify a specific output directory for the writer to use.

```
writer = rep.WriterRegistry.get("OmniWriter")

writer.initialize(run_id=1, output_dir="_output", rgb=True,   bounding_box_2d_tight=True)

writer.attach([render_product])

```
Copy to clipboard
Note
If you did not modify output_dir, in linux, the data will be in HOME/omni.replicator_out/_output or in the folder where code was installed. In Windows due to permissions it might have failed. Make sure to modify _output folder to something valid.
Below is the entire script which can be copied directly to the script editor.

```
import omni.replicator.core as rep

with rep.new_layer():

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
Click on the Run (Ctrl + Enter) button at the bottom of the Script Editor Window. This creates all the necessary nodes needed to run the workload. The last line rep.orchestrator.preview() runs the graph once, for you tor preview the output.
To run the complete generation or another preview, click on the top left corner on Replicator → Run to start the data generation process as shown in [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running). Generated data is stored in the specified output directory.
Note
If you did not modify output_dir, in linux, the data will be in HOME/omni.replicator_out/_output. In Windows due to permissions it might have failed. Make sure to modify _output folder to something valid.
