---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html
---

# Randomizer Examples[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizer-examples "Link to this heading")
Within replicator there are multiple off-the-shelf randomizers to bridge the domain gap between simulation and reality. Domain Randomization varies the parameters that define a scene in the simulation environment. Some of the parameters include the pose, scale of various objects in a scene, the lighting of the simulated environment, the appearance of simulated objects via their color and texture properties and so on. One of the main objectives of domain randomization is to enhance the training of deep learning applications by exposing the neural network to wide variety of domain parameters in simulation which will help to generalize well to real world applications. For example, in order to train a deep network to detect a cup, a huge data set is needed for training purpose with randomized color, texture, pose, size of the cup and different lighting conditions. This huge data set is made possible by generating synthetic data in Omniverse Isaac Sim instead of real images.
Below are a few examples of domain randomization applied on a scene using Replicator APIs.
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#learning-objectives "Link to this heading")
Through this page you will see some highlighted randomizers and how to use them. However, for all randomizers available and more information consult the [API documentation](https://docs.omniverse.nvidia.com/py/replicator) .
## Set up[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#set-up "Link to this heading")
Each of the randomizations shown below are standalone scripts that can be run following the set up described in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up) and [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running).
## Randomizing a light source[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-a-light-source "Link to this heading")
Replicator comes with multiple built-in light sources. Parameters such as position, temperature etc. can be randomized easily using Replicator APIs. In the following example shows a script that changes and intensity, temperature, scale and position of a sphere light. Plane, sphere and cube used in this example are used to show the changes. If another light source is desired, the workflow is similar. Explore the [API documentation](https://docs.omniverse.nvidia.com/py/replicator) for the full breadth of light sources.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(200, 200 , 100) )
    plane = rep.create.plane(scale=10, visible=True)

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

    with rep.trigger.on_frame(num_frames=10):
        rep.randomizer.sphere_lights(10)

```
Copy to clipboard
## Randomizing dome lights[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-dome-lights "Link to this heading")
Dome lights are used for image-based (background) lighting when supplied with a texture. Dome lights allow to easily illuminate the entire scene with a high or low dynamic image ranges. These can be very useful at providing realistic looking lighting in an environment and changing backgrounds.

```
import omni.replicator.core as rep

with rep.new_layer():
    def dome_lights():
        lights = rep.create.light(
            light_type="Dome",
            rotation= (270,0,0),
            texture=rep.distribution.choice([
                'omniverse://localhost/NVIDIA/Assets/Skies/Cloudy/champagne_castle_1_4k.hdr',
                'omniverse://localhost/NVIDIA/Assets/Skies/Clear/evening_road_01_4k.hdr',
                'omniverse://localhost/NVIDIA/Assets/Skies/Clear/mealie_road_4k.hdr',
                'omniverse://localhost/NVIDIA/Assets/Skies/Clear/qwantani_4k.hdr'
                ])
            )
        return lights.node

    rep.randomizer.register(dome_lights)

    with rep.trigger.on_frame(num_frames=10,interval=10):
        rep.randomizer.dome_lights()

```
Copy to clipboard
## Randomizing textures[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-textures "Link to this heading")
In the following script a scene is created with a cube and sphere. For the randomization in the function `get_shapes()`, the texture is randomized based on a list of textures. In this case we are using NVIDIA provided PNG images, however any PNG image can be used here.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(200, 200 , 100),count=10 )

    plane = rep.create.plane(scale=10, visible=True)

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.randomizer.texture(textures=[
                    'omniverse://localhost/NVIDIA/Materials/vMaterials_2/Ground/textures/aggregate_exposed_diff.jpg',
                    'omniverse://localhost/NVIDIA/Materials/vMaterials_2/Ground/textures/gravel_track_ballast_diff.jpg',
                    'omniverse://localhost/NVIDIA/Materials/vMaterials_2/Ground/textures/gravel_track_ballast_multi_R_rough_G_ao.jpg',
                    'omniverse://localhost/NVIDIA/Materials/vMaterials_2/Ground/textures/rough_gravel_rough.jpg'
                    ])
        return shapes.node

    rep.randomizer.register(get_shapes)

    # Setup randomization
    with rep.trigger.on_frame(num_frames=100):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Randomizing materials[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-materials "Link to this heading")
In this example we cover a process of creating custom materials and changing its material properties. For more information on the material properties and understanding on materials visit the [Omniverse materials](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html "\(in Omniverse Materials and Rendering\)") and the [API Documentation](https://docs.omniverse.nvidia.com/py/replicator). After making the material,s, the material randomizer is used to change materials per frame.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    mats = rep.create.material_omnipbr(diffuse=rep.distribution.uniform((0,0,0), (1,1,1)), count=100)
    spheres = rep.create.sphere(
        scale=0.2,
        position=rep.distribution.uniform((-100,-100,-100), (100,100,100)),
        count=100)


    def get_spheres():
        with spheres:
            rep.randomizer.materials(mats)
        return spheres.node

    rep.randomizer.register(get_spheres)

    # Setup randomization
    with rep.trigger.on_frame(num_frames=100):
        rep.randomizer.get_spheres()

```
Copy to clipboard
## Randomizing colors[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-colors "Link to this heading")
The function get shapes below, retrieves the prims created in the script and with `rep.randomizer.color` it changes the color with a uniform distribution.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(200, 200 , 100) )
    plane = rep.create.plane(scale=10, visible=True)

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.randomizer.color(colors=rep.distribution.uniform((0, 0, 0), (1, 1, 1)))
        return shapes.node

    rep.randomizer.register(get_shapes)

    # Setup randomization
    with rep.trigger.on_frame(num_frames=100):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Randomizing pose: position, rotation and scale[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#randomizing-pose-position-rotation-and-scale "Link to this heading")
In this example shows the process of using `modify.pose` to change rotation, position, and scale.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(200, 200 , 100) )
    plane = rep.create.plane(scale=10, visible=True)

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 50, -500), (500, 50, 500)),
                rotation=rep.distribution.uniform((0,-180, 0), (0, 180, 0)),
                scale=rep.distribution.normal(1, 0.5)
            )
        return shapes.node

    rep.randomizer.register(get_shapes)


    # Setup randomization
    with rep.trigger.on_frame(num_frames=30):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Scattering objects in a surface[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#scattering-objects-in-a-surface "Link to this heading")
In this example we show you how to scatter objects in a 2D surface using the function `scatter_2d`.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(100, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(200, 200 , 100) )
    plane = rep.create.plane(scale=10, visible=False)

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.randomizer.scatter_2d(plane)
        return shapes.node

    rep.randomizer.register(get_shapes)


    # Setup randomization
    with rep.trigger.on_frame(num_frames=30):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Instantiate multiple assets from a props folder[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html#instantiate-multiple-assets-from-a-props-folder "Link to this heading")
For domain randomization you may want to drop in assets as distractors into the scene. This is possible with Replicator using the function `rep.randomizer.instantiate`. Notice here we are using an NVIDIA asset. Make sure to have a nucleus server installed, if not follow [Nucleus](https://docs.omniverse.nvidia.com/nucleus/latest/index.html#nucleus "\(in Omniverse Nucleus\)").
`instanciate`.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    PROPS = 'omniverse://localhost/NVIDIA/Assets/Vegetation/Plant_Tropical/'
    plane = rep.create.plane(scale=10, visible=True)

    def get_props(size):
        instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS, recursive=True), size=size, mode='point_instance')
        with instances:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
                rotation=rep.distribution.uniform((-90, -180, 0), (-90, 180, 0)),
            )
        return instances.node

    rep.randomizer.register(get_props)

    # Setup randomization
    with rep.trigger.on_frame(num_frames=30):
        rep.randomizer.get_props(3)

```
Copy to clipboard
