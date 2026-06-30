---
source: https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html
---

# Replicator Troubleshooting[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-troubleshooting "Link to this heading")
This page consolidates troubleshooting information for Replicator components in Isaac Sim.
## Replicator Rendering Issues[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-rendering-issues "Link to this heading")
If there is unwanted noise in simulated depth images, disable anti-aliasing under the **Render Settings > Ray Tracing > Anti-Aliasing** tab by setting the `Algorithm` to `None`.
If randomized materials are not loaded on time for synthetic data generation, the [rt_subframes](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html#subframes-examples "\(in Omniverse Extensions\)") must be set to be at least `2`.
The replicator Scatter3D OmniGraph node breaks physics when called on a stage using world. Avoid using these together or use alternative methods for object placement.
If ghosting artifacts are observed in the captured data, especially for scenes with moving objects or significant changes in lighting conditions, increase the `rt_subframes` value when capturing the data to a value until the renderer is able to remove the artifacts. For more information see [RT Subframes Parameter](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_getting_started.html#isaac-sim-replicator-getting-started-subframes) and [subframes examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html#subframes-examples "\(in Omniverse Extensions\)").
If the captured images are written as black, try starting Isaac Sim once with the `--reset-user` to clear any previous user settings.
## Async Rendering and Frame Skipping[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#async-rendering-and-frame-skipping "Link to this heading")
When using Replicator, frames may be skipped due to the `isaacsim.core.throttling` extension toggling `/app/asyncRendering=True` by default when the timeline is stopped. Since Replicator remains in STARTED mode, it does not re-initialize and toggle the setting back to False, leading to frames being skipped during capture.
**Solution:** Launch Isaac Sim with the following flag to disable async rendering toggling from the throttling extension:

```
--/exts/isaacsim.core.throttling/enable_async=false

```
Copy to clipboard
This occurs because when the timeline is stopped, the throttling extension enables async rendering for performance. However, when Replicator schedules frames for capture before the timeline starts playing again, those frames may be skipped due to async rendering being enabled. The flag above prevents the throttling extension from toggling async rendering, ensuring all scheduled frames are captured properly.
## Replicator Data Storage Issues[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-data-storage-issues "Link to this heading")
Using Replicator to write to S3 buckets with the built-in backend in Windows may require setting the credentials in the environment variables instead of the AWS config files. This is because of a possible path parsing error in Boto3 on Windows.
When working with large datasets or high-resolution images, you may experience storage bottlenecks. Consider: 1. Using a faster storage device 2. Reducing the image resolution or compression level 3. Using batch processing with smaller batches
## Replicator Layers and Randomization[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-layers-and-randomization "Link to this heading")
Using [replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html "\(in Omniverse Extensions\)")’s `rep.new_layer()` functionality, which creates a new layer in which to place and randomize assets, may lead to issues in simulation scenarios where these assets are used. In such cases the use of `rep.new_layer()` can be omitted.
When using multiple randomizers, be aware that they may conflict with each other. Test your randomization settings carefully to ensure they produce the expected results.
## Replicator Performance Issues[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-performance-issues "Link to this heading")
For complex scenes with many objects and randomizers, you may experience performance issues. Consider: 1. Reducing the number of objects in the scene 2. Simplifying the randomization parameters 3. Using fewer sensors or lower resolution sensors 4. Running with headless mode for improved performance during data generation
## Replicator API Changes[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#replicator-api-changes "Link to this heading")
If you are encountering any issues regarding the dependencies on `omni.replicator.character` or `omni.replicator.agent`, the extension is now renamed to `isaacsim.replicator.agent`. Revise your code accordingly.
## Getting Started Scripts Issues[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#getting-started-scripts-issues "Link to this heading")
Common issues and solutions for the Getting Started Scripts:
  1. **Data not being captured** - Ensure the capture-on-play flag is properly set - Check if the render products are correctly attached to writers - Verify the output directory has write permissions
  2. **Rendering artifacts** - Try increasing RTSubframes value - Check if materials are fully loaded before capture - Ensure proper lighting setup
  3. **Performance issues** - Reduce resolution or number of cameras - Use headless mode for faster processing - Optimize scene complexity
  4. **Memory issues** - Reduce batch size - Clear unused resources with `destroy()` - Monitor GPU memory usage


## First Frame Missing in Windows Standalone Mode[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#first-frame-missing-in-windows-standalone-mode "Link to this heading")
On Windows, when running SDG pipelines with Replicator in standalone mode, the first frame may be skipped by writers or data may be missing from annotators.
### Workaround[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#workaround "Link to this heading")
Call a few “warmup” steps to advance the simulation before the first capture to avoid missing the initial frame. For example:

```
# Warmup the simulation
timeline = omni.timeline.get_timeline_interface()
timeline.play()
for _ in range(2):
    standalone_app.update()

```
Copy to clipboard
Alternative (depending on your Replicator control flow):

```
import omni.replicator.core as rep
# [..] initialize writer [..]
rep.orchestrator.step()
# [..] start SDG pipeline [..]

```
Copy to clipboard
