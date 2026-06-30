---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html
---

# Replicator - Annotating with Transparent Materials[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html#replicator-annotating-with-transparent-materials "Link to this heading")
There are several situations where different annotation behaviors are required when handling transparent materials.
Controlling whether a mesh with a transparent material appears in segmentation, is done through the mesh `Cast Shadows` flag, attribute name of `primvars:doNotCastShadows`. Consider using the `RTX Interactive (Path Tracing)` rendering mode with glass effects if you need higher quality.
## Use with OmniGlass[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html#use-with-omniglass "Link to this heading")
Using `OmniGlass` you can see the effect of changing this flag on segmentation.
![Comparison of using "Cast Shadows" flag](https://docs.omniverse.nvidia.com/extensions/latest/_images/rep_transparency_cast_shadows_comparison.png)
`Cast Shadows` can be found in the properties panel of the mesh object with transparency.
![Enabling the "Cast Shadows" flag](https://docs.omniverse.nvidia.com/extensions/latest/_images/rep_transparency_cast_shadows_flag.png)
## Use with OmniPBR[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html#use-with-omnipbr "Link to this heading")
Masked transparency is available using `Enable Opacity` on the `OmniPBR` material and others. This can be used for objects such as chain link fences.
![Using opacity masking with materials](https://docs.omniverse.nvidia.com/extensions/latest/_images/rep_transparency_pbr_masked.png)
`Enable Opacity` must be true, and the opacity map is what controls the opacity. Segmentation is true for values of 1.0. Values below do not show segmentation.
![Enabling the "Enable Opacity" flag](https://docs.omniverse.nvidia.com/extensions/latest/_images/rep_transparency_pbr_opacity_flag.png)
