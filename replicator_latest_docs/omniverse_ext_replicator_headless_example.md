---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html
---

# Running Replicator Headlessly[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#running-replicator-headlessly "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#learning-objectives "Link to this heading")
The goal of this tutorial is to show you how to use Replicator headlessly. Headless in this context means the computing device has no monitor or peripherals, such as a keyboard and mouse. In order to do this, we will make mild modifications to the script explained in [Core Functions - “Hello World” of Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#hello-world) to make it work. It is encouraged to first go through that tutorial to understand the basics of Replicator.
## Modifying Hello World Script for running headlessly[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#modifying-hello-world-script-for-running-headlessly "Link to this heading")
  1. Add a light
There are two main modifications required to run headlessly. The first one is to add an extra light. When running with a head, by default, the Omniverse Application starts a dome light. When running headlessly, a light needs to be added. For this example, a sphere light is chosen. However, you could choose a different type of light.

```
sphere_light = rep.create.light(
   light_type="Sphere",
   temperature=rep.distribution.normal(6500, 500),
   intensity=rep.distribution.normal(35000, 5000),
   position=rep.distribution.uniform((-300, -300, -300), (300, 300, 300)),
   scale=rep.distribution.uniform(50, 100),
   count=2
)

```
Copy to clipboard
  2. Set `orchestator` to run
The second and most important change is to add `rep.orchestrator.run()` at the end of the script. As mentioned in the introduction, in the background replicator makes an omnigraph and then you need to tell Omniverse to execute the graph. This will be done by `rep.orchestrator.run`. Without it, the script will not run the omnigraph and won’t produce an output. The full script below may be copied and pasted. You can store this as a python file anywhere in your computer. For the sake of this example call it test.py .

```
import omni.replicator.core as rep

# Use these settings when in Isaac Sim
rep.settings.set_stage_up_axis("Y")
rep.settings.set_stage_meters_per_unit(0.01)

with rep.new_layer():

   camera = rep.create.camera(position=(0, 0, 1000))

   sphere_light = rep.create.light(
         light_type="Sphere",
         temperature=rep.distribution.normal(6500, 500),
         intensity=rep.distribution.normal(35000, 5000),
         position=rep.distribution.uniform((-300, -300, -300), (300, 300, 300)),
         scale=rep.distribution.uniform(50, 100),
         count=2
   )

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

   rep.orchestrator.run()

```
Copy to clipboard


## Running Replicator script headlessly[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#running-replicator-script-headlessly "Link to this heading")
  1. Run script
Now you are ready to run the test.py script above. In your [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html) installation, locate the directory containing isaac-sim.bat for Windows or ./isaac-sim.sh for Linux. From a terminal run the command:

```
isaac-sim.bat --no-window --/omni/replicator/script=C:\PATH\TO\test.py

```
Copy to clipboard
Note
If you did not modify output_dir, in linux, the data will be in HOME/omni.replicator_out/_output or in the folder your python script is in. If you have any errors due to permissions modify the output folder in the script.
  2. Wait for the script to run
A minute or so after running the script, you will have the images with annotations. Any example run headlessly may have a long initial start up time as it is launching the application in the background. The generation of samples itself should be quick.


