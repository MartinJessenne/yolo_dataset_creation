---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html
---

# Randomizing appearance, placement and orientation of an existing 3D assets with a built-in writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html#randomizing-appearance-placement-and-orientation-of-an-existing-3d-assets-with-a-built-in-writer "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html#learning-objectives "Link to this heading")
Let’s say we want to create a DNN model that is able to identify an object within a large set of environments. In order to create such a model a training dataset would be needed where the target object is placed in a variety of different ways in a variety of different environments. In some cases this target object may not be completely visible and could be occluded by other assets in the scene. In this example, we would walk through the process of synthetically creating this dataset. The intent of this tutorial is to show an end-to-end example of a synthetic data generation process where a target object is placed in randomized environments. We end this tutorial with a writer that outputs annotated data in a form that can be used to train a machine learning model.
For this example we use a built in asset (a worker in blue dress) as our target object that we place in randomized environments along with other assets. Assets placements on the scene and rotations are selected from uniform random distributions. In addition to randomizing assets in this example we also demonstrate camera placement randomization to generate images from different angles to capture different backgrounds. Finally, images and annotations are written to the disk using a predefined writer.
For this tutorial there is a [Video Tutorial](https://www.youtube.com/watch?v=5gBRbFqmZSE) available.
## Using the Replicator APIs[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html#using-the-replicator-apis "Link to this heading")
To run the following tutorial first make sure to follow script follow [Nucleus](https://docs.omniverse.nvidia.com/nucleus/latest/index.html#nucleus "\(in Omniverse Nucleus\)") to get the assets for this randomization. Tor run the spript use the script editor as shown in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up).
Let’s `import omni.replicator` first. As we have done in the other examples, let’s create a new layer in the USD file which will be used to place and randomize the assets. We also define paths for 3D assets used in this example.

```
import omni.replicator.core as rep

with rep.new_layer():
    # Define paths for the character, the props, the environment and the surface where the assets will be scattered in.

    WORKER = 'omniverse://localhost/NVIDIA/Assets/Characters/Reallusion/Worker/Worker.usd'
    PROPS = 'omniverse://localhost/NVIDIA/Assets/Vegetation/Shrub'
    ENVS = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Outdoor/Puddles.usd'
    SURFACE = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Basic/display_riser.usd'

```
Copy to clipboard
In the following function we define a randomizer for shrubs assets. These are referred to as PROPS assets in this example. As a first step, we create a subset (size = 50) of these PROPS assets. We want to use different shrubs in different frames to ensure that we have enough variety of background generated for this dataset. Once this subset is selected the next step is to place these shrubs in random positions with random rotations.

```
# Define randomizer function for PROPS assets. This randomization includes placement and rotation of the assets on the surface.
def env_props(size=50):
    instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS), size=size, mode='point_instance')
    with instances:
        rep.modify.pose(
            position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
            rotation=rep.distribution.uniform((-90,-180, 0), (-90, 180, 0)),
        )
    return instances.node

```
Copy to clipboard
Note
If you are using your own PROPS folder and it is full of subfolders with USDs, you will need to use the flag `recursive=True` as shown here `rep.utils.get_usd_files(PROPS, recursive=True)`. This will take a long time if the assets are in a remote nucleus server.
Next we define a randomizer for our target object - a worker in blue dress. As with the other assets (shrubs) in the scene we also randomize the position and rotation of the target object.

```
def worker():
    worker = rep.create.from_usd(WORKER, semantics=[('class', 'worker')])

    with worker:
        rep.modify.pose(
            position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
            rotation=rep.distribution.uniform((-90,-45, 0), (-90, 45, 0)),
        )
    return worker

```
Copy to clipboard
In the following lines, we register the two randomizers we defined above.

```
rep.randomizer.register(env_props)

rep.randomizer.register(worker)

```
Copy to clipboard
Next we set up our static elements of the scene, room and the table on which the assets are going to be placed. We also setup camera and attach to a render product.

```
# Setup the static elements
env = rep.create.from_usd(ENVS)

surface = rep.create.from_usd(SURFACE)

# Setup camera and attach it to render product
camera = rep.create.camera(
    focus_distance=800,
    f_stop=0.5
)
render_product = rep.create.render_product(camera, resolution=(1024, 1024))

```
Copy to clipboard
As a last step we initialize our default writer and define an output directory where we want to store our images. This writer is then attached to the render product we defined in the previous step.

```
# Initialize and attach writer
writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir="_output", rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

```
Copy to clipboard
Now we have defined our target and base assets, have defined randomizers, have defined our environment, have set up camera, render product and a default writer. After all the setup is complete, we are not ready to generate data. In the following lines, we trigger our registered randomizers every frame. For every frame Base and target assets are randomized along with the camera position to ensure we have images captured from different angles for our dataset.

```
with rep.trigger.on_frame(num_frames=10000):
    rep.randomizer.env_props(75)

    rep.randomizer.worker()

    with camera:
        rep.modify.pose(position=rep.distribution.uniform((-500, 200, 1000), (500, 500, 1500)), look_at=surface)

```
Copy to clipboard
Below is the complete code that can be copied over and tested for convenience.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    # Define paths for the character, the props, the environment and the surface where the assets will be scattered in.

    WORKER = 'omniverse://localhost/NVIDIA/Assets/Characters/Reallusion/Worker/Worker.usd'
    PROPS = 'omniverse://localhost/NVIDIA/Assets/Vegetation/Shrub'
    ENVS = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Outdoor/Puddles.usd'
    SURFACE = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Basic/display_riser.usd'

    # Define randomizer function for Base assets. This randomization includes placement and rotation of the assets on the surface.
    def env_props(size=50):
        instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS), size=size, mode='point_instance')
        with instances:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
                rotation=rep.distribution.uniform((-90,-180, 0), (-90, 180, 0)),
            )
        return instances.node

    def worker():
        worker = rep.create.from_usd(WORKER, semantics=[('class', 'worker')])

        with worker:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
                rotation=rep.distribution.uniform((-90,-45, 0), (-90, 45, 0)),
            )
        return worker

    # Register randomization
    rep.randomizer.register(env_props)
    rep.randomizer.register(worker)

    # Setup the static elements
    env = rep.create.from_usd(ENVS)
    surface = rep.create.from_usd(SURFACE)

    # Setup camera and attach it to render product
    camera = rep.create.camera(
        focus_distance=800,
        f_stop=0.5
    )
    render_product = rep.create.render_product(camera, resolution=(1024, 1024))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_output", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    with rep.trigger.on_frame(num_frames=10000):
        rep.randomizer.env_props(75)
        rep.randomizer.worker()
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-500, 200, 1000), (500, 500, 1500)), look_at=surface)

```
Copy to clipboard
Click on the Run (Ctrl + Enter) button at the bottom of the Script Editor Window. This creates all the necessary nodes needed to run the workload.
Now click on Replicator → Run to start the data generation process as shown in [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running). Generated data is stored in the specified output directory.
![../_images/replicatorRun.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicatorRun.png)
Note
If you did not modify output_dir, in linux, the data will be in HOME/omni.replicator_out/_output. In Windows due to permissions it might have failed. Make sure to modify _output folder to something valid.
