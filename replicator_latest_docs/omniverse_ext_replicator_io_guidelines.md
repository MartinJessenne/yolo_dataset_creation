---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html
---

# I/O Optimization Guide[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html#i-o-optimization-guide "Link to this heading")
This guide is intended to offer some insights and tips to optimize throughput when data generation is I/O bound.
## Threading[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html#threading "Link to this heading")
Replicator offers a built-in feature to asynchronously encode images and write data to disk using rep.BackendDispatch. This functionality is built-in all the default Replicator writers and can optionally be added to any custom writer. When tasks are sent to BackendDispatch, they are added to a queue to be processed by one of the available threads. If the rate at which data is added to the queue is greater than the rate at which the threads can process the data, a maximum queue size will be reached and the warning “Throttling generation due to I/O bottleneck.” will be displayed (note that this warning is only displayed once). There are two knobs that can be used to tune this function:
  1. Number of write threads (“/omni/replicator/backend/writeThreads”) - default: 4
  2. Queue Size (“/omni/replicator/backend/queueSize”) - default: 1000


**Write Threads**
This setting (“/omni/replicator/backend/writeThreads”) controls the number of threads to utilize for writing data. On high core count CPUs, this setting can be increased to take further advantage of the hardware’s capabilities.
**Queue Size**
This setting (“/omni/replicator/backend/queueSize”) controls the maximum number of tasks that are allowed to be queued. On systems with limited system memory, the queue size can be reduced to avoid running out of RAM, while on systems with lots of available memory, the queue size can be increased. Note that a higher queue size can help in cases where data size is variable, but otherwise will only move the throttling point further down the line.
**Tests**
We can do a few simple tests to see how this plays out. Below is the starting script from which tests will be derived.

```
import time
import asyncio

import omni.replicator.core as rep

NUM_RENDER_PRODUCTS = 1
NUM_FRAMES = 100
WRITE_THREADS = 1
QUEUE_SIZE = 5

rep.settings.carb_settings("/omni/replicator/backend/writeThreads", WRITE_THREADS)
rep.settings.carb_settings("/omni/replicator/backend/queueSize", QUEUE_SIZE)

# Add Default Light
distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

sphere = rep.create.sphere()
camera = rep.create.camera(position=(1000, 1000, 1000), look_at=sphere)
render_products = [rep.create.render_product(camera, (3840, 2160)) for _ in range(NUM_RENDER_PRODUCTS)]

writer = rep.writers.get("BasicWriter")
writer.initialize(output_dir="_out", rgb=True, distance_to_camera=True, distance_to_image_plane=True)
writer.attach(render_products)

with rep.trigger.on_frame(num_frames=NUM_FRAMES):
    with sphere:
        rep.modify.pose(position=rep.distribution.uniform((-100, -100, -100), (100, 100, 100)))

async def go():
    await rep.orchestrator.run_async()
    start = time.time()
    await rep.orchestrator.run_until_complete_async()
    print(f"FPS: {NUM_FRAMES / (time.time() - start)}")

asyncio.ensure_future(go())

```
Copy to clipboard
In our first experiment, we set WRITE_THREADS to 1, and set queue size to a constant 5 which will allow us to see the throttling very early. On a test system, this leads very rapidly to I/O throttling occurring, and an FPS of around 3.0.
Next, let’s change QUEUE_SIZE to 50. This should allow generation to proceed rapidly until just past halfway, at which point we’d expect throttling to occur again. The final FPS is unchanged at around 3.0, as replicator will wait for I/O to complete as part of the run_until_complete_async call.
For our final experiment, we set WRITE_THREADS to 16. On the same system, no throttling occurs and the FPS reported is around 6.5 (render bound), more than doubling the generation throughput.
Note: The numbers here are provided as references only and are system dependent. The test system used for these experiments has an 8-core CPU and a NVIDIA Titan RTX GPU.
## Data Encoding[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html#data-encoding "Link to this heading")
A big source of time spent during I/O is while encoding data for more efficient storage on disk. PNG offers lossless compression, but at the cost of nearly an order of magnitude more time encoding data than JPEG. PNG compression levels and JPEG quality offer further controls on the compromise of quality vs. throughput, and yet other image formats and libraries can provide improvements. When designing your own writer, it’s a good idea to experiment with different formats to understand these compromises and make decisions based on storage constraints, throughput targets and how the data will be read into a training dataloader.
BasicWriter was designed to offer a compromise between quality, performance and ease of data read-back. However, there are a few tips that can offer some solutions if using this writer and encountering I/O throttling. If the data saved is image heavy, changing the image_output_format to jpeg will offer higher performance at the expense of some quality loss. It’s also a good idea to reduce the amount of floating point data saved, as this data is comparatively large. The semantic_filter_predicate setting filters the semantics processed to only those that matter to you. This not only reduces the size of data saved for many annotators, but increases render performance by reducing the annotator workload.
