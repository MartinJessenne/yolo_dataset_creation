---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html
---

# Replicator - Working with Layers[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html#replicator-working-with-layers "Link to this heading")
[Layers In USD](https://docs.omniverse.nvidia.com/extensions/latest/ext_core/ext_layers.html) are a convenient way to organize and manage scenes. Replicator makes use of them in a few key ways.
  * Layers provide a clean way to prototype and manage scenes during authoring.
  * Layers allow a non destructive workflow in synthetic data generation, where there is no risk to permanently altering your root scene layer.
  * Used by Replicator to hold all replicator randomizations and graphs when `rep.new_layer()` is used.


## Layer Organization with Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html#layer-organization-with-replicator "Link to this heading")
The base scene has a `root` Authoring Layer. This is for:
  * User-specified changes
  * Optionally includes Replicator Randomizations (for creation of smart scenes and smart assets)


When we put `with rep.new_layer()` in a script, this creates a _Replicator Randomization Layer_ that:
  * Holds replicator randomizations. `rep.new_layer()` will remove an existing Replicator Randomization Layer if it exists. When iterating, this makes it convenient to avoid accumulating multiple graphs.
  * Can be saved and layered on top of scenarios to provide preset randomization options.


## Example[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html#example "Link to this heading")
When `with rep.new_layer()` is used, a new layer is created

```
import omni.replicator.core as rep

camera = rep.create.camera()
render_product = rep.create.render_product(camera, (1920, 1080))

with rep.new_layer():
    rep.create.cube()

```
Copy to clipboard
With this corresponding to the layer newly created and shown in the Layers tab:
![Replicator Use of Layers](https://docs.omniverse.nvidia.com/extensions/latest/_images/rep_use_of_layers.png)
