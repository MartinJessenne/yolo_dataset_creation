---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html
---

# Using physics with Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html#using-physics-with-replicator "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html#learning-objectives "Link to this heading")
Through this tutorial you will learn how to use the physics Randomizer with [YCB](https://www.ycbbenchmarks.com/object-models/) assets. In this case we will create a scene with assets falling down onto a plane and save the frames.
## Using the Replicator APIs[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html#using-the-replicator-apis "Link to this heading")
First we define the assets needed from the nucleus server ([Nucleus](https://docs.omniverse.nvidia.com/nucleus/latest/index.html#nucleus "\(in Omniverse Nucleus\)")).

```
with rep.new_layer():
    # Define paths for the character, the props, the environment and the surface where the assets will be scattered in.
    PROPS = 'omniverse://localhost/NVIDIA/Assets/Isaac/2022.1/Isaac/Props/YCB/Axis_Aligned_Physics'
    SURFACE = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Basic/display_riser.usd'
    ENVS = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Interior/ZetCG_ExhibitionHall.usd'

```
Copy to clipboard
Then we make a randomizer that takes in the YCB assets modifies their position and then makes them into a rigid body. Notice we are using scene_instance with the instantiate function. This is needed in order to use physics. For the physics functionality we use rep.physics.rigid_body. Feel free to modify the velocity or angular_velocity. After, we register the randomizer.

```
def env_props(size=50):
        instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS, recursive=True), size=size, mode='scene_instance')
        with instances:
            rep.modify.pose(
                position=rep.distribution.uniform((-50, 5, -50), (50, 20, 50)),
                rotation=rep.distribution.uniform((0,-180, 0), (0, 180, 0)),
                scale = 100
            )

            rep.physics.rigid_body(
                velocity=rep.distribution.uniform((-0,0,-0),(0,0,0)),
                angular_velocity=rep.distribution.uniform((-0,0,-100),(0,0,0)))
        return instances.node
    # Register randomization
    rep.randomizer.register(env_props)

```
Copy to clipboard
We must then define the environment and add a ground. For that we use the surface described above. Notice that we must make this surface a physics collider so that items fall onto it and stop, in replicator you do this with rep.physics.collider.

```
env = rep.create.from_usd(ENVS)
surface = rep.create.from_usd(SURFACE)
with surface:
    rep.physics.collider()

```
Copy to clipboard
The rest of the script is similar to other tutorials. Another light randomizer is added to move around lights, but other than that it is similar to the [Randomizing appearance, placement and orientation of an existing 3D assets with a built-in writer](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html#shrub) example. The biggest difference is the type of trigger used by this example. In this case we use trigger on time. Here we tell it to run an interval of 2 seconds and record 10 frames per interval.

```
with rep.trigger.on_time(interval=2,num=10):
    rep.randomizer.env_props(10)
    rep.randomizer.sphere_lights(10)
    with camera:
        rep.modify.pose(position=rep.distribution.uniform((-50, 20, 100), (50, 50, 150)), look_at=surface)

```
Copy to clipboard
Below is the full script of this example. This can be directly copied into the script editor.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    # Define paths for the character, the props, the environment and the surface where the assets will be scattered in.
    PROPS = 'omniverse://localhost/NVIDIA/Assets/Isaac/2022.1/Isaac/Props/YCB/Axis_Aligned_Physics'
    SURFACE = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Basic/display_riser.usd'
    ENVS = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Interior/ZetCG_ExhibitionHall.usd'

    # Define randomizer function for Base assets. This randomization includes placement and rotation of the assets on the surface.
    def env_props(size=50):
        instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS, recursive=True), size=size, mode='scene_instance')
        with instances:
            rep.modify.pose(
                position=rep.distribution.uniform((-50, 5, -50), (50, 20, 50)),
                rotation=rep.distribution.uniform((0,-180, 0), (0, 180, 0)),
                scale = 100
            )
        return instances.node

    # Register randomization
    rep.randomizer.register(env_props)
    # Setup the static elements
    env = rep.create.from_usd(ENVS)
    surface = rep.create.from_usd(SURFACE)
    with surface:
        # Add physics to the collision floor, the props already have rigid-body physics applied
        rep.physics.collider()

    # Setup camera and attach it to render product
    camera = rep.create.camera()
    render_product = rep.create.render_product(camera, resolution=(1024, 1024))

    # sphere lights for extra randomization
    def sphere_lights(num):
        lights = rep.create.light(
            light_type="Sphere",
            temperature=rep.distribution.normal(6500, 500),
            intensity=rep.distribution.normal(35000, 5000),
            position=rep.distribution.uniform((-300, -300, -300), (300, 300, 300)),
            scale=rep.distribution.uniform(50, 100),
            count=num
        )
        return lights.node
    rep.randomizer.register(sphere_lights)
    # trigger on frame for an interval

    with rep.trigger.on_time(interval=2,num=10):
        rep.randomizer.env_props(10)
        rep.randomizer.sphere_lights(10)
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-50, 20, 100), (50, 50, 150)), look_at=surface)
    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize( output_dir="_output_physics10", rgb=True,   bounding_box_2d_tight=True)
    writer.attach([render_product])

```
Copy to clipboard
Click on the Run (Ctrl + Enter) button at the bottom of the Script Editor Window. This creates all the necessary nodes needed to run the workload.
To run the complete generation or another preview, click on the top left corner on Replicator → Run to start the data generation process as shown in [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running). Generated data is stored in the specified output directory.
