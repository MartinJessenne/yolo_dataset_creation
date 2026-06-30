---
source: https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html
---

# Data Augmentation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#data-augmentation "Link to this heading")
Example of using Isaac Sim and Replicator to capture augmented synthetic data.
## Learning Objectives[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#learning-objectives "Link to this heading")
This tutorial provides examples on how to use omni.replicator [augmentations](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html "\(in Omniverse Extensions\)") on annotators or writers. The provided examples will showcase how to augment **rgb** and **depth** annotator data using warp (GPU) or NumPy (CPU) kernel/filters. The use of warp is particularly advantageous for executing parallelizable tasks, especially if the data already resides in the GPUs memory, thus avoiding memory copies from GPU to CPU.
  * For a better understanding of the tutorial, familiarity with [omni.replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html "\(in Omniverse Extensions\)"), [annotators](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html "\(in Omniverse Extensions\)"), [writers](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html "\(in Omniverse Extensions\)") and [warp](https://docs.omniverse.nvidia.com/extensions/latest/ext_warp.html "\(in Omniverse Extensions\)") is recommended.


## Scenario[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#scenario "Link to this heading")
![../_images/isaac_tutorial_replicator_augmentation.png](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_augmentation.png)
The depicted figure showcases the example augmentations used throughout the examples. The first image is an illustrative example switching the red and blue channels of the image. The second image is a composed augmentation of converting the rgb data to hsv, adding gaussian noise, and converting back to rgb. The third and forth image are results of applying gaussian noise filters with various sigma values to the depth data.
For the example scenario a red cube is spawned with a camera looking at it from a top view. For the cube a replicator randomization graph is created which is triggered by a custom event sent before each capture step, producing a random rotation for every frame capture.
## Implementation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#implementation "Link to this heading")
The tutorial is split into two parts, the first example will showcase how to augment annotators directly, and secondly how to augment writers. Both examples can be run as [Standalone Applications](https://docs.isaacsim.omniverse.nvidia.com/latest/introduction/workflows.html#standalone-application) or from the UI using the [Script Editor](https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/omniverse_script_editor.html#script-editor).
### Annotator Augmentation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#annotator-augmentation "Link to this heading")
The annotator example will output rgb images with the red and blue channels switched, and two depth images with different gaussian noise levels (saved as grayscale PNGs). The example can switch between using warp or NumPy augmentations.
Standalone Application
The example can be run as a standalone application using the following commands in the terminal (on Windows use `python.bat` instead of `python.sh`):

```
./python.sh standalone_examples/replicator/augmentation/annotator_augmentation.py --env_url /Isaac/Environments/Grid/default_environment.usd

```
Copy to clipboard
Optionally the following arguments can be used to change the default behavior:
  * `--env_url` – USD environment path relative to the assets root (default: empty scene with dome light and ground plane)
  * `--use_warp` – flag to use warp (GPU) instead of numpy (CPU) for the augmentation functions (default: False)
  * `--num_frames` – the number of frames to be captured (default: 25)



```
./python.sh standalone_examples/replicator/augmentation/annotator_augmentation.py --use_warp --num_frames 25 --env_url /Isaac/Environments/Grid/default_environment.usd

```
Copy to clipboard
Full Standalone Script

```
"""Generate augmented synthetic data from annotators."""

from isaacsim import SimulationApp

simulation_app = SimulationApp(launch_config={"headless": False})

import argparse
import os
import time

import carb.settings
import numpy as np
import omni.replicator.core as rep
import omni.usd
import warp as wp
from isaacsim.core.utils.stage import open_stage
from isaacsim.storage.native import get_assets_root_path
from omni.replicator.core.functional import write_image

parser = argparse.ArgumentParser()
parser.add_argument("--num_frames", type=int, default=5, help="The number of frames to capture")
parser.add_argument(
    "--use_warp",
    action="store_true",
    help="Use warp augmentations instead of numpy",
)
parser.add_argument("--resolution", nargs=2, type=int, default=[512, 512], help="Camera resolution")
parser.add_argument("--env_url", type=str, default="", help="USD environment URL (empty for basic scene)")
args, unknown = parser.parse_known_args()

num_frames = args.num_frames
use_warp = args.use_warp
resolution = args.resolution
env_url = args.env_url or None
SEED = 42

# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)


def rgb_to_bgr_np(data_in):
    """Swap RGBA red and blue channels using NumPy (CPU)."""
    data_in[:, :, [0, 2]] = data_in[:, :, [2, 0]]
    return data_in


@wp.kernel
def rgb_to_bgr_wp(data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8)):
    """Swap RGBA red and blue channels using Warp (GPU)."""
    i, j = wp.tid()
    data_out[i, j, 0] = data_in[i, j, 2]
    data_out[i, j, 1] = data_in[i, j, 1]
    data_out[i, j, 2] = data_in[i, j, 0]
    data_out[i, j, 3] = data_in[i, j, 3]


def gaussian_noise_depth_np(data_in, sigma, seed):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.annotators.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=SEED)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.annotators.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=SEED)
)


def convert_depth_to_uint8(data: np.ndarray | wp.array) -> np.ndarray:
    """Normalize depth data and convert it to uint8 grayscale."""
    if isinstance(data, wp.array):
        data = data.numpy()
    depth = data.astype(np.float32, copy=False)
    depth[np.isinf(depth)] = np.nan
    mean_val = np.nanmean(depth)
    if np.isnan(mean_val):
        mean_val = 0.0
    depth = np.nan_to_num(depth, nan=mean_val, copy=False)
    min_val = depth.min()
    max_val = depth.max()
    if max_val <= min_val:
        return np.zeros(depth.shape, dtype=np.uint8)
    normalized = (depth - min_val) / (max_val - min_val)
    return (normalized * 255.0).astype(np.uint8)


def run_example(num_frames: int, resolution: tuple[int, int], use_warp: bool, env_url: str | None = None) -> float:
    """Run the capture pipeline using step() to trigger a randomization and data capture."""
    print(f"Running example with num_frames: {num_frames}, resolution: {resolution}, use_warp: {use_warp}")

    if env_url is not None and env_url != "":
        assets_root_path = get_assets_root_path()
        stage_path = assets_root_path + env_url
        print(f"Opening stage: {stage_path}")
        open_stage(stage_path)
    else:
        omni.usd.get_context().new_stage()
        rep.functional.create.dome_light(intensity=1000, rotation=(270, 0, 0))
        ground_plane = rep.functional.create.plane(scale=(10, 10, 1), position=(0, 0, 0))
        rep.functional.physics.apply_collider(ground_plane)

    # Use a fixed global seed for reproducibility
    rep.set_global_seed(SEED)

    # Disable capture on play, data is captured manually using the step function
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode (2) for best SDG results (Options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Augment the RGB and depth annotators
    rgb_to_bgr_augm = rep.annotators.Augmentation.from_function(rgb_to_bgr_wp if use_warp else rgb_to_bgr_np)
    depth_aug = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")
    rgb_to_bgr_annot = rep.annotators.augment(
        source_annotator=rep.annotators.get("rgb"),
        augmentation=rgb_to_bgr_augm,
    )
    depth_annot_1 = rep.annotators.get("distance_to_camera")
    depth_annot_1.augment(depth_aug)
    depth_annot_2 = rep.annotators.get("distance_to_camera")
    depth_annot_2.augment(depth_aug, sigma=0.5)

    # Create the render product and attach the annotators to it
    cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
    rp = rep.create.render_product(cam, resolution)
    rgb_to_bgr_annot.attach(rp)
    depth_annot_1.attach(rp)
    depth_annot_2.attach(rp)

    # Create a red cube and randomize its rotation on a custom event sent before each capture step
    red_cube = rep.functional.create.cube(position=(0, 0, 0.71))
    rep.functional.create.material(mdl="OmniPBR.mdl", bind_prims=[red_cube], diffuse_color_constant=(1, 0, 0))

    with rep.trigger.on_custom_event(event_name="randomize_red_cube"):
        red_cube_node = rep.get.prim_at_path(red_cube.GetPath())
        with red_cube_node:
            rep.randomizer.rotation()

    # Output directory
    out_dir = os.path.join(os.getcwd(), f"_out_augm_annot_{'warp' if use_warp else 'numpy'}")
    print(f"Writing data to: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)

    capture_start = time.time()
    for frame_idx in range(num_frames):
        print(f"  Capturing frame {frame_idx + 1}/{num_frames}")
        rep.utils.send_og_event(event_name="randomize_red_cube")
        rep.orchestrator.step(rt_subframes=32)

        # Get the data from the annotators
        rgb_data = rgb_to_bgr_annot.get_data()
        depth_data_1 = depth_annot_1.get_data()
        depth_data_2 = depth_annot_2.get_data()

        # Schedule the write of the data to disk
        write_image(path=os.path.join(out_dir, f"annot_rgb_{frame_idx}.png"), data=rgb_data)
        write_image(
            path=os.path.join(out_dir, f"annot_depth_1_{frame_idx}.png"),
            data=convert_depth_to_uint8(depth_data_1),
        )
        write_image(
            path=os.path.join(out_dir, f"annot_depth_2_{frame_idx}.png"),
            data=convert_depth_to_uint8(depth_data_2),
        )

    # Wait for the data to be written to disk and release resources
    rep.orchestrator.wait_until_complete()
    rgb_to_bgr_annot.detach()
    depth_annot_1.detach()
    depth_annot_2.detach()
    rp.destroy()

    return time.time() - capture_start


duration = run_example(num_frames, resolution, use_warp, env_url)
average = duration / num_frames if num_frames else 0.0
mode_label = "warp" if use_warp else "numpy"
print(
    f"The duration for capturing {num_frames} frames using '{mode_label}' was: {duration:.4f} seconds, "
    f"with an average of {average:.4f} seconds per frame."
)

simulation_app.close()

```
Copy to clipboard
Script Editor
Full Script Editor Script

```
import asyncio
import os
import time

import carb.settings
import numpy as np
import omni.replicator.core as rep
import warp as wp
from isaacsim.core.experimental.utils.stage import open_stage
from isaacsim.storage.native import get_assets_root_path_async
from omni.replicator.core.functional import write_image

NUM_FRAMES = 5
RESOLUTION = (512, 512)
USE_WARP = False
ENV_URL = "/Isaac/Environments/Grid/default_environment.usd"
SEED = 42

# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)


def rgb_to_bgr_np(data_in):
    """Swap RGBA red and blue channels using NumPy (CPU)."""
    data_in[:, :, [0, 2]] = data_in[:, :, [2, 0]]
    return data_in


@wp.kernel
def rgb_to_bgr_wp(data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8)):
    """Swap RGBA red and blue channels using Warp (GPU)."""
    i, j = wp.tid()
    data_out[i, j, 0] = data_in[i, j, 2]
    data_out[i, j, 1] = data_in[i, j, 1]
    data_out[i, j, 2] = data_in[i, j, 0]
    data_out[i, j, 3] = data_in[i, j, 3]


def gaussian_noise_depth_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.annotators.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=SEED)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.annotators.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=SEED)
)


def convert_depth_to_uint8(data):
    """Normalize depth data and convert it to uint8 grayscale."""
    if isinstance(data, wp.array):
        data = data.numpy()
    depth = data.astype(np.float32, copy=False)
    depth[np.isinf(depth)] = np.nan
    mean_val = np.nanmean(depth)
    if np.isnan(mean_val):
        mean_val = 0.0
    depth = np.nan_to_num(depth, nan=mean_val, copy=False)
    min_val = depth.min()
    max_val = depth.max()
    if max_val <= min_val:
        return np.zeros(depth.shape, dtype=np.uint8)
    normalized = (depth - min_val) / (max_val - min_val)
    return (normalized * 255.0).astype(np.uint8)


# Run the capture pipeline using step() to trigger a randomization and data capture
async def run_example_async(num_frames: int, resolution: tuple[int, int], use_warp: bool) -> float:
    print(f"Running example with num_frames: {num_frames}, resolution: {resolution}, use_warp: {use_warp}")

    # Open a new stage
    assets_root_path = await get_assets_root_path_async()
    stage_path = assets_root_path + ENV_URL
    print(f"Opening stage: {stage_path}")
    open_stage(stage_path)

    # Use a fixed global seed for reproducibility
    rep.set_global_seed(SEED)

    # Disable capture on play, data is captured manually using the step function
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode (2) for best SDG results (Options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Augment the RGB and depth annotators
    rgb_to_bgr_augm = rep.annotators.Augmentation.from_function(rgb_to_bgr_wp if use_warp else rgb_to_bgr_np)
    depth_aug = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")
    rgb_to_bgr_annot = rep.annotators.augment(
        source_annotator=rep.annotators.get("rgb"),
        augmentation=rgb_to_bgr_augm,
    )
    depth_annot_1 = rep.annotators.get("distance_to_camera")
    depth_annot_1.augment(depth_aug)
    depth_annot_2 = rep.annotators.get("distance_to_camera")
    depth_annot_2.augment(depth_aug, sigma=0.5)

    # Create the render product and attach the annotators to it
    cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
    rp = rep.create.render_product(cam, resolution)
    rgb_to_bgr_annot.attach(rp)
    depth_annot_1.attach(rp)
    depth_annot_2.attach(rp)

    # Create a red cube and randomize its rotation on a custom event sent before each capture step
    red_cube = rep.functional.create.cube(position=(0, 0, 0.71))
    rep.functional.create.material(mdl="OmniPBR.mdl", bind_prims=[red_cube], diffuse_color_constant=(1, 0, 0))

    with rep.trigger.on_custom_event(event_name="randomize_red_cube"):
        red_cube_node = rep.get.prim_at_path(red_cube.GetPath())
        with red_cube_node:
            rep.randomizer.rotation()

    # Output directory
    out_dir = os.path.join(os.getcwd(), "_out_augm_annot")
    print(f"Writing data to: {out_dir}")
    os.makedirs(out_dir, exist_ok=True)

    capture_start = time.time()
    for frame_idx in range(num_frames):
        print(f"  Capturing frame {frame_idx + 1}/{num_frames}")
        rep.utils.send_og_event(event_name="randomize_red_cube")
        await rep.orchestrator.step_async(rt_subframes=32)

        # Get the data from the annotators
        rgb_data = rgb_to_bgr_annot.get_data()
        depth_data_1 = depth_annot_1.get_data()
        depth_data_2 = depth_annot_2.get_data()

        # Schedule the write of the data to disk
        write_image(path=os.path.join(out_dir, f"annot_rgb_{frame_idx}.png"), data=rgb_data)
        write_image(
            path=os.path.join(out_dir, f"annot_depth_1_{frame_idx}.png"),
            data=convert_depth_to_uint8(depth_data_1),
        )
        write_image(
            path=os.path.join(out_dir, f"annot_depth_2_{frame_idx}.png"),
            data=convert_depth_to_uint8(depth_data_2),
        )

    # Wait for the data to be written to disk and release resources
    await rep.orchestrator.wait_until_complete_async()
    rgb_to_bgr_annot.detach()
    depth_annot_1.detach()
    depth_annot_2.detach()
    rp.destroy()

    return time.time() - capture_start


def on_task_done(task: asyncio.Task):
    """Report timing information when capture completes."""
    duration = task.result()
    average = duration / NUM_FRAMES if NUM_FRAMES else 0.0
    mode_label = "warp" if USE_WARP else "numpy"
    print(
        f"The duration for capturing {NUM_FRAMES} frames using '{mode_label}' was: {duration:.4f} seconds, "
        f"with an average of {average:.4f} seconds per frame."
    )


task = asyncio.ensure_future(run_example_async(NUM_FRAMES, RESOLUTION, USE_WARP))
task.add_done_callback(on_task_done)

```
Copy to clipboard
Code Explanation
To be able to run the augmentation functions, enable scripting in the settings:
Enable Scripting

```
# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)

```
Copy to clipboard
To augment the **rgb** data we provide for illustrative purposes a function that switches the red and blue channels in the rgb data using NumPy (CPU) and warp (GPU) kernels:
RGB to BGR using Warp and Numpy

```
def rgb_to_bgr_np(data_in):
    """Swap RGBA red and blue channels using NumPy (CPU)."""
    data_in[:, :, [0, 2]] = data_in[:, :, [2, 0]]
    return data_in


@wp.kernel
def rgb_to_bgr_wp(data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8)):
    """Swap RGBA red and blue channels using Warp (GPU)."""
    i, j = wp.tid()
    data_out[i, j, 0] = data_in[i, j, 2]
    data_out[i, j, 1] = data_in[i, j, 1]
    data_out[i, j, 2] = data_in[i, j, 0]
    data_out[i, j, 3] = data_in[i, j, 3]

```
Copy to clipboard
For the **depth** data we use gaussian noise filters. Note that the functions are registered in the annotator registry for later access:
Depth Gaussian Noise using Warp and Numpy

```
def gaussian_noise_depth_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.annotators.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=SEED)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.annotators.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=SEED)
)

```
Copy to clipboard
Create the augmentations (warp or NumPy) once using the function directly and once from the registry:
Augmentations using Warp or Numpy

```
# Augment the RGB and depth annotators
rgb_to_bgr_augm = rep.annotators.Augmentation.from_function(rgb_to_bgr_wp if use_warp else rgb_to_bgr_np)
depth_aug = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")
rgb_to_bgr_annot = rep.annotators.augment(
    source_annotator=rep.annotators.get("rgb"),
    augmentation=rgb_to_bgr_augm,
)
depth_annot_1 = rep.annotators.get("distance_to_camera")
depth_annot_1.augment(depth_aug)
depth_annot_2 = rep.annotators.get("distance_to_camera")
depth_annot_2.augment(depth_aug, sigma=0.5)

```
Copy to clipboard
You can also register a new annotator together with its augmentation:
Register Augmentated Annotator

```
rgb_to_bgr_annot = rep.annotators.augment(
    source_annotator=rep.annotators.get("rgb"),
    augmentation=rgb_to_bgr_augm,
)
depth_annot_1 = rep.annotators.get("distance_to_camera")
depth_annot_1.augment(depth_aug)
depth_annot_2 = rep.annotators.get("distance_to_camera")
depth_annot_2.augment(depth_aug, sigma=0.5)

```
Copy to clipboard
Finally create the augmented annotators (1x **rgb** , 2x **depth**) and attach them to a render product to generate data:
Annotator Augmentation

```
# Create the render product and attach the annotators to it
cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
rp = rep.create.render_product(cam, resolution)
rgb_to_bgr_annot.attach(rp)
depth_annot_1.attach(rp)
depth_annot_2.attach(rp)

```
Copy to clipboard
### Writer Augmentation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_augmentation.html#writer-augmentation "Link to this heading")
The **writer** example will output gaussian noise augmented RGB and depth annotator data from a writer.
Standalone Application
The example can be run as a standalone application using the following commands in the terminal (on Windows use `python.bat` instead of `python.sh`):
> 
```
./python.sh standalone_examples/replicator/augmentation/writer_augmentation.py --env_url /Isaac/Environments/Grid/default_environment.usd

```
Copy to clipboard
> Optionally the following arguments can be used to change the default behavior:
>   * `--env_url` – USD environment path relative to the assets root (default: empty scene with dome light and ground plane)
>   * `--use_warp` – flag to use warp (GPU) instead of NumPy (CPU) for the augmentation functions (default: False)
>   * `--num_frames` – the number of frames to be captured (default: 25)
> 

> 
```
./python.sh standalone_examples/replicator/augmentation/writer_augmentation.py --use_warp --num_frames 25 --env_url /Isaac/Environments/Grid/default_environment.usd

```
Copy to clipboard
> Full Standalone Script
> 
```
"""Generate augmented synthetic data from a writer."""

from isaacsim import SimulationApp

simulation_app = SimulationApp(launch_config={"headless": False})

import argparse
import os
import time

import carb.settings
import numpy as np
import omni.replicator.core as rep
import omni.usd
import warp as wp
from isaacsim.core.utils.stage import open_stage
from isaacsim.storage.native import get_assets_root_path

parser = argparse.ArgumentParser()
parser.add_argument("--num_frames", type=int, default=5, help="The number of frames to capture")
parser.add_argument(
    "--use_warp",
    action="store_true",
    help="Use warp augmentations instead of numpy",
)
parser.add_argument("--resolution", nargs=2, type=int, default=[512, 512], help="Camera resolution")
parser.add_argument("--env_url", type=str, default="", help="USD environment URL (empty for basic scene)")
args, unknown = parser.parse_known_args()

num_frames = args.num_frames
use_warp = args.use_warp
resolution = args.resolution
env_url = args.env_url or None
SEED = 42

# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)


def gaussian_noise_rgb_np(data_in, sigma, seed):
    """Add Gaussian noise to RGB data using NumPy (CPU)."""
    np.random.seed(seed)
    # Convert to float32 space
    data_in = data_in.astype(np.float32)
    # Add Gaussian noise to each channel
    data_in[:, :, 0] = data_in[:, :, 0] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 1] = data_in[:, :, 1] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 2] = data_in[:, :, 2] + np.random.randn(*data_in.shape[:-1]) * sigma
    # Clip to [0, 255] and convert to uint8
    data_in = np.clip(data_in, 0, 255).astype(np.uint8)
    return data_in


@wp.kernel
def gaussian_noise_rgb_wp(
    data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8), sigma: float, seed: int
):
    """Add Gaussian noise to RGB data using Warp (GPU)."""
    # Get thread coordinates and image dimensions to calculate unique pixel ID for random generation
    i, j = wp.tid()
    dim_i = data_in.shape[0]
    dim_j = data_in.shape[1]
    pixel_id = i * dim_i + j

    # Use pixel_id as offset to create unique seeds for each pixel and channel (ensure independent noise patterns across R,G,B channels)
    state_r = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 0))
    state_g = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 1))
    state_b = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 2))

    # Apply noise to each channel independently using unique seeds; work in float32 space, then clip and convert to uint8
    val_r = wp.float32(data_in[i, j, 0]) + sigma * wp.randn(state_r)
    val_g = wp.float32(data_in[i, j, 1]) + sigma * wp.randn(state_g)
    val_b = wp.float32(data_in[i, j, 2]) + sigma * wp.randn(state_b)

    # Clip to [0, 255] and convert to uint8
    data_out[i, j, 0] = wp.uint8(wp.clamp(val_r, 0.0, 255.0))
    data_out[i, j, 1] = wp.uint8(wp.clamp(val_g, 0.0, 255.0))
    data_out[i, j, 2] = wp.uint8(wp.clamp(val_b, 0.0, 255.0))
    data_out[i, j, 3] = data_in[i, j, 3]


def gaussian_noise_depth_np(data_in, sigma, seed):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.AnnotatorRegistry.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=None)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.AnnotatorRegistry.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=None)
)


def run_example(num_frames: int, resolution: tuple[int, int], use_warp: bool, env_url: str | None = None) -> float:
    """Run the capture pipeline using step() to trigger a randomization and data capture."""
    print(f"Running example with num_frames: {num_frames}, resolution: {resolution}, use_warp: {use_warp}")

    if env_url is not None and env_url != "":
        assets_root_path = get_assets_root_path()
        stage_path = assets_root_path + env_url
        print(f"Opening stage: {stage_path}")
        open_stage(stage_path)
    else:
        omni.usd.get_context().new_stage()
        rep.functional.create.dome_light(intensity=1000, rotation=(270, 0, 0))
        ground_plane = rep.functional.create.plane(scale=(10, 10, 1), position=(0, 0, 0))
        rep.functional.physics.apply_collider(ground_plane)

    # Use a fixed global seed for reproducibility
    rep.set_global_seed(SEED)

    # Disable capture on play, data is captured manually using the step function
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode (2) for best SDG results (Options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Augment the annotators
    rgb_to_hsv_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_rgb_to_hsv)
    hsv_to_rgb_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_hsv_to_rgb)

    # Augment the RGB and depth annotators
    gn_rgb_augm = rep.annotators.Augmentation.from_function(
        gaussian_noise_rgb_wp if use_warp else gaussian_noise_rgb_np, sigma=15.0, seed=SEED
    )
    gn_depth_augm = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")

    # Create a writer and apply the augmentations to its corresponding annotators
    out_dir = os.path.join(os.getcwd(), f"_out_augm_writer_{'warp' if use_warp else 'numpy'}")
    backend = rep.backends.get("DiskBackend")
    backend.initialize(output_dir=out_dir)
    print(f"Writing data to: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(backend=backend, rgb=True, distance_to_camera=True, colorize_depth=True)

    # Apply the augmentations to the RGB and depth annotators
    augmented_rgb_annot = rep.annotators.get("rgb").augment_compose(
        [rgb_to_hsv_augm, gn_rgb_augm, hsv_to_rgb_augm], name="rgb"
    )
    writer.add_annotator(augmented_rgb_annot)
    writer.augment_annotator("distance_to_camera", gn_depth_augm)

    # Create a camera and a render product and attach them to the writer
    cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
    rp = rep.create.render_product(cam, resolution)
    writer.attach(rp)

    # Create a red cube and randomize its rotation on a custom event sent before each capture step
    red_cube = rep.functional.create.cube(position=(0, 0, 0.71))
    rep.functional.create.material(mdl="OmniPBR.mdl", bind_prims=[red_cube], diffuse_color_constant=(1, 0, 0))
    with rep.trigger.on_custom_event(event_name="randomize_red_cube"):
        red_cube_node = rep.get.prim_at_path(red_cube.GetPath())
        with red_cube_node:
            rep.randomizer.rotation()

    capture_start = time.time()
    for frame_idx in range(num_frames):
        print(f"  Capturing frame {frame_idx + 1}/{num_frames}")
        rep.utils.send_og_event(event_name="randomize_red_cube")
        rep.orchestrator.step(rt_subframes=32)

    # Wait for the data to be written to disk and release resources
    rep.orchestrator.wait_until_complete()
    writer.detach()
    rp.destroy()

    return time.time() - capture_start


duration = run_example(num_frames, resolution, use_warp, env_url)
average = duration / num_frames if num_frames else 0.0
mode_label = "warp" if use_warp else "numpy"
print(
    f"The duration for capturing {num_frames} frames using '{mode_label}' was: {duration:.4f} seconds, "
    f"with an average of {average:.4f} seconds per frame."
)

simulation_app.close()

```
Copy to clipboard
Script Editor
Full Script Editor Script

```
import asyncio
import os
import time

import carb.settings
import numpy as np
import omni.replicator.core as rep
import warp as wp
from isaacsim.core.experimental.utils.stage import open_stage
from isaacsim.storage.native import get_assets_root_path_async

NUM_FRAMES = 5
RESOLUTION = (512, 512)
USE_WARP = False
ENV_URL = "/Isaac/Environments/Grid/default_environment.usd"
SEED = 42

# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)


def gaussian_noise_rgb_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to RGB data using NumPy (CPU)."""
    np.random.seed(seed)
    # Convert to float32 space
    data_in = data_in.astype(np.float32)
    # Add Gaussian noise to each channel
    data_in[:, :, 0] = data_in[:, :, 0] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 1] = data_in[:, :, 1] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 2] = data_in[:, :, 2] + np.random.randn(*data_in.shape[:-1]) * sigma
    # Clip to [0, 255] and convert to uint8
    data_in = np.clip(data_in, 0, 255).astype(np.uint8)
    return data_in


@wp.kernel
def gaussian_noise_rgb_wp(
    data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8), sigma: float, seed: int
):
    """Add Gaussian noise to RGB data using Warp (GPU)."""
    # Get thread coordinates and image dimensions to calculate unique pixel ID for random generation
    i, j = wp.tid()
    dim_i = data_in.shape[0]
    dim_j = data_in.shape[1]
    pixel_id = i * dim_i + j

    # Use pixel_id as offset to create unique seeds for each pixel and channel (ensure independent noise patterns across R,G,B channels)
    state_r = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 0))
    state_g = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 1))
    state_b = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 2))

    # Apply noise to each channel independently using unique seeds; work in float32 space, then clip and convert to uint8
    val_r = wp.float32(data_in[i, j, 0]) + sigma * wp.randn(state_r)
    val_g = wp.float32(data_in[i, j, 1]) + sigma * wp.randn(state_g)
    val_b = wp.float32(data_in[i, j, 2]) + sigma * wp.randn(state_b)

    # Clip to [0, 255] and convert to uint8
    data_out[i, j, 0] = wp.uint8(wp.clamp(val_r, 0.0, 255.0))
    data_out[i, j, 1] = wp.uint8(wp.clamp(val_g, 0.0, 255.0))
    data_out[i, j, 2] = wp.uint8(wp.clamp(val_b, 0.0, 255.0))
    data_out[i, j, 3] = data_in[i, j, 3]


def gaussian_noise_depth_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.annotators.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=SEED)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.annotators.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=SEED)
)


# Run the capture pipeline using step() to trigger a randomization and data capture
async def run_example_async(num_frames: int, resolution: tuple[int, int], use_warp: bool) -> float:
    print(f"Running example with num_frames: {num_frames}, resolution: {resolution}, use_warp: {use_warp}")

    # Open a new stage
    assets_root_path = await get_assets_root_path_async()
    stage_path = assets_root_path + ENV_URL
    print(f"Opening stage: {stage_path}")
    open_stage(stage_path)

    # Use a fixed global seed for reproducibility
    rep.set_global_seed(SEED)

    # Disable capture on play, data is captured manually using the step function
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode (2) for best SDG results (Options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Augment the annotators
    rgb_to_hsv_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_rgb_to_hsv)
    hsv_to_rgb_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_hsv_to_rgb)

    # Augment the RGB and depth annotators
    gn_rgb_augm = rep.annotators.Augmentation.from_function(
        gaussian_noise_rgb_wp if use_warp else gaussian_noise_rgb_np, sigma=15.0, seed=SEED
    )
    gn_depth_augm = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")

    # Create a writer and apply the augmentations to its corresponding annotators
    out_dir = os.path.join(os.getcwd(), "_out_augm_writer")
    backend = rep.backends.get("DiskBackend")
    backend.initialize(output_dir=out_dir)
    print(f"Writing data to: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(backend=backend, rgb=True, distance_to_camera=True, colorize_depth=True)

    # Apply the augmentations to the RGB and depth annotators
    augmented_rgb_annot = rep.annotators.get("rgb").augment_compose(
        [rgb_to_hsv_augm, gn_rgb_augm, hsv_to_rgb_augm], name="rgb"
    )
    writer.add_annotator(augmented_rgb_annot)
    writer.augment_annotator("distance_to_camera", gn_depth_augm)

    # Create a camera and a render product and attach them to the writer
    cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
    rp = rep.create.render_product(cam, resolution)
    writer.attach(rp)

    # Create a red cube and randomize its rotation on a custom event sent before each capture step
    red_cube = rep.functional.create.cube(position=(0, 0, 0.71))
    rep.functional.create.material(mdl="OmniPBR.mdl", bind_prims=[red_cube], diffuse_color_constant=(1, 0, 0))
    with rep.trigger.on_custom_event(event_name="randomize_red_cube"):
        red_cube_node = rep.get.prim_at_path(red_cube.GetPath())
        with red_cube_node:
            rep.randomizer.rotation()

    capture_start = time.time()
    for frame_idx in range(num_frames):
        print(f"  Capturing frame {frame_idx + 1}/{num_frames}")
        rep.utils.send_og_event(event_name="randomize_red_cube")
        await rep.orchestrator.step_async(rt_subframes=32)

    # Wait for the data to be written to disk and release resources
    await rep.orchestrator.wait_until_complete_async()
    writer.detach()
    rp.destroy()

    return time.time() - capture_start


def on_task_done(task: asyncio.Task):
    """Report timing information when capture completes."""
    duration = task.result()
    average = duration / NUM_FRAMES if NUM_FRAMES else 0.0
    mode_label = "warp" if USE_WARP else "numpy"
    print(
        f"The duration for capturing {NUM_FRAMES} frames using '{mode_label}' was: {duration:.4f} seconds, "
        f"with an average of {average:.4f} seconds per frame."
    )


task = asyncio.ensure_future(run_example_async(NUM_FRAMES, RESOLUTION, USE_WARP))
task.add_done_callback(on_task_done)

```
Copy to clipboard
Code Explanation
To be able to run the augmentation functions one needs to enable scripting in the settings:
Enable Scripting

```
# Enable warp scripts
carb.settings.get_settings().set_bool("/app/omni.graph.scriptnode/opt_in", True)

```
Copy to clipboard
For the **rgb** (**LdrColor**) annotator of the writer, we provide gaussian noise functions using NumPy (CPU) and warp (GPU) kernels, applied on the RGB channels of the RGBA provided data format.
RGB Gaussian Noise using Warp and Numpy

```
def gaussian_noise_rgb_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to RGB data using NumPy (CPU)."""
    np.random.seed(seed)
    # Convert to float32 space
    data_in = data_in.astype(np.float32)
    # Add Gaussian noise to each channel
    data_in[:, :, 0] = data_in[:, :, 0] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 1] = data_in[:, :, 1] + np.random.randn(*data_in.shape[:-1]) * sigma
    data_in[:, :, 2] = data_in[:, :, 2] + np.random.randn(*data_in.shape[:-1]) * sigma
    # Clip to [0, 255] and convert to uint8
    data_in = np.clip(data_in, 0, 255).astype(np.uint8)
    return data_in


@wp.kernel
def gaussian_noise_rgb_wp(
    data_in: wp.array3d(dtype=wp.uint8), data_out: wp.array3d(dtype=wp.uint8), sigma: float, seed: int
):
    """Add Gaussian noise to RGB data using Warp (GPU)."""
    # Get thread coordinates and image dimensions to calculate unique pixel ID for random generation
    i, j = wp.tid()
    dim_i = data_in.shape[0]
    dim_j = data_in.shape[1]
    pixel_id = i * dim_i + j

    # Use pixel_id as offset to create unique seeds for each pixel and channel
    state_r = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 0))
    state_g = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 1))
    state_b = wp.rand_init(seed, pixel_id + (dim_i * dim_j * 2))

    # Apply noise to each channel independently using unique seeds
    val_r = wp.float32(data_in[i, j, 0]) + sigma * wp.randn(state_r)
    val_g = wp.float32(data_in[i, j, 1]) + sigma * wp.randn(state_g)
    val_b = wp.float32(data_in[i, j, 2]) + sigma * wp.randn(state_b)

    # Clip to [0, 255] and convert to uint8
    data_out[i, j, 0] = wp.uint8(wp.clamp(val_r, 0.0, 255.0))
    data_out[i, j, 1] = wp.uint8(wp.clamp(val_g, 0.0, 255.0))
    data_out[i, j, 2] = wp.uint8(wp.clamp(val_b, 0.0, 255.0))
    data_out[i, j, 3] = data_in[i, j, 3]

```
Copy to clipboard
For the **depth** annotator of the writer, there are gaussian noise functions using NumPy (CPU) and warp (GPU) kernels, applied on the 2D array of float32 values. The functions are registered in the annotator registry for later access:
Depth Gaussian Noise using Warp and Numpy

```
def gaussian_noise_depth_np(data_in, sigma: float, seed: int):
    """Add Gaussian noise to depth values using NumPy (CPU)."""
    np.random.seed(seed)
    result = data_in.astype(np.float32) + np.random.randn(*data_in.shape) * sigma
    return np.clip(result, 0, None).astype(data_in.dtype)


rep.AnnotatorRegistry.register_augmentation(
    "gn_depth_np", rep.annotators.Augmentation.from_function(gaussian_noise_depth_np, sigma=0.1, seed=None)
)


@wp.kernel
def gaussian_noise_depth_wp(
    data_in: wp.array2d(dtype=wp.float32), data_out: wp.array2d(dtype=wp.float32), sigma: float, seed: int
):
    """Add Gaussian noise to depth values using Warp (GPU)."""
    i, j = wp.tid()
    # Unique ID for random seed per pixel
    scalar_pixel_id = i * data_in.shape[1] + j
    state = wp.rand_init(seed, scalar_pixel_id)
    data_out[i, j] = data_in[i, j] + sigma * wp.randn(state)


rep.AnnotatorRegistry.register_augmentation(
    "gn_depth_wp", rep.annotators.Augmentation.from_function(gaussian_noise_depth_wp, sigma=0.1, seed=None)
)

```
Copy to clipboard
Access the default (**rgb**) augmentations from replicator:
Built-in Replicator Augmentations

```
# Augment the annotators
rgb_to_hsv_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_rgb_to_hsv)
hsv_to_rgb_augm = rep.annotators.Augmentation.from_function(rep.augmentations_default.aug_hsv_to_rgb)

```
Copy to clipboard
Furthermore the custom augmentations are created (warp or NumPy), after using the function directly and once from the registry:
Augmentations using Warp or Numpy

```
# Augment the RGB and depth annotators
gn_rgb_augm = rep.annotators.Augmentation.from_function(
    gaussian_noise_rgb_wp if use_warp else gaussian_noise_rgb_np, sigma=15.0, seed=SEED
)
gn_depth_augm = rep.annotators.get_augmentation("gn_depth_wp" if use_warp else "gn_depth_np")

```
Copy to clipboard
Finally the writer is created and initialized to use the **rgb** and **depth** (**distance_to_camera**) annotators. The built-in `rgb` annotator is replaced by a new augmented one by using the same `name="rgb"` name and adding it to the writer (`add_annotator`). The augmented RGB annotator uses a composition by switching the data to hsv, adding gaussian noise, and switching back to RGB. The `distance_to_camera` annotator is augmented by using the built-in `augment_annotator` function:
Writer Augmentation

```
# Create a writer and apply the augmentations to its corresponding annotators
out_dir = os.path.join(os.getcwd(), f"_out_augm_writer_{'warp' if use_warp else 'numpy'}")
backend = rep.backends.get("DiskBackend")
backend.initialize(output_dir=out_dir)
print(f"Writing data to: {out_dir}")
writer = rep.writers.get("BasicWriter")
writer.initialize(backend=backend, rgb=True, distance_to_camera=True, colorize_depth=True)

# Apply the augmentations to the RGB and depth annotators
augmented_rgb_annot = rep.annotators.get("rgb").augment_compose(
    [rgb_to_hsv_augm, gn_rgb_augm, hsv_to_rgb_augm], name="rgb"
)
writer.add_annotator(augmented_rgb_annot)
writer.augment_annotator("distance_to_camera", gn_depth_augm)

# Create a camera and a render product and attach them to the writer
cam = rep.functional.create.camera(position=(0, 0, 5), look_at=(0, 0, 0))
rp = rep.create.render_product(cam, resolution)
writer.attach(rp)

```
Copy to clipboard
