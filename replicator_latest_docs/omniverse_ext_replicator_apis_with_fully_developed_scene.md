---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html
---

# Using the Replicator with a fully developed scene[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html#using-the-replicator-with-a-fully-developed-scene "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html#learning-objectives "Link to this heading")
Through this tutorial you will learn how to use a previously developed scene with Replicator. Here, we will show you how you can randomize what is visible on the scene, but you should be able to use any of the randomizers following this structure.
## Open an existing scene[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html#open-an-existing-scene "Link to this heading")
In this tutorial you will use the warehouse from [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html). It has many assets for use with industrial use cases.
  1. Open the warehouse scene through the [content browser](https://docs.omniverse.nvidia.com/extensions/latest/ext_core/ext_content-browser.html) by navigating to:
**`Isaac Sim`** > **`Environments`** > **`Simple_Warehouse`** > **`warehouse_multiple_shelves.usd`**
Next, you will randomize the scene.
  2. To run the following script follow set up instructions in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up).
  3. Import replicator and create a render_product. Notice in this tutorial we use a camera that was already set up in the scene.

```
import omni.replicator.core as rep

with rep.new_layer():
   render_product = rep.create.render_product('/Root/Camera', (2048, 1024))

```
Copy to clipboard
  4. Get the prim you want to randomize and randomize in the way you want. In this case we are looking for the prim of the KLT boxes and for the randomization we are toggling visibility. Then you register your randomizer.

```
def hide_boxes():
      boxes = rep.get.prims(path_pattern='SmallKLT_Visual_\d\d\d', prim_types=['Xform'])
      with boxes:
         rep.modify.visibility(rep.distribution.choice([True, False]))
      return boxes.node
rep.randomizer.register(hide_boxes)

```
Copy to clipboard
  5. Lastly a randomization is triggered for 100 frames. To run it make sure to click on the top corner Replicator then run. Notice here we don’t have a writer, so it won’t be stored. In other tutorials we show you how to use `BasicWriter` or crate a custom writer.

```
with rep.trigger.on_frame(num_frames=100):
      rep.randomizer.hide_boxes()

```
Copy to clipboard


The full script can be found below:

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    render_product = rep.create.render_product('/Root/Camera', (2048, 1024))

    def hide_boxes():
        boxes = rep.get.prims(path_pattern='SmallKLT_Visual_\d\d\d$', prim_types=['Xform'])
        with boxes:
            rep.modify.visibility(rep.distribution.choice([True, False]))
        return boxes.node

    rep.randomizer.register(hide_boxes)

    # Setup randomization
    with rep.trigger.on_frame(num_frames=100):
        rep.randomizer.hide_boxes()

```
Copy to clipboard
