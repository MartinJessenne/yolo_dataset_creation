---
source: https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html
---

# SDG Workflows[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#sdg-workflows "Link to this heading")
This tutorial walks through two complete synthetic data generation (SDG) scripts. Each script authors a USD scene, randomizes it, runs the simulation, and writes annotated images to disk through a `BasicWriter`. The two scripts share the same setup code but solve different problems: the first reuses one persistent scene and settles physics between captures, the second rebuilds the scene on a cadence and places assets with collision checks.
This tutorial is for developers who are comfortable with rigid-body simulation and USD scene graphs and want to see the Replicator API used end to end. By the end you will recognize the settings every SDG script configures at startup, the capture loop pattern both workflows follow, and the gotchas that produce corrupt or low-quality datasets.
## Prerequisites[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#prerequisites "Link to this heading")
Before starting, make sure you have:
  * Read [Getting Started Scripts](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_getting_started.html#isaac-sim-app-tutorial-replicator-getting-started). It introduces the orchestrator step, the capture-on-play flag, `rt_subframes`, `wait_for_render`, `wait_until_complete`, and DLSS quality mode one concept at a time. This tutorial assumes you know what each one does.
  * Familiarity with USD (Universal Scene Description) concepts: prims, scopes, references, and transforms.
  * A working Isaac Sim install you can run as a [Standalone Application](https://docs.isaacsim.omniverse.nvidia.com/latest/introduction/workflows.html#standalone-application) or through the [Script Editor](https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/omniverse_script_editor.html#script-editor).
  * Enough disk space for the captured dataset (scales with resolution and frame count).


## Setup and Configuration[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#setup-and-configuration "Link to this heading")
Both scripts run the same startup sequence before the capture loop. Each setting below shows the API call, why the workflows use it, and the effect of omitting it. The excerpts come from the example scripts shown later.
## Writers and Backends[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#writers-and-backends "Link to this heading")
A _writer_ formats annotator output (RGB, depth, segmentation, bounding boxes, and so on) and hands it to a _backend_ that performs the I/O. Both workflows attach the built-in `BasicWriter` to a `DiskBackend` and request RGB and colorized semantic segmentation:

```
backend = rep.backends.get("DiskBackend")
backend.initialize(output_dir=out_dir)
writer = rep.writers.get("BasicWriter")
writer.initialize(
    backend=backend,
    rgb=True,
    semantic_segmentation=True,
    colorize_semantic_segmentation=True,
)
writer.attach(rp)

```
Copy to clipboard
`attach` connects the writer to one or more render products. After this call, every orchestrator step routes that render product’s annotator data through the writer. Each annotator you enable (`rgb`, `semantic_segmentation`, and so on) adds GPU and I/O cost, so enable only what your dataset needs.
Replicator ships other built-in writers, for example `PoseWriter` (6-DoF object pose data) and `CosmosWriter` (multi-modal training data for [NVIDIA Cosmos](https://www.nvidia.com/en-us/ai/cosmos/)). To emit any other format, register a [custom writer](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html "\(in Omniverse Extensions\)"). See [writer examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html "\(in Omniverse Extensions\)") for the full list and [annotators](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html "\(in Omniverse Extensions\)") for the data sources writers can consume.
## Capture on Play Flag[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#capture-on-play-flag "Link to this heading")
By default Replicator captures a frame every time the timeline ticks. Both workflows capture data at specific timepoints rather than continuously, so they disable this flag once at startup and trigger each capture explicitly:

```
rep.orchestrator.set_capture_on_play(False)

```
Copy to clipboard
After this call the writer receives only frames produced by an explicit `step()` (or `step_async`). This lets Workflow 1 advance several physics frames between captures without recording any of them.
## Orchestrator Step[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#orchestrator-step "Link to this heading")
`rep.orchestrator.step()` (`step_async()` in the Script Editor) captures and processes one frame for the attached writers and annotators. Each workflow calls it once per capture. Its parameters are:

```
rep.orchestrator.step(rt_subframes=-1, pause_timeline=True, delta_time=None, wait_for_render=True)

```
Copy to clipboard
  * `rt_subframes` - number of subframes rendered before the frame is captured, covered in [RT Subframes](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#isaac-sim-app-tutorial-replicator-sdg-workflows-rt-subframes) below.
  * `pause_timeline` - pause the timeline after the step. Defaults to `True`
  * `delta_time` - how far the timeline advances during the step. `None` (default) advances by the timeline’s rate, `0.0` does not advance the timeline, and a positive value advances by that amount.
  * `wait_for_render` - block until the frame finishes rendering. Defaults to `True`. Set it to `False` to let the next randomization start while the previous frame is still rendering, when exact frame-to-state correspondence is not required.


## RT Subframes[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#rt-subframes "Link to this heading")
`rt_subframes` is the number of times the renderer produces the _same_ logical frame before the writer reads its annotators. The simulation is paused during subframe generation. The default is `-1` (use the global `/omni/replicator/RTSubframes` carb setting); per-step values must be greater than `0`. Both workflows pass `rt_subframes=8` because they teleport the camera and randomize materials between captures.
Increase it when:
  * The camera or props moved a lot between two captures (DLSS ghosting; faint trails or blurred silhouettes from the previous frame).
  * Lights, textures, or MDL materials changed between captures (newly assigned materials need a few frames to fully load and resolve in the render graph).
  * Path tracing is enabled or the scene is dimly lit.


Use `rt_subframes=1` only when nothing is changing between captures.
## DLSS Quality Mode[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#dlss-quality-mode "Link to this heading")
Isaac Sim ships with the DLSS denoiser in Performance mode (`execMode=0`). At common SDG resolutions the performance modes can produce visible ghosting around moving edges and incorrect transparency on thin geometry. Both workflows switch DLSS to Quality mode once at startup:

```
import carb.settings

carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

```
Copy to clipboard
Available values: `0` Performance, `1` Balanced, `2` Quality, `3` Auto.
## Render Product Updates[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#render-product-updates "Link to this heading")
A render product ties a camera to the rendering and annotation graph (ray tracing, denoising, segmentation, bounding boxes, etc.). Once created, it keeps rendering on every application tick even when `step()` is not called. This wastes GPU time during physics, scene construction, and randomization.
The pattern both scripts use is to disable updates immediately after the render product is created and re-enable them only around the orchestrator step:

```
rp = rep.create.render_product(cam, RESOLUTION, name="rp_workflow_01")
rp.hydra_texture.set_updates_enabled(False)

# ... scene updates, physics, randomization (no rendering cost) ...

rp.hydra_texture.set_updates_enabled(True)
rep.orchestrator.step(delta_time=0.0, rt_subframes=RT_SUBFRAMES)
rp.hydra_texture.set_updates_enabled(False)

```
Copy to clipboard
The cost difference is most visible in Workflow 1, which advances PhysX many ticks between captures, and in any pipeline with multiple high-resolution cameras.
## Seeded Randomization[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#seeded-randomization "Link to this heading")
The scripts use a single `ReplicatorRNG` instance for all sampling. Helpers such as `randomize_camera`, `scatter_2d`, and `rng.generator.uniform` all take that instance as their `rng=` argument. Seed it once at startup so the script is fully reproducible:

```
rng = rep.rng.ReplicatorRNG(seed=42)

```
Copy to clipboard
The same seed always produces the same dataset, which is useful when regenerating a specific outlier image.
## Wait Until Complete[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#wait-until-complete "Link to this heading")
Replicator writers do their I/O on background threads. If the script closes the application immediately after the last orchestrator step, the writer can still have several frames queued and the dataset will be missing PNGs or have half-written JSON files. Always wait before tearing down:

```
rep.orchestrator.wait_until_complete()                  # standalone
await rep.orchestrator.wait_until_complete_async()      # script editor

```
Copy to clipboard
After `wait_until_complete` returns it is safe to detach the writer, destroy the render product, and close the application.
## Async vs Sync[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#async-vs-sync "Link to this heading")
Each workflow ships with two entry-point scripts that share scene-authoring code but differ in how they drive the application loop:
  * **Script Editor** (`*_script_editor.py`) - executes inside the Isaac Sim [Script Editor](https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/omniverse_script_editor.html#script-editor) window. The entry function is a coroutine that awaits the `_async` Replicator helpers (for example `rep.orchestrator.step_async`) and yields back to the application loop with `await omni.kit.app.get_app().next_update_async()`.
  * **Standalone Application** (`sdg_workflow_*.py`) - launches its own [Standalone Application](https://docs.isaacsim.omniverse.nvidia.com/latest/introduction/workflows.html#standalone-application) (`python.sh` on Linux, `python.bat` on Windows). It uses the synchronous Replicator helpers and drives the application loop directly with `simulation_app.update()`.


## Examples[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#examples "Link to this heading")
The following sections present two complete example scripts that apply the settings from the previous section. Each section describes its scene, its capture loop, and its output on its own. Every script is shown in both the Script Editor and Standalone Application forms described above.
### Workflow 1: Physics-Based Object Settling[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#workflow-1-physics-based-object-settling "Link to this heading")
This workflow builds one scene (dome light, pallet, distractors, cardboxes, and camera) and keeps it for the whole run. Before each capture it re-drops one box and lets PhysX settle it, so every frame shows a slightly different physical arrangement of the same objects. The render product and writer are created once and reused, which avoids per-capture setup cost when the scene structure does not change.
[![Persistent SDG scene where a re-dropped cardbox settles on a pallet between captures](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isim_6.0_replicator_tut_external_workflow_1.webp) ](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isim_6.0_replicator_tut_external_workflow_1.webp)
The script defines helper functions that each randomize one part of the existing scene:
  * `randomize_dome_light` - chooses an HDR texture and intensity for the dome light.
  * `randomize_distractors` - samples positions, rotations, scales, and display colors for the distractor prims.
  * `randomize_pallet` - picks one of the pre-created materials and binds it to the pallet.
  * `randomize_camera` - samples an orbit position around the pallet and points the camera back at it.
  * `randomize_boxes` - writes per-box poses just before the timeline plays so PhysX settles the boxes over `NUM_SIMULATION_FRAMES` ticks.


The capture loop runs `NUM_CAPTURES` times:
  1. Randomize the lighting, distractors, and pallet material with the helpers above.
  2. Pick one box at random, give it a fresh pose, and advance the timeline `NUM_SIMULATION_FRAMES` ticks so PhysX settles the new pose.
  3. Move the camera, enable the render product, call the orchestrator step, then disable the render product again.


Physics runs _between_ captures (step 2), and only the orchestrator step (step 3) produces a frame.
The standalone example can also be run directly (on Windows use `python.bat` instead of `python.sh`):

```
./python.sh standalone_examples/api/isaacsim.replicator.examples/sdg_workflow_01.py

```
Copy to clipboard
Script Editor

```
"""
Basic SDG workflow with scene creation, asset placement, randomization, and data capture.
Boxes are randomized and simulated with physics before each capture.
"""

import asyncio
import math
import os

import carb
import carb.settings
import omni.kit.app
import omni.replicator.core as rep
import omni.timeline
import omni.usd
from isaacsim.storage.native import get_assets_root_path
from pxr import Usd, UsdGeom, UsdPhysics

NUM_CAPTURES = 5
RESOLUTION = (1280, 720)
RT_SUBFRAMES = 8
NUM_DROP_BOXES = 10
NUM_SIMULATION_FRAMES = 75
NUM_PRIM_DISTRACTORS = 5
ENV_URL = "/Isaac/Environments/Grid/default_environment.usd"


def randomize_distractors(prims, rng):
    # Sample small distractors on a loose ring around the pallet.
    count = len(prims)
    angles = rng.generator.uniform(0.0, 2.0 * math.pi, count)
    radii = rng.generator.uniform(0.9, 1.4, count)
    heights = rng.generator.uniform(0.15, 0.45, count)
    positions = [
        (float(radius * math.cos(angle)), float(radius * math.sin(angle)), float(height))
        for angle, radius, height in zip(angles, radii, heights)
    ]
    rotations = rng.generator.uniform((0.0, 0.0, 0.0), (45.0, 45.0, 360.0), size=(count, 3)).tolist()
    scales = rng.generator.uniform(0.1, 0.2, count).tolist()
    rep.functional.modify.pose(
        prims,
        position_value=positions,
        rotation_value=rotations,
        scale_value=scales,
    )
    rep.functional.randomizer.display_color(prims, rng=rng)


def randomize_dome_light(dome_light, texture_urls, rng):
    texture_url = texture_urls[int(rng.generator.integers(0, len(texture_urls)))]
    intensity = float(rng.generator.uniform(500.0, 900.0))
    rep.functional.modify.attribute(dome_light, "inputs:texture:file", texture_url)
    rep.functional.modify.attribute(dome_light, "inputs:intensity", intensity)


def randomize_pallet(pallet, materials, rng):
    material = materials[int(rng.generator.integers(0, len(materials)))]
    rep.functional.modify.material(pallet, material)


def randomize_camera(camera, look_at, rng):
    theta = float(rng.generator.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.generator.uniform(2.6, 3.4))
    position = (
        radius * math.cos(theta),
        radius * math.sin(theta),
        float(rng.generator.uniform(1.4, 2.2)),
    )
    rep.functional.modify.pose(
        camera,
        position_value=position,
        look_at_value=look_at,
        look_at_up_axis=(0, 0, 1),
        write_to_usd=True,
    )


def randomize_boxes(boxes, start_height, rng):
    for i, box in enumerate(boxes):
        lateral_range = 0.4
        height = start_height + 0.2 * i
        tilt_range = 15.0
        rep.functional.modify.pose(
            box,
            position_value=(
                float(rng.generator.uniform(-lateral_range, lateral_range)),
                float(rng.generator.uniform(-lateral_range, lateral_range)),
                height,
            ),
            rotation_value=(
                float(rng.generator.uniform(0.0, tilt_range)),
                float(rng.generator.uniform(0.0, tilt_range)),
                float(rng.generator.uniform(0.0, 360.0)),
            ),
            write_to_usd=True,
        )


async def run_workflow_async():
    assets_root_path = get_assets_root_path()
    if assets_root_path is None:
        carb.log_error("[SDG] Could not resolve assets root path; aborting.")
        return

    # Load stage.
    env_path = assets_root_path + ENV_URL
    stage, error = await omni.usd.get_context().open_stage_async(env_path)
    if error or stage is None:
        carb.log_error(f"[SDG] Failed to open stage: '{env_path}', exiting.")
        return

    # Disable automatic capture so only explicit `step_async()` calls write frames.
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode to reduce low-resolution SDG rendering artifacts.
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Seed the functional randomizer so re-running the script is reproducible.
    rng = rep.rng.ReplicatorRNG(seed=42)

    # Create a dome light which will be randomized by texture and brightness.
    rep.functional.create.xform(name="SDG")
    rep.functional.create.scope(name="Lights", parent="/SDG")
    dome_texture_urls = [
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/autoshop_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/carpentry_shop_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/wooden_lounge_4k.hdr",
    ]
    dome_light = rep.functional.create.dome_light(
        texture=dome_texture_urls[0],
        intensity=700,
        parent="/SDG/Lights",
        name="DomeLight",
    )
    randomize_dome_light(dome_light, dome_texture_urls, rng=rng)

    # Create a pallet with collision to drop boxes onto, its materials will be randomized.
    rep.functional.create.scope(name="Assets", parent="/SDG")
    rep.functional.create.scope(name="Materials", parent="/SDG")
    pallet_url = assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_PaletteA_01.usd"
    pallet = rep.functional.create.reference(
        usd_path=pallet_url,
        parent="/SDG/Assets",
        name="Pallet",
        semantics={"class": "pallet"},
    )
    rep.functional.physics.apply_rigid_body(pallet, with_collider=True, kinematicEnabled=True)
    pallet_materials = []
    for i in range(5):
        color = rng.generator.uniform((0.45, 0.3, 0.15), (0.95, 0.85, 0.55), size=3)
        pallet_materials.append(
            rep.functional.create.material(
                mdl="OmniPBR.mdl",
                diffuse_color_constant=tuple(float(channel) for channel in color),
                reflection_roughness_constant=float(rng.generator.uniform(0.45, 0.95)),
                metallic_constant=float(rng.generator.uniform(0.0, 0.05)),
                name=f"PalletMaterial_{i}",
                parent="/SDG/Materials",
            )
        )
    randomize_pallet(pallet, pallet_materials, rng=rng)

    # Create primitive distractors to randomly place around the scene.
    rep.functional.create.scope(name="Distractors", parent="/SDG/Assets")
    cube_distractors = rep.functional.create_batch.cube(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCube",
        semantics={"class": "distractor"},
    )
    sphere_distractors = rep.functional.create_batch.sphere(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorSphere",
        semantics={"class": "distractor"},
    )
    cylinder_distractors = rep.functional.create_batch.cylinder(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCylinder",
        semantics={"class": "distractor"},
    )
    cone_distractors = rep.functional.create_batch.cone(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCone",
        semantics={"class": "distractor"},
    )
    distractors = cube_distractors + sphere_distractors + cylinder_distractors + cone_distractors
    randomize_distractors(distractors, rng=rng)

    # Create boxes with rigid body dynamics to randomly drop onto the pallet.
    cardbox_url = assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_04.usd"
    boxes = []
    for i in range(NUM_DROP_BOXES):
        box = rep.functional.create.reference(
            usd_path=cardbox_url,
            parent="/SDG/Assets",
            name=f"Box_{i}",
            semantics={"class": "cardbox"},
        )
        # The referenced box has mesh children, so set a simple box collider on each mesh.
        for child_prim in Usd.PrimRange(box):
            if child_prim.IsA(UsdGeom.Mesh):
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(child_prim)
                mesh_collision_api.CreateApproximationAttr().Set("boundingCube")
                rep.functional.physics.apply_rigid_body(child_prim, with_collider=True, approximation="boundingCube")
        rep.functional.physics.apply_rigid_body(box)
        boxes.append(box)
    randomize_boxes(boxes, start_height=0.3, rng=rng)

    # Drop the boxes.
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    for _ in range(NUM_SIMULATION_FRAMES):
        await omni.kit.app.get_app().next_update_async()
    timeline.pause()

    # Setup SDG.
    rep.functional.create.scope(name="Cameras", parent="/SDG")
    cam = rep.functional.create.camera(
        position=(3.0, 3.0, 2.0), look_at=(0, 0, 0.4), parent="/SDG/Cameras", name="Camera"
    )
    rp = rep.create.render_product(cam, RESOLUTION, name="rp_workflow_01")
    # Disable render products by default and only enable them at capture time.
    rp.hydra_texture.set_updates_enabled(False)

    # Create a `BasicWriter` to save common annotations from the same camera view.
    backend = rep.backends.get("DiskBackend")
    out_dir = os.path.join(os.getcwd(), "_out_workflow_01")
    backend.initialize(output_dir=out_dir)
    print(f"[SDG] Output directory: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        backend=backend,
        rgb=True,
        semantic_segmentation=True,
        colorize_semantic_segmentation=True,
    )
    writer.attach(rp)

    for i in range(NUM_CAPTURES):
        print(f"[SDG] Capture {i + 1}/{NUM_CAPTURES}")

        # Run the randomizers on the scene.
        randomize_dome_light(dome_light, dome_texture_urls, rng=rng)
        randomize_distractors(distractors, rng=rng)
        randomize_pallet(pallet, pallet_materials, rng=rng)

        # Re-drop one box so each capture has a slightly different physical arrangement.
        box = boxes[int(rng.generator.integers(0, len(boxes)))]
        randomize_boxes([box], start_height=1.2, rng=rng)
        timeline.play()
        for _ in range(NUM_SIMULATION_FRAMES):
            await omni.kit.app.get_app().next_update_async()
        timeline.pause()

        # Sample a new camera position on a small orbit while looking at the pallet.
        randomize_camera(cam, pallet, rng=rng)

        # Enable rendering only for the capture step to avoid extra GPU work.
        rp.hydra_texture.set_updates_enabled(True)
        await rep.orchestrator.step_async(delta_time=0.0, rt_subframes=RT_SUBFRAMES)
        rp.hydra_texture.set_updates_enabled(False)

    # Cleanup.
    await rep.orchestrator.wait_until_complete_async()
    writer.detach()
    rp.destroy()


asyncio.ensure_future(run_workflow_async())

```
Copy to clipboard
Standalone Application

```
"""Basic SDG workflow with scene creation, asset placement, randomization, and data capture.

Boxes are randomized and simulated with physics before each capture.
"""

import math
import os
from typing import Any

from isaacsim import SimulationApp

simulation_app = SimulationApp(launch_config={"headless": False})

import carb
import carb.settings
import omni.replicator.core as rep
import omni.timeline
import omni.usd
from isaacsim.storage.native import get_assets_root_path
from pxr import Usd, UsdGeom, UsdPhysics

NUM_CAPTURES = 5
RESOLUTION = (1280, 720)
RT_SUBFRAMES = 8
NUM_DROP_BOXES = 10
NUM_SIMULATION_FRAMES = 75
NUM_PRIM_DISTRACTORS = 5
ENV_URL = "/Isaac/Environments/Grid/default_environment.usd"


def randomize_distractors(prims: list[Any], rng: Any) -> None:
    """Randomize small distractors on a loose ring around the pallet."""
    count = len(prims)
    angles = rng.generator.uniform(0.0, 2.0 * math.pi, count)
    radii = rng.generator.uniform(0.9, 1.4, count)
    heights = rng.generator.uniform(0.15, 0.45, count)
    positions = [
        (float(radius * math.cos(angle)), float(radius * math.sin(angle)), float(height))
        for angle, radius, height in zip(angles, radii, heights)
    ]
    rotations = rng.generator.uniform((0.0, 0.0, 0.0), (45.0, 45.0, 360.0), size=(count, 3)).tolist()
    scales = rng.generator.uniform(0.1, 0.2, count).tolist()
    rep.functional.modify.pose(
        prims,
        position_value=positions,
        rotation_value=rotations,
        scale_value=scales,
    )
    rep.functional.randomizer.display_color(prims, rng=rng)


def randomize_dome_light(dome_light: Any, texture_urls: list[str], rng: Any) -> None:
    """Randomize the dome light texture and intensity."""
    texture_url = texture_urls[int(rng.generator.integers(0, len(texture_urls)))]
    intensity = float(rng.generator.uniform(500.0, 900.0))
    rep.functional.modify.attribute(dome_light, "inputs:texture:file", texture_url)
    rep.functional.modify.attribute(dome_light, "inputs:intensity", intensity)


def randomize_pallet(pallet: Any, materials: list[Any], rng: Any) -> None:
    """Randomize the pallet material."""
    material = materials[int(rng.generator.integers(0, len(materials)))]
    rep.functional.modify.material(pallet, material)


def randomize_camera(camera: Any, look_at: Any, rng: Any) -> None:
    """Randomize the camera pose while keeping it aimed at the target."""
    theta = float(rng.generator.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.generator.uniform(2.6, 3.4))
    position = (
        radius * math.cos(theta),
        radius * math.sin(theta),
        float(rng.generator.uniform(1.4, 2.2)),
    )
    rep.functional.modify.pose(
        camera,
        position_value=position,
        look_at_value=look_at,
        look_at_up_axis=(0, 0, 1),
        write_to_usd=True,
    )


def randomize_boxes(boxes: list[Any], start_height: float, rng: Any) -> None:
    """Randomize box poses before dropping them onto the pallet."""
    for i, box in enumerate(boxes):
        lateral_range = 0.4
        height = start_height + 0.2 * i
        tilt_range = 15.0
        rep.functional.modify.pose(
            box,
            position_value=(
                float(rng.generator.uniform(-lateral_range, lateral_range)),
                float(rng.generator.uniform(-lateral_range, lateral_range)),
                height,
            ),
            rotation_value=(
                float(rng.generator.uniform(0.0, tilt_range)),
                float(rng.generator.uniform(0.0, tilt_range)),
                float(rng.generator.uniform(0.0, 360.0)),
            ),
            write_to_usd=True,
        )


def run_workflow() -> None:
    """Run the pallet drop SDG workflow."""
    assets_root_path = get_assets_root_path()
    if assets_root_path is None:
        carb.log_error("[SDG] Could not resolve assets root path; aborting.")
        return

    # Load stage.
    env_path = assets_root_path + ENV_URL
    omni.usd.get_context().open_stage(env_path)
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        carb.log_error(f"[SDG] Failed to open stage: '{env_path}', exiting.")
        return

    # Disable automatic capture so only explicit `step()` calls write frames.
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode to reduce low-resolution SDG rendering artifacts.
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Seed the functional randomizer so re-running the script is reproducible.
    rng = rep.rng.ReplicatorRNG(seed=42)
    timeline = omni.timeline.get_timeline_interface()

    # Create a dome light which will be randomized by texture and brightness.
    rep.functional.create.xform(name="SDG")
    rep.functional.create.scope(name="Lights", parent="/SDG")
    dome_texture_urls = [
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/autoshop_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/carpentry_shop_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Indoor/wooden_lounge_4k.hdr",
    ]
    dome_light = rep.functional.create.dome_light(
        texture=dome_texture_urls[0],
        intensity=700,
        parent="/SDG/Lights",
        name="DomeLight",
    )
    randomize_dome_light(dome_light, dome_texture_urls, rng=rng)

    # Create a pallet with collision to drop boxes onto, its materials will be randomized.
    rep.functional.create.scope(name="Assets", parent="/SDG")
    rep.functional.create.scope(name="Materials", parent="/SDG")
    pallet_url = assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_PaletteA_01.usd"
    pallet = rep.functional.create.reference(
        usd_path=pallet_url,
        parent="/SDG/Assets",
        name="Pallet",
        semantics={"class": "pallet"},
    )
    rep.functional.physics.apply_rigid_body(pallet, with_collider=True, kinematicEnabled=True)
    pallet_materials = []
    for i in range(5):
        color = rng.generator.uniform((0.45, 0.3, 0.15), (0.95, 0.85, 0.55), size=3)
        pallet_materials.append(
            rep.functional.create.material(
                mdl="OmniPBR.mdl",
                diffuse_color_constant=tuple(float(channel) for channel in color),
                reflection_roughness_constant=float(rng.generator.uniform(0.45, 0.95)),
                metallic_constant=float(rng.generator.uniform(0.0, 0.05)),
                name=f"PalletMaterial_{i}",
                parent="/SDG/Materials",
            )
        )
    randomize_pallet(pallet, pallet_materials, rng=rng)

    # Create primitive distractors to randomly place around the scene.
    rep.functional.create.scope(name="Distractors", parent="/SDG/Assets")
    cube_distractors = rep.functional.create_batch.cube(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCube",
        semantics={"class": "distractor"},
    )
    sphere_distractors = rep.functional.create_batch.sphere(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorSphere",
        semantics={"class": "distractor"},
    )
    cylinder_distractors = rep.functional.create_batch.cylinder(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCylinder",
        semantics={"class": "distractor"},
    )
    cone_distractors = rep.functional.create_batch.cone(
        count=NUM_PRIM_DISTRACTORS,
        parent="/SDG/Assets/Distractors",
        name="DistractorCone",
        semantics={"class": "distractor"},
    )
    distractors = cube_distractors + sphere_distractors + cylinder_distractors + cone_distractors
    randomize_distractors(distractors, rng=rng)

    # Create boxes with rigid body dynamics to randomly drop onto the pallet.
    cardbox_url = assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_04.usd"
    boxes = []
    for i in range(NUM_DROP_BOXES):
        box = rep.functional.create.reference(
            usd_path=cardbox_url,
            parent="/SDG/Assets",
            name=f"Box_{i}",
            semantics={"class": "cardbox"},
        )
        # The referenced box has mesh children, so set a simple box collider on each mesh.
        for child_prim in Usd.PrimRange(box):
            if child_prim.IsA(UsdGeom.Mesh):
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(child_prim)
                mesh_collision_api.CreateApproximationAttr().Set("boundingCube")
                rep.functional.physics.apply_rigid_body(child_prim, with_collider=True, approximation="boundingCube")
        rep.functional.physics.apply_rigid_body(box)
        boxes.append(box)
    randomize_boxes(boxes, start_height=0.3, rng=rng)

    # Drop the boxes.
    timeline.play()
    for _ in range(NUM_SIMULATION_FRAMES):
        simulation_app.update()
    timeline.pause()

    # Setup SDG.
    rep.functional.create.scope(name="Cameras", parent="/SDG")
    cam = rep.functional.create.camera(
        position=(3.0, 3.0, 2.0), look_at=(0, 0, 0.4), parent="/SDG/Cameras", name="Camera"
    )
    rp = rep.create.render_product(cam, RESOLUTION, name="rp_workflow_01")
    # Disable render products by default and only enable them at capture time.
    rp.hydra_texture.set_updates_enabled(False)

    # Attach a `BasicWriter` to save common annotations from the same camera view.
    backend = rep.backends.get("DiskBackend")
    out_dir = os.path.join(os.getcwd(), "_out_workflow_01")
    backend.initialize(output_dir=out_dir)
    print(f"[SDG] Output directory: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        backend=backend,
        rgb=True,
        semantic_segmentation=True,
        colorize_semantic_segmentation=True,
    )
    writer.attach(rp)

    for i in range(NUM_CAPTURES):
        print(f"[SDG] Capture {i + 1}/{NUM_CAPTURES}")

        # Run the randomizers on the scene.
        randomize_dome_light(dome_light, dome_texture_urls, rng=rng)
        randomize_distractors(distractors, rng=rng)
        randomize_pallet(pallet, pallet_materials, rng=rng)

        # Re-drop one box so each capture has a slightly different physical arrangement.
        box = boxes[int(rng.generator.integers(0, len(boxes)))]
        randomize_boxes([box], start_height=1.2, rng=rng)
        timeline.play()
        for _ in range(NUM_SIMULATION_FRAMES):
            simulation_app.update()
        timeline.pause()

        # Sample a new camera position on a small orbit while looking at the pallet.
        randomize_camera(cam, pallet, rng=rng)

        # Enable rendering only for the capture step to avoid extra GPU work.
        rp.hydra_texture.set_updates_enabled(True)
        rep.orchestrator.step(delta_time=0.0, rt_subframes=RT_SUBFRAMES)
        rp.hydra_texture.set_updates_enabled(False)

    # Cleanup.
    rep.orchestrator.wait_until_complete()
    writer.detach()
    rp.destroy()


run_workflow()


```
Copy to clipboard
Output directory `_out_workflow_01`: per captured frame, an `rgb_*.png`, a colorized `semantic_segmentation_*.png`, and a matching `*.json` label map written by the `BasicWriter`.
### Workflow 2: Collision-Checked Asset Placement[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#workflow-2-collision-checked-asset-placement "Link to this heading")
This workflow rebuilds its SDG content on a configurable cadence (`CAPTURES_PER_SCENE`). Each rebuild picks an environment, scatters pallets on the floor, builds vertical box stacks on each pallet, and orbits one camera around each pallet. It places assets with sample-time collision checks rather than rigid-body simulation, so there is no physics settling step.
[![SDG scenes rebuilt across environments with pallets and collision-checked box stacks captured from an orbiting camera](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isim_6.0_replicator_tut_external_workflow_2.webp) ](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isim_6.0_replicator_tut_external_workflow_2.webp)
The persistent objects (a dome light, one camera, one render product, and one `BasicWriter`) are created once. The per-rebuild content lives under a unique scope `/World/SDG/Scene_<n>`. The script removes the previous scope before authoring the next one. If the old scope remains on the stage, Replicator’s scatter-mesh cache reuses stale planes and asset placement fails.
Each scene rebuild does the following:
  1. Pick an environment URL from `DEFAULT_ENV_URLS`. If the entry is `None`, build a large ground plane with a collider instead.
  2. `create_pallets_on_floor` - sample a count from `PALLET_COUNT_RANGE`, scatter that many pallets on a hidden floor plane with `rep.functional.randomizer.scatter_2d` and `check_for_collisions=True`, then snap each pallet so its measured bottom rests at `z=0`.
  3. `create_stacks_on_pallet` for each pallet - sample a stack count, scatter base boxes on a hidden plane fitted to the pallet top with collision checks (retry with one fewer base if scattering cannot find a collision-free layout), then build each stack vertically by referencing the same box asset at increasing heights.
  4. For each capture in this scene, `randomize_camera` orbits the camera around the next pallet and the orchestrator step writes one frame.


The outer loop continues until `TOTAL_CAPTURES` frames have been written. The hidden scatter planes and the bounding-box queries (`compute_aabb`) place assets on surfaces without running physics.
The standalone example can also be run directly (on Windows use `python.bat` instead of `python.sh`):

```
./python.sh standalone_examples/api/isaacsim.replicator.examples/sdg_workflow_02.py

```
Copy to clipboard
Script Editor

```
"""
Generate palletized box stacks across randomized scenes.
Each scene chooses an environment, scatters pallets, builds box stacks, and captures camera views.
"""

import asyncio
import math
import os

import carb
import carb.settings
import isaacsim.core.experimental.utils.bounds as bounds_utils
import omni.kit.app
import omni.replicator.core as rep
import omni.usd
from isaacsim.storage.native import get_assets_root_path
from omni.replicator.core.scripts.functional import utils as rep_utils

DEFAULT_ENV_URLS = [
    "/Isaac/Environments/Simple_Warehouse/warehouse.usd",
    None,
]
PALLET_URL = "/Isaac/Environments/Simple_Warehouse/Props/SM_PaletteA_01.usd"
BOX_URLS = [
    "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxC_01.usd",
    "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_01.usd",
]

TOTAL_CAPTURES = 5
CAPTURES_PER_SCENE = 3
RESOLUTION = (1280, 720)
RT_SUBFRAMES = 8
PALLET_COUNT_RANGE = range(2, 6)
STACK_COUNT_RANGE = range(1, 4)
BOXES_PER_STACK_RANGE = range(1, 6)
STACK_SCATTER_AREA_SCALE = 0.9


async def create_pallets_on_floor(scene_scope_path, assets_root_path, rng):
    pallet_count = int(rng.generator.choice(PALLET_COUNT_RANGE))
    # Use a hidden floor plane as a sampling surface so scattered pallets avoid each other.
    floor_plane = rep.functional.create.plane(
        parent=scene_scope_path,
        name="PalletScatterPlane",
        position=(0.0, 0.0, 0.0),
        scale=(5.0, 5.0, 1.0),
        visible=False,
    )

    pallets = []
    for i in range(pallet_count):
        pallets.append(
            rep.functional.create.reference(
                usd_path=assets_root_path + PALLET_URL,
                parent=scene_scope_path,
                name=f"Pallet_{i}",
                position=(i * 2.0, 0.0, 1.0),
                rotation=(0.0, 0.0, float(rng.generator.choice([0.0, 90.0, 180.0, 270.0]))),
                semantics={"class": "pallet"},
            )
        )

    await omni.kit.app.get_app().next_update_async()
    rep.functional.randomizer.scatter_2d(pallets, floor_plane, check_for_collisions=True, rng=rng)
    await omni.kit.app.get_app().next_update_async()

    bbox_cache = bounds_utils.create_bbox_cache()
    for pallet in pallets:
        aabb = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
        origin = rep_utils.get_world_position(pallet)
        origin_to_bottom = float(origin[2] - aabb[2])
        # Move the pallet origin so the measured bottom sits on the floor.
        rep.functional.modify.pose(
            pallet,
            position_value=(float(origin[0]), float(origin[1]), origin_to_bottom),
            write_to_usd=True,
        )

    await omni.kit.app.get_app().next_update_async()
    return pallets


async def create_stacks_on_pallet(scene_scope_path, pallet_index, pallet, assets_root_path, rng):
    bbox_cache = bounds_utils.create_bbox_cache()
    pallet_bounds = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
    pallet_origin = rep_utils.get_world_position(pallet)
    stack_count = int(rng.generator.choice(STACK_COUNT_RANGE))
    pallet_top_z = float(pallet_bounds[5])
    pallet_center_x = float(pallet_origin[0])
    pallet_center_y = float(pallet_origin[1])
    pallet_size_x = float(pallet_bounds[3] - pallet_bounds[0])
    pallet_size_y = float(pallet_bounds[4] - pallet_bounds[1])

    base_boxes = []
    stack_data = []
    for i in range(stack_count):
        box_url = BOX_URLS[int(rng.generator.integers(0, len(BOX_URLS)))]
        box = rep.functional.create.reference(
            usd_path=assets_root_path + box_url,
            parent=scene_scope_path,
            name=f"Pallet_{pallet_index}_BoxStack_{i}_Base",
            position=(i * 2.0, 0.0, pallet_top_z + 1.0),
            semantics={"class": "cardbox"},
        )
        base_boxes.append(box)
        stack_data.append(
            {
                "box": box,
                "url": assets_root_path + box_url,
                "height_count": int(rng.generator.choice(BOXES_PER_STACK_RANGE)),
            }
        )

    await omni.kit.app.get_app().next_update_async()
    bbox_cache = bounds_utils.create_bbox_cache()
    max_box_height = 0.0
    for stack in stack_data:
        aabb = bounds_utils.compute_aabb(stack["box"], bbox_cache=bbox_cache, include_children=True)
        origin = rep_utils.get_world_position(stack["box"])
        stack["size"] = (
            float(aabb[3] - aabb[0]),
            float(aabb[4] - aabb[1]),
            float(aabb[5] - aabb[2]),
        )
        # Referenced box assets use an origin near the bottom, so keep this offset when stacking.
        stack["origin_to_bottom"] = float(origin[2] - aabb[2])
        max_box_height = max(max_box_height, stack["size"][2])

    # Scatter stack bases on a hidden plane smaller than the pallet top.
    scatter_plane = rep.functional.create.plane(
        parent=scene_scope_path,
        name=f"Pallet_{pallet_index}_StackScatterPlane",
        position=(pallet_center_x, pallet_center_y, pallet_top_z),
        scale=(pallet_size_x * STACK_SCATTER_AREA_SCALE, pallet_size_y * STACK_SCATTER_AREA_SCALE, 1.0),
        visible=False,
    )

    while True:
        try:
            rep.functional.randomizer.scatter_2d(
                base_boxes,
                scatter_plane,
                offset=max_box_height * 0.5,
                check_for_collisions=True,
                rng=rng,
            )
            break
        except ValueError:
            if len(base_boxes) <= 1:
                raise
            stack_data.pop()
            removed_box = base_boxes.pop()
            omni.usd.get_context().get_stage().RemovePrim(removed_box.GetPath())
            print(
                f"[SDG] Warning: could not scatter {len(base_boxes) + 1} stacks on pallet {pallet_index}; "
                f"retrying with {len(base_boxes)}."
            )
            await omni.kit.app.get_app().next_update_async()
    await omni.kit.app.get_app().next_update_async()

    all_boxes = list(base_boxes)
    for stack_idx, stack in enumerate(stack_data):
        _, _, box_height = stack["size"]
        origin_to_bottom = stack["origin_to_bottom"]
        origin = rep_utils.get_world_position(stack["box"])
        origin_x = float(origin[0])
        origin_y = float(origin[1])

        rep.functional.modify.pose(
            stack["box"],
            position_value=(origin_x, origin_y, pallet_top_z + origin_to_bottom),
            write_to_usd=True,
        )

        for level in range(1, stack["height_count"]):
            all_boxes.append(
                rep.functional.create.reference(
                    usd_path=stack["url"],
                    parent=scene_scope_path,
                    name=f"Pallet_{pallet_index}_BoxStack_{stack_idx}_{level}",
                    position=(origin_x, origin_y, pallet_top_z + origin_to_bottom + box_height * level),
                    semantics={"class": "cardbox"},
                )
            )

    return all_boxes


def randomize_camera(camera, pallet, rng):
    bbox_cache = bounds_utils.create_bbox_cache()
    pallet_bounds = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
    pallet_origin = rep_utils.get_world_position(pallet)
    target = (
        float(pallet_origin[0]),
        float(pallet_origin[1]),
        float(pallet_bounds[5] + 0.5),
    )
    theta = float(rng.generator.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.generator.uniform(2.4, 3.2))
    height = float(rng.generator.uniform(1.4, 2.2))
    rep.functional.modify.pose(
        camera,
        position_value=(
            target[0] + radius * math.cos(theta),
            target[1] + radius * math.sin(theta),
            target[2] + height,
        ),
        look_at_value=target,
        look_at_up_axis=(0, 0, 1),
        write_to_usd=True,
    )


async def run_workflow_async():
    # Create a clean stage for this tutorial workflow.
    assets_root_path = get_assets_root_path()
    if assets_root_path is None:
        carb.log_error("[SDG] Could not resolve assets root path; aborting.")
        return

    await omni.usd.get_context().new_stage_async()
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        carb.log_error("[SDG] Could not create a new stage; aborting.")
        return

    # Disable automatic capture so only explicit `step_async()` calls write frames.
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode to reduce low-resolution SDG rendering artifacts.
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Seed the randomizer so re-running the script produces the same scene.
    rng = rep.rng.ReplicatorRNG(seed=42)

    rep.functional.create.xform(name="World")
    rep.functional.create.xform(parent="/World", name="SDG")

    # Keep generated SDG content separate from the randomized environment.
    rep.functional.create.dome_light(intensity=500, parent="/World/SDG", name="DomeLight")

    # Use one camera and move it to each pallet before capturing.
    cam = rep.functional.create.camera(position=(3, 3, 3), look_at=(0, 0, 0), parent="/World/SDG", name="Camera")
    rp = rep.create.render_product(cam, RESOLUTION, name="rp_workflow_02")
    # Disable render products by default and only enable them at capture time.
    rp.hydra_texture.set_updates_enabled(False)

    # Create a `BasicWriter` to save RGB and colorized semantic labels.
    backend = rep.backends.get("DiskBackend")
    out_dir = os.path.join(os.getcwd(), "_out_workflow_02")
    backend.initialize(output_dir=out_dir)
    print(f"[SDG] Output directory: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        backend=backend,
        rgb=True,
        semantic_segmentation=True,
        colorize_semantic_segmentation=True,
    )
    writer.attach(rp)

    environment_scope_path = "/World/Environment"
    capture_count = 0
    randomization_count = 0
    prev_scene_scope_path = None

    while capture_count < TOTAL_CAPTURES:
        randomization_count += 1
        print(f"[SDG] Randomization {randomization_count}")

        # Use a unique scene scope per randomization so Replicator's scatter mesh cache stays fresh.
        scene_scope_name = f"Scene_{randomization_count}"
        scene_scope_path = f"/World/SDG/{scene_scope_name}"

        if stage.GetPrimAtPath(environment_scope_path).IsValid():
            stage.RemovePrim(environment_scope_path)
        if prev_scene_scope_path is not None and stage.GetPrimAtPath(prev_scene_scope_path).IsValid():
            stage.RemovePrim(prev_scene_scope_path)
        await omni.kit.app.get_app().next_update_async()

        rep.functional.create.scope(name="Environment", parent="/World")
        # Pick an environment; None means use a generated ground plane.
        env_url = DEFAULT_ENV_URLS[int(rng.generator.integers(0, len(DEFAULT_ENV_URLS)))]
        if env_url is None:
            ground = rep.functional.create.plane(
                parent=environment_scope_path,
                name="GroundPlane",
                scale=(100, 100, 1),
            )
            rep.functional.physics.apply_collider(ground)
        else:
            rep.functional.create.reference(
                usd_path=assets_root_path + env_url,
                parent=environment_scope_path,
                name="Scene",
            )

        rep.functional.create.scope(name=scene_scope_name, parent="/World/SDG")
        prev_scene_scope_path = scene_scope_path

        # Choose the pallet count, scatter them, shuffle the order, then build stacks.
        pallets = await create_pallets_on_floor(scene_scope_path, assets_root_path, rng)
        pallet_order = list(range(len(pallets)))
        rng.generator.shuffle(pallet_order)
        pallets = [pallets[i] for i in pallet_order]
        for pallet_idx, pallet in enumerate(pallets):
            await create_stacks_on_pallet(scene_scope_path, pallet_idx, pallet, assets_root_path, rng)

        captures_this_scene = min(CAPTURES_PER_SCENE, TOTAL_CAPTURES - capture_count)
        for capture_idx in range(captures_this_scene):
            pallet = pallets[capture_idx % len(pallets)]
            randomize_camera(cam, pallet, rng)

            capture_count += 1
            print(f"[SDG] Capture {capture_count}/{TOTAL_CAPTURES}")
            rp.hydra_texture.set_updates_enabled(True)
            await rep.orchestrator.step_async(rt_subframes=RT_SUBFRAMES)
            rp.hydra_texture.set_updates_enabled(False)

    # Cleanup.
    await rep.orchestrator.wait_until_complete_async()
    writer.detach()
    rp.destroy()


asyncio.ensure_future(run_workflow_async())

```
Copy to clipboard
Standalone Application

```
"""Generate palletized box stacks across randomized scenes.

Each scene chooses an environment, scatters pallets, builds box stacks, and captures camera views.
"""

import math
import os
from typing import Any

from isaacsim import SimulationApp

simulation_app = SimulationApp(launch_config={"headless": False})

import carb
import carb.settings
import isaacsim.core.experimental.utils.bounds as bounds_utils
import omni.replicator.core as rep
import omni.usd
from isaacsim.storage.native import get_assets_root_path
from omni.replicator.core.scripts.functional import utils as rep_utils

DEFAULT_ENV_URLS = [
    "/Isaac/Environments/Simple_Warehouse/warehouse.usd",
    None,
]
PALLET_URL = "/Isaac/Environments/Simple_Warehouse/Props/SM_PaletteA_01.usd"
BOX_URLS = [
    "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxC_01.usd",
    "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_01.usd",
]

TOTAL_CAPTURES = 5
CAPTURES_PER_SCENE = 3
RESOLUTION = (1280, 720)
RT_SUBFRAMES = 8
PALLET_COUNT_RANGE = range(2, 6)
STACK_COUNT_RANGE = range(1, 4)
BOXES_PER_STACK_RANGE = range(1, 6)
STACK_SCATTER_AREA_SCALE = 0.9


def create_pallets_on_floor(scene_scope_path: str, assets_root_path: str, rng: Any) -> list[Any]:
    """Create and scatter pallets on a hidden floor plane."""
    pallet_count = int(rng.generator.choice(PALLET_COUNT_RANGE))
    # Use a hidden floor plane as a sampling surface so scattered pallets avoid each other.
    floor_plane = rep.functional.create.plane(
        parent=scene_scope_path,
        name="PalletScatterPlane",
        position=(0.0, 0.0, 0.0),
        scale=(5.0, 5.0, 1.0),
        visible=False,
    )

    pallets = []
    for i in range(pallet_count):
        pallets.append(
            rep.functional.create.reference(
                usd_path=assets_root_path + PALLET_URL,
                parent=scene_scope_path,
                name=f"Pallet_{i}",
                position=(i * 2.0, 0.0, 1.0),
                rotation=(0.0, 0.0, float(rng.generator.choice([0.0, 90.0, 180.0, 270.0]))),
                semantics={"class": "pallet"},
            )
        )

    simulation_app.update()
    rep.functional.randomizer.scatter_2d(pallets, floor_plane, check_for_collisions=True, rng=rng)
    simulation_app.update()

    bbox_cache = bounds_utils.create_bbox_cache()
    for pallet in pallets:
        aabb = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
        origin = rep_utils.get_world_position(pallet)
        origin_to_bottom = float(origin[2] - aabb[2])
        # Move the pallet origin so the measured bottom sits on the floor.
        rep.functional.modify.pose(
            pallet,
            position_value=(float(origin[0]), float(origin[1]), origin_to_bottom),
            write_to_usd=True,
        )

    simulation_app.update()
    return pallets


def create_stacks_on_pallet(
    scene_scope_path: str, pallet_index: int, pallet: Any, assets_root_path: str, rng: Any
) -> list[Any]:
    """Create randomized box stacks on a pallet."""
    bbox_cache = bounds_utils.create_bbox_cache()
    pallet_bounds = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
    pallet_origin = rep_utils.get_world_position(pallet)
    stack_count = int(rng.generator.choice(STACK_COUNT_RANGE))
    pallet_top_z = float(pallet_bounds[5])
    pallet_center_x = float(pallet_origin[0])
    pallet_center_y = float(pallet_origin[1])
    pallet_size_x = float(pallet_bounds[3] - pallet_bounds[0])
    pallet_size_y = float(pallet_bounds[4] - pallet_bounds[1])

    base_boxes = []
    stack_data = []
    for i in range(stack_count):
        box_url = BOX_URLS[int(rng.generator.integers(0, len(BOX_URLS)))]
        box = rep.functional.create.reference(
            usd_path=assets_root_path + box_url,
            parent=scene_scope_path,
            name=f"Pallet_{pallet_index}_BoxStack_{i}_Base",
            position=(i * 2.0, 0.0, pallet_top_z + 1.0),
            semantics={"class": "cardbox"},
        )
        base_boxes.append(box)
        stack_data.append(
            {
                "box": box,
                "url": assets_root_path + box_url,
                "height_count": int(rng.generator.choice(BOXES_PER_STACK_RANGE)),
            }
        )

    simulation_app.update()
    bbox_cache = bounds_utils.create_bbox_cache()
    max_box_height = 0.0
    for stack in stack_data:
        aabb = bounds_utils.compute_aabb(stack["box"], bbox_cache=bbox_cache, include_children=True)
        origin = rep_utils.get_world_position(stack["box"])
        stack["size"] = (
            float(aabb[3] - aabb[0]),
            float(aabb[4] - aabb[1]),
            float(aabb[5] - aabb[2]),
        )
        # Referenced box assets use an origin near the bottom, so keep this offset when stacking.
        stack["origin_to_bottom"] = float(origin[2] - aabb[2])
        max_box_height = max(max_box_height, stack["size"][2])

    # Scatter stack bases on a hidden plane smaller than the pallet top.
    scatter_plane = rep.functional.create.plane(
        parent=scene_scope_path,
        name=f"Pallet_{pallet_index}_StackScatterPlane",
        position=(pallet_center_x, pallet_center_y, pallet_top_z),
        scale=(pallet_size_x * STACK_SCATTER_AREA_SCALE, pallet_size_y * STACK_SCATTER_AREA_SCALE, 1.0),
        visible=False,
    )

    while True:
        try:
            rep.functional.randomizer.scatter_2d(
                base_boxes,
                scatter_plane,
                offset=max_box_height * 0.5,
                check_for_collisions=True,
                rng=rng,
            )
            break
        except ValueError:
            if len(base_boxes) <= 1:
                raise
            stack_data.pop()
            removed_box = base_boxes.pop()
            omni.usd.get_context().get_stage().RemovePrim(removed_box.GetPath())
            print(
                f"[SDG] Warning: could not scatter {len(base_boxes) + 1} stacks on pallet {pallet_index}; "
                f"retrying with {len(base_boxes)}."
            )
            simulation_app.update()
    simulation_app.update()

    all_boxes = list(base_boxes)
    for stack_idx, stack in enumerate(stack_data):
        _, _, box_height = stack["size"]
        origin_to_bottom = stack["origin_to_bottom"]
        origin = rep_utils.get_world_position(stack["box"])
        origin_x = float(origin[0])
        origin_y = float(origin[1])

        rep.functional.modify.pose(
            stack["box"],
            position_value=(origin_x, origin_y, pallet_top_z + origin_to_bottom),
            write_to_usd=True,
        )

        for level in range(1, stack["height_count"]):
            all_boxes.append(
                rep.functional.create.reference(
                    usd_path=stack["url"],
                    parent=scene_scope_path,
                    name=f"Pallet_{pallet_index}_BoxStack_{stack_idx}_{level}",
                    position=(origin_x, origin_y, pallet_top_z + origin_to_bottom + box_height * level),
                    semantics={"class": "cardbox"},
                )
            )

    return all_boxes


def randomize_camera(camera: Any, pallet: Any, rng: Any) -> None:
    """Randomize a camera pose around the selected pallet."""
    bbox_cache = bounds_utils.create_bbox_cache()
    pallet_bounds = bounds_utils.compute_aabb(pallet, bbox_cache=bbox_cache, include_children=True)
    pallet_origin = rep_utils.get_world_position(pallet)
    target = (
        float(pallet_origin[0]),
        float(pallet_origin[1]),
        float(pallet_bounds[5] + 0.5),
    )
    theta = float(rng.generator.uniform(0.0, 2.0 * math.pi))
    radius = float(rng.generator.uniform(2.4, 3.2))
    height = float(rng.generator.uniform(1.4, 2.2))
    rep.functional.modify.pose(
        camera,
        position_value=(
            target[0] + radius * math.cos(theta),
            target[1] + radius * math.sin(theta),
            target[2] + height,
        ),
        look_at_value=target,
        look_at_up_axis=(0, 0, 1),
        write_to_usd=True,
    )


def run_workflow() -> None:
    """Run the multi-scene pallet stack SDG workflow."""
    assets_root_path = get_assets_root_path()
    if assets_root_path is None:
        carb.log_error("[SDG] Could not resolve assets root path; aborting.")
        return

    # Create a clean stage for this tutorial workflow.
    omni.usd.get_context().new_stage()
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        carb.log_error("[SDG] Could not create a new stage; aborting.")
        return

    # Disable automatic capture so only explicit `step()` calls write frames.
    rep.orchestrator.set_capture_on_play(False)

    # Set DLSS to Quality mode to reduce low-resolution SDG rendering artifacts.
    carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

    # Seed the randomizer so re-running the script produces the same scene.
    rng = rep.rng.ReplicatorRNG(seed=42)

    rep.functional.create.xform(name="World")
    rep.functional.create.xform(parent="/World", name="SDG")

    # Keep generated SDG content separate from the randomized environment.
    rep.functional.create.dome_light(intensity=500, parent="/World/SDG", name="DomeLight")

    # Use one camera and move it to each pallet before capturing.
    cam = rep.functional.create.camera(position=(3, 3, 3), look_at=(0, 0, 0), parent="/World/SDG", name="Camera")
    rp = rep.create.render_product(cam, RESOLUTION, name="rp_workflow_02")
    rp.hydra_texture.set_updates_enabled(False)

    # Attach a `BasicWriter` to save RGB and colorized semantic labels.
    backend = rep.backends.get("DiskBackend")
    out_dir = os.path.join(os.getcwd(), "_out_workflow_02")
    backend.initialize(output_dir=out_dir)
    print(f"[SDG] Output directory: {out_dir}")
    writer = rep.writers.get("BasicWriter")
    writer.initialize(
        backend=backend,
        rgb=True,
        semantic_segmentation=True,
        colorize_semantic_segmentation=True,
    )
    writer.attach(rp)

    environment_scope_path = "/World/Environment"
    capture_count = 0
    randomization_count = 0
    prev_scene_scope_path = None

    while capture_count < TOTAL_CAPTURES:
        randomization_count += 1
        print(f"[SDG] Randomization {randomization_count}")

        # Use a unique scene scope per randomization so Replicator's scatter mesh cache stays fresh.
        scene_scope_name = f"Scene_{randomization_count}"
        scene_scope_path = f"/World/SDG/{scene_scope_name}"

        if stage.GetPrimAtPath(environment_scope_path).IsValid():
            stage.RemovePrim(environment_scope_path)
        if prev_scene_scope_path is not None and stage.GetPrimAtPath(prev_scene_scope_path).IsValid():
            stage.RemovePrim(prev_scene_scope_path)
        simulation_app.update()

        rep.functional.create.scope(name="Environment", parent="/World")
        # Pick an environment; None means use a generated ground plane.
        env_url = DEFAULT_ENV_URLS[int(rng.generator.integers(0, len(DEFAULT_ENV_URLS)))]
        if env_url is None:
            ground = rep.functional.create.plane(
                parent=environment_scope_path,
                name="GroundPlane",
                scale=(100, 100, 1),
            )
            rep.functional.physics.apply_collider(ground)
        else:
            rep.functional.create.reference(
                usd_path=assets_root_path + env_url,
                parent=environment_scope_path,
                name="Scene",
            )

        rep.functional.create.scope(name=scene_scope_name, parent="/World/SDG")
        prev_scene_scope_path = scene_scope_path

        # Choose the pallet count, scatter them, shuffle the order, then build stacks.
        pallets = create_pallets_on_floor(scene_scope_path, assets_root_path, rng)
        pallet_order = list(range(len(pallets)))
        rng.generator.shuffle(pallet_order)
        pallets = [pallets[i] for i in pallet_order]
        for pallet_idx, pallet in enumerate(pallets):
            create_stacks_on_pallet(scene_scope_path, pallet_idx, pallet, assets_root_path, rng)

        captures_this_scene = min(CAPTURES_PER_SCENE, TOTAL_CAPTURES - capture_count)
        for capture_idx in range(captures_this_scene):
            pallet = pallets[capture_idx % len(pallets)]
            randomize_camera(cam, pallet, rng)

            capture_count += 1
            print(f"[SDG] Capture {capture_count}/{TOTAL_CAPTURES}")
            rp.hydra_texture.set_updates_enabled(True)
            rep.orchestrator.step(rt_subframes=RT_SUBFRAMES)
            rp.hydra_texture.set_updates_enabled(False)

    # Cleanup.
    rep.orchestrator.wait_until_complete()
    writer.detach()
    rp.destroy()


run_workflow()


```
Copy to clipboard
Output directory `_out_workflow_02`: per captured frame, an `rgb_*.png`, a colorized `semantic_segmentation_*.png`, and a matching `*.json` label map.
## Troubleshooting[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#troubleshooting "Link to this heading")
See [Replicator Troubleshooting](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#isaac-sim-replicator-troubleshooting) for the full list.
  * **Ghosting or artifacts in early captures.** Increase `rt_subframes` (see [above](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#isaac-sim-app-tutorial-replicator-sdg-workflows-rt-subframes)).
  * **Frames missing from the writer.** `wait_until_complete` was not called before exit.
  * **Scattered assets overlap or land in the wrong place after a rebuild (Workflow 2).** The previous scene scope was not removed before authoring the new one, so Replicator’s scatter-mesh cache reused stale planes.
  * **Slow runs even though few frames are written.** The render product was left enabled during physics, scene construction, or randomization. Disable it and re-enable only around the orchestrator step.


## See Also[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_sdg_workflows.html#see-also "Link to this heading")
  * [Getting Started Scripts](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_getting_started.html#isaac-sim-app-tutorial-replicator-getting-started) - smaller, single-concept scripts that introduce the same settings in isolation.
  * [Scene Based SDG](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_scene_based_sdg.html#isaac-sim-app-tutorial-replicator-scene-based-sdg) - large-scale configurable dataset generation.
  * [Object Based SDG](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_object_based_sdg.html#isaac-sim-app-tutorial-replicator-object-based-sdg) - physics-heavy object drops with multiple cameras.
  * [Writer examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html "\(in Omniverse Extensions\)") and [custom writer guide](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html "\(in Omniverse Extensions\)") - write a different output format.
  * [Annotators](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html "\(in Omniverse Extensions\)") - the full set of data sources available to writers.
  * [I/O Optimization Guide](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html "\(in Omniverse Extensions\)") - scaling to large datasets.
  * [Performance Optimization Handbook](https://docs.isaacsim.omniverse.nvidia.com/latest/reference_material/sim_performance_optimization_handbook.html#isaac-sim-performance-optimization-handbook) - full set of `rtx/post/dlss/execMode` values and other render settings.
  * [Replicator Troubleshooting](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/troubleshooting.html#isaac-sim-replicator-troubleshooting).


