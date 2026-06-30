---
source: https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html
---

# Randomization in Simulation – AMR Navigation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html#randomization-in-simulation-amr-navigation "Link to this heading")
Example of using Isaac Sim and Replicator to capture synthetic data from simulated environments (AMR Navigation).
## Learning Objectives[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html#learning-objectives "Link to this heading")
The goal of this tutorial is to demonstrate how to setup an Isaac Sim simulation scenario together with the [omni.replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html "\(in Omniverse Extensions\)") extension to capture synthetic data using diverse randomization techniques.
In this tutorial you:
  * Implement scene randomizations using USD / Isaac Sim APIs:
>     * Randomize poses of assets in the scene
>     * Switch between different background environments
  * Collect synthetic data at specific simulation events with Replicator
  * Create and destroy render products on the fly to improve runtime performance
  * Create and destroy Replicator capture graphs within the same simulation instance


### Prerequisites[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html#prerequisites "Link to this heading")
  * Familiarity with USD / Isaac Sim APIs for scene creation and manipulation.
  * Familiarity with [omni.replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html "\(in Omniverse Extensions\)") and its [writers](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html "\(in Omniverse Extensions\)").
  * Basic understanding of [OmniGraph](https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html "\(in Omniverse Extensions\)") for the navigation implementation.
  * Running simulations as [Standalone Applications](https://docs.isaacsim.omniverse.nvidia.com/latest/introduction/workflows.html#standalone-application) or via the [Script Editor](https://docs.isaacsim.omniverse.nvidia.com/latest/development_tools/omniverse_script_editor.html#script-editor).


## Scenario[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html#scenario "Link to this heading")
This tutorial uses the Nova Carter robot equipped with an [OmniGraph](https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html "\(in Omniverse Extensions\)") navigation stack, notably without collision avoidance features. The navigation stack constantly drives the robot towards a designated Xform target (`<..>/targetXform`), positioned at the location of the randomized objects of interest. As the robot comes in the proximity of the object of interest, a synthetic data generation (SDG) pipeline is triggered to capture data from its two main camera sensors. After the data is captured the objects of interest are re-randomized and the simulation continues. After a certain number of frames (`env_interval`) the background environment is changed as well. After `num_frames` the application terminates.
The `use_temp_rp` flag is used to provide an option to use temporary render products to improve the runtime performance. This speeds up the simulation by only using the render products when capturing the data, thus avoiding the overhead of rendering the sensor views when not capturing data.
[![../_images/isaac_tutorial_replicator_amr_0.gif](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_0.gif) ](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_0.gif) [![../_images/isaac_tutorial_replicator_amr_2.gif](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_2.gif) ](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_2.gif) [![../_images/isaac_tutorial_replicator_amr_1.gif](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_1.gif) ](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_1.gif)
The scenario uses the left and right camera sensors of Nova Carter (`<..>/stereo_cam_<left/right>_sensor_frame/camera_sensor_<left/right>`) to collect **LdrColor** (rgb) [annotator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html "\(in Omniverse Extensions\)") data using Replicator. By default, the data is written to `<working_dir>/_out_nav_sdg_demo` and runs for `num_frames=9` iterations.
Furthermore, it changes the background environment every `env_interval=3` captured frames. By default the tutorial cycles through `DEFAULT_ENV_URLS`; an entry of `None` creates a generic environment under `/Environment` using a Replicator dome light and a collider-enabled plane instead of loading a USD environment. The `use_temp_rp` flag can be used to optimize performance by disabling the sensor render products during simulation and temporarily enabling them during data capture.
The following image provides an illustration of the resulting data from the various environments.
![../_images/isaac_tutorial_replicator_amr_data.png](https://docs.isaacsim.omniverse.nvidia.com/latest/_images/isaac_tutorial_replicator_amr_data.png)
## Implementation[#](https://docs.isaacsim.omniverse.nvidia.com/latest/replicator_tutorials/tutorial_replicator_amr_navigation.html#implementation "Link to this heading")
The following section provides an overview and explanation of the implementation and examples on how to run the demo.
Standalone Application
To run the example as a standalone application, use the following command to execute the provided script. The script also accepts several optional arguments to customize its behavior (on Windows use `python.bat` instead of `python.sh`):

```
./python.sh standalone_examples/replicator/amr_navigation.py

```
Copy to clipboard
Arguments include:
  * `--use_temp_rp` flag to use temporary render products (default: False)
  * `--num_frames` the number of frames to be captured (default: 9)
  * `--env_interval` the capture interval at which the background environment is changed (default: 3)
  * `--env_urls` replaces `DEFAULT_ENV_URLS` entirely. Use `None` for the generic environment


For example, to run the application with all the arguments:

```
./python.sh standalone_examples/replicator/amr_navigation.py --use_temp_rp --num_frames 9 --env_interval 3

```
Copy to clipboard
Standalone Script

```
"""Generate synthetic data from an AMR navigating to random locations."""

from isaacsim import SimulationApp

simulation_app = SimulationApp(launch_config={"headless": False})

import argparse
import builtins
import os
import random
from itertools import cycle

import carb.eventdispatcher
import carb.settings
import omni.client
import omni.replicator.core as rep
import omni.timeline
import omni.usd
import omni.usd.commands
from isaacsim.core.utils.stage import create_new_stage
from isaacsim.storage.native import get_assets_root_path
from pxr import Gf, UsdGeom

DEFAULT_ENV_URLS = [
    "/Isaac/Environments/Grid/default_environment.usd",
    "/Isaac/Environments/Simple_Warehouse/warehouse.usd",
    "/Isaac/Environments/Grid/gridroom_black.usd",
    None,
]


def _parse_env_url_arg(env_url: str) -> str | None:
    """Parse CLI environment arguments, where None/null selects the generic environment."""
    return None if env_url.lower() in {"none", "null"} else env_url


parser = argparse.ArgumentParser()
parser.add_argument("--num_frames", type=int, default=9, help="The number of frames to capture")
parser.add_argument("--env_interval", type=int, default=3, help="Interval at which to change the environments")
parser.add_argument(
    "--env_urls",
    nargs="+",
    type=_parse_env_url_arg,
    default=None,
    help="Replace DEFAULT_ENV_URLS entirely. Use None for the generic environment.",
)
parser.add_argument("--use_temp_rp", action="store_true", help="Create and destroy render products for each SDG frame")
args, unknown = parser.parse_known_args()


class NavSDGDemo:
    """Demonstration of synthetic data generation using an AMR navigating towards a target."""

    CARTER_URL = "/Isaac/Samples/Replicator/OmniGraph/nova_carter_nav_only.usd"
    DOLLY_URL = "/Isaac/Props/Dolly/dolly.usd"
    PROPS_URL = "/Isaac/Props/YCB/Axis_Aligned_Physics"
    LEFT_CAMERA_REL_PATH = "sensors/front_hawk/left/camera_left"
    RIGHT_CAMERA_REL_PATH = "sensors/front_hawk/right/camera_right"
    ENVIRONMENT_SCOPE_PATH = "/Environment"

    def __init__(self) -> None:
        """Initialize the navigation SDG demo with default values."""
        self._carter_chassis = None
        self._carter_nav_target = None
        self._dolly = None
        self._dolly_light = None
        self._props = []
        self._cycled_env_urls = None
        self._env_interval = 1
        self._timeline = None
        self._timeline_sub = None
        self._stage_event_sub = None
        self._stage = None
        self._trigger_distance = 2.0
        self._num_frames = 0
        self._frame_counter = 0
        self._writer = None
        self._out_dir = None
        self._render_products = []
        self._use_temp_rp = False
        self._in_running_state = False

    def start(
        self,
        num_frames: int = 10,
        out_dir: str | None = None,
        env_urls: list[str | None] | None = None,
        env_interval: int = 3,
        use_temp_rp: bool = False,
        seed: int | None = None,
    ) -> None:
        """Start the SDG demo with the given configuration."""
        print(f"[SDG] Starting")
        if seed is not None:
            rep.set_global_seed(seed)
            random.seed(seed)
        selected_env_urls = env_urls if env_urls is not None else DEFAULT_ENV_URLS
        self._num_frames = num_frames
        self._out_dir = out_dir if out_dir is not None else os.path.join(os.getcwd(), "_out_nav_sdg_demo")
        self._cycled_env_urls = cycle(selected_env_urls)
        self._env_interval = env_interval
        self._use_temp_rp = use_temp_rp
        self._frame_counter = 0
        self._trigger_distance = 2.0
        self._load_env()
        self._randomize_dolly_pose()
        self._randomize_dolly_light()
        self._randomize_prop_poses()
        self._setup_sdg()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline.play()
        self._timeline_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
            on_event=self._on_timeline_event,
            observer_name="amr_navigation.NavSDGDemo._on_timeline_event",
        )
        self._stage_event_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.CLOSING),
            on_event=self._on_stage_closing_event,
            observer_name="amr_navigation.NavSDGDemo._on_stage_closing_event",
        )
        self._in_running_state = True

    def clear(self) -> None:
        """Reset all state variables and unsubscribe from events."""
        self._cycled_env_urls = None
        self._carter_chassis = None
        self._carter_nav_target = None
        self._dolly = None
        self._dolly_light = None
        self._timeline = None
        self._frame_counter = 0
        self._stage_event_sub = None
        self._timeline_sub = None
        self._clear_sdg_render_products()
        self._stage = None
        self._in_running_state = False

    def is_running(self) -> bool:
        """Return whether the SDG demo is currently running."""
        return self._in_running_state

    def _is_running_in_script_editor(self) -> bool:
        """Return whether the script is running in the Isaac Sim script editor."""
        return builtins.ISAAC_LAUNCHED_FROM_TERMINAL is True

    def _on_stage_closing_event(self, e: carb.eventdispatcher.Event) -> None:
        """Handle stage closing event by clearing state."""
        self.clear()

    def _load_env(self) -> None:
        """Create a new stage and load environment, robot, dolly, light, and props."""
        create_new_stage()
        self._stage = omni.usd.get_context().get_stage()
        assets_root_path = get_assets_root_path()
        rep.functional.physics.create_physics_scene(
            "/PhysicsScene", enableCCD=True, broadphaseType="MBP", enableGPUDynamics=False
        )

        # Environment
        self._load_environment(next(self._cycled_env_urls))

        # Nova Carter
        rep.functional.create.scope(name="NavWorld")
        carter = rep.functional.create.reference(
            position=(0, 0, 0),
            rotation=(0, 0, 0),
            usd_path=assets_root_path + self.CARTER_URL,
            parent="/NavWorld",
            name="CarterNav",
        )

        # Iterate children until targetXform (for navigation target) and chassis_link (for current location) are found
        for child in carter.GetChildren():
            if child.GetName() == "targetXform":
                self._carter_nav_target = child
                break
        for child in carter.GetChildren():
            if child.GetName() == "chassis_link":
                self._carter_chassis = child
                break

        # Dolly
        self._dolly = rep.functional.create.reference(
            position=(0, 0, 0),
            rotation=(0, 0, 0),
            usd_path=assets_root_path + self.DOLLY_URL,
            parent="/NavWorld",
            name="Dolly",
        )

        # # Add colliders to the dolly and its geometry primitives
        for desc_prim in self._dolly.GetChildren():
            if desc_prim.IsA(UsdGeom.Gprim):
                rep.functional.physics.apply_rigid_body(desc_prim)

        # Light
        self._dolly_light = rep.functional.create.sphere_light(
            position=(0, 0, 0),
            intensity=250000,
            radius=0.3,
            color=(1.0, 1.0, 1.0),
            parent="/NavWorld",
            name="DollyLight",
        )

        # Props
        props_urls = []
        props_folder_path = assets_root_path + self.PROPS_URL
        result, entries = omni.client.list(props_folder_path)
        if result != omni.client.Result.OK:
            carb.log_error(f"Could not list assets in path: {props_folder_path}")
            return
        for entry in entries:
            _, ext = os.path.splitext(entry.relative_path)
            if ext == ".usd":
                props_urls.append(f"{props_folder_path}/{entry.relative_path}")

        cycled_props_url = cycle(props_urls)
        for i in range(15):
            prop_url = next(cycled_props_url)
            prop_name = os.path.splitext(os.path.basename(prop_url))[0]
            path = f"/NavWorld/Props/Prop_{prop_name}_{i}"
            prim = self._stage.DefinePrim(path, "Xform")
            prim.GetReferences().AddReference(prop_url)
            self._props.append(prim)

    def _randomize_dolly_pose(self) -> None:
        """Set random dolly position ensuring minimum distance from Carter."""
        min_dist_from_carter = 4
        carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
        for _ in range(100):
            x, y = random.uniform(-6, 6), random.uniform(-6, 6)
            dist = (Gf.Vec2f(x, y) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
            if dist > min_dist_from_carter:
                self._dolly.GetAttribute("xformOp:translate").Set((x, y, 0))
                self._carter_nav_target.GetAttribute("xformOp:translate").Set((x, y, 0))
                break
        self._dolly.GetAttribute("xformOp:rotateXYZ").Set((0, 0, random.uniform(-180, 180)))

    def _randomize_dolly_light(self) -> None:
        """Position light above dolly with random color."""
        dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        self._dolly_light.GetAttribute("xformOp:translate").Set(dolly_loc + (0, 0, 3))
        self._dolly_light.GetAttribute("inputs:color").Set(
            (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
        )

    def _randomize_prop_poses(self) -> None:
        """Stack props above the dolly with random horizontal offsets."""
        spawn_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        spawn_loc[2] = spawn_loc[2] + 0.5
        for prop in self._props:
            prop.GetAttribute("xformOp:translate").Set(spawn_loc + (random.uniform(-1, 1), random.uniform(-1, 1), 0))
            spawn_loc[2] = spawn_loc[2] + 0.2

    def _setup_sdg(self) -> None:
        """Configure SDG settings, camera parameters, writer, and render products."""
        rep.orchestrator.set_capture_on_play(False)

        # Set DLSS to Quality mode (2) for best SDG results , options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
        carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

        # fStop=0 for well-lit sharp images; tickRate=0 forces autotrigger so the sensor
        # cameras stay in sync with rep.orchestrator.step_async under multi-tick rendering.
        for rel_path in (self.LEFT_CAMERA_REL_PATH, self.RIGHT_CAMERA_REL_PATH):
            camera_prim = self._stage.GetPrimAtPath(self._carter_chassis.GetPath().AppendPath(rel_path))
            camera_prim.GetAttribute("fStop").Set(0.0)
            if camera_prim.HasAttribute("omni:sensor:tickRate"):
                camera_prim.GetAttribute("omni:sensor:tickRate").Set(0.0)

        backend = rep.backends.get("DiskBackend")
        backend.initialize(output_dir=self._out_dir)
        print(f"[SDG] Writing data to: {self._out_dir}")
        self._writer = rep.writers.get("BasicWriter")
        self._writer.initialize(backend=backend, rgb=True)
        self._setup_sdg_render_products()

    def _setup_sdg_render_products(self) -> None:
        """Create and attach render products for left and right cameras."""
        print(f"[SDG] Creating SDG render products")
        left_camera_path = self._carter_chassis.GetPath().AppendPath(self.LEFT_CAMERA_REL_PATH)
        rp_left = rep.create.render_product(
            str(left_camera_path),
            (1024, 1024),
            name="left_sensor",
            force_new=True,
        )
        right_camera_path = self._carter_chassis.GetPath().AppendPath(self.RIGHT_CAMERA_REL_PATH)
        rp_right = rep.create.render_product(
            str(right_camera_path),
            (1024, 1024),
            name="right_sensor",
            force_new=True,
        )
        self._render_products = [rp_left, rp_right]
        # For better performance the render products can be disabled when not in use, and re-enabled only during SDG
        if self._use_temp_rp:
            self._disable_render_products()
        self._writer.attach(self._render_products)

    def _clear_sdg_render_products(self) -> None:
        """Detach writer and destroy all render products."""
        print(f"[SDG] Clearing SDG render products")
        if self._writer:
            self._writer.detach()
        for rp in self._render_products:
            rp.destroy()
        self._render_products.clear()
        if self._stage.GetPrimAtPath("/Replicator"):
            omni.kit.commands.execute("DeletePrimsCommand", paths=["/Replicator"])

    def _enable_render_products(self) -> None:
        """Enable texture updates on all render products."""
        print(f"[SDG] Enabling render products for SDG..")
        for rp in self._render_products:
            rp.hydra_texture.set_updates_enabled(True)

    def _disable_render_products(self) -> None:
        """Disable texture updates on all render products."""
        print(f"[SDG] Disabling render products (enabled only during SDG)..")
        for rp in self._render_products:
            rp.hydra_texture.set_updates_enabled(False)

    def _run_sdg(self) -> None:
        """Execute one SDG capture step synchronously."""
        if self._use_temp_rp:
            self._enable_render_products()
        rep.orchestrator.step(rt_subframes=16)
        if self._use_temp_rp:
            self._disable_render_products()

    async def _run_sdg_async(self) -> None:
        """Execute one SDG capture step asynchronously."""
        if self._use_temp_rp:
            self._enable_render_products()
        await rep.orchestrator.step_async(rt_subframes=16)
        if self._use_temp_rp:
            self._disable_render_products()

    def _load_next_env(self) -> None:
        """Replace current environment with the next one from the cycle."""
        self._load_environment(next(self._cycled_env_urls))

    def _load_environment(self, env_url: str | None) -> None:
        """Load the next environment under a shared scope."""
        if self._stage.GetPrimAtPath(self.ENVIRONMENT_SCOPE_PATH):
            omni.kit.commands.execute("DeletePrimsCommand", paths=[self.ENVIRONMENT_SCOPE_PATH])

        rep.functional.create.scope(name="Environment")
        if env_url:
            assets_root_path = get_assets_root_path()
            rep.functional.create.reference(
                usd_path=assets_root_path + env_url, parent=self.ENVIRONMENT_SCOPE_PATH, name="Scene"
            )
            return

        rep.functional.create.dome_light(intensity=500, parent=self.ENVIRONMENT_SCOPE_PATH, name="DomeLight")
        ground = rep.functional.create.plane(
            parent=self.ENVIRONMENT_SCOPE_PATH, name="GroundPlane", scale=(100, 100, 1)
        )
        rep.functional.physics.apply_collider(ground)

    def _on_sdg_done(self, task: object) -> None:
        """Callback invoked when async SDG step completes."""
        self._setup_next_frame()

    def _setup_next_frame(self) -> None:
        """Prepare scene for next frame or finish if all frames captured."""
        self._frame_counter += 1
        if self._frame_counter >= self._num_frames:
            print(f"[SDG] Finished")
            # Make sure the data has been written to disk before clearing the state
            if self._is_running_in_script_editor():
                import asyncio

                task = asyncio.ensure_future(rep.orchestrator.wait_until_complete_async())
                task.add_done_callback(lambda t: self.clear())
            else:
                rep.orchestrator.wait_until_complete()
                self.clear()
            return

        self._randomize_dolly_pose()
        self._randomize_dolly_light()
        self._randomize_prop_poses()
        if self._frame_counter % self._env_interval == 0:
            self._load_next_env()
        # Set a new random distance from which to take capture the next frame
        self._trigger_distance = random.uniform(1.75, 2.5)
        self._timeline.play()
        self._timeline_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
            event_name=omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
            on_event=self._on_timeline_event,
            observer_name="amr_navigation.NavSDGDemo._on_timeline_event",
        )

    def _on_timeline_event(self, e: carb.eventdispatcher.Event) -> None:
        """Check distance to dolly and trigger SDG capture when close enough."""
        carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
        dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        dist = (Gf.Vec2f(dolly_loc[0], dolly_loc[1]) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
        if dist < self._trigger_distance:
            print(f"[SDG] Starting SDG for frame no. {self._frame_counter}")
            self._timeline.pause()
            if self._is_running_in_script_editor():
                import asyncio

                task = asyncio.ensure_future(self._run_sdg_async())
                task.add_done_callback(self._on_sdg_done)
            else:
                self._run_sdg()
                self._setup_next_frame()


out_dir = os.path.join(os.getcwd(), "_out_nav_sdg_demo", "")
selected_env_urls = args.env_urls if args.env_urls is not None else DEFAULT_ENV_URLS
nav_demo = NavSDGDemo()
nav_demo.start(
    num_frames=args.num_frames,
    out_dir=out_dir,
    env_urls=selected_env_urls,
    env_interval=args.env_interval,
    use_temp_rp=args.use_temp_rp,
    seed=22,
)

while simulation_app.is_running() and nav_demo.is_running():
    simulation_app.update()

simulation_app.close()

```
Copy to clipboard
Script Editor
To run the example from the script editor, the following code must be executed:
Script Editor Script

```
import asyncio
import builtins
import os
import random
from itertools import cycle

import carb.settings
import omni.client
import omni.kit.app
import omni.replicator.core as rep
import omni.timeline
import omni.usd
import omni.usd.commands
from isaacsim.core.experimental.utils.stage import create_new_stage
from isaacsim.storage.native import get_assets_root_path
from pxr import Gf, UsdGeom

DEFAULT_ENV_URLS = [
    "/Isaac/Environments/Grid/default_environment.usd",
    "/Isaac/Environments/Simple_Warehouse/warehouse.usd",
    "/Isaac/Environments/Grid/gridroom_black.usd",
    None,
]
NUM_FRAMES = 9
ENV_INTERVAL = 3
USE_TEMP_RP = True


class NavSDGDemo:
    """Demonstration of synthetic data generation using an AMR navigating towards a target."""

    CARTER_URL = "/Isaac/Samples/Replicator/OmniGraph/nova_carter_nav_only.usd"
    DOLLY_URL = "/Isaac/Props/Dolly/dolly.usd"
    PROPS_URL = "/Isaac/Props/YCB/Axis_Aligned_Physics"
    LEFT_CAMERA_REL_PATH = "sensors/front_hawk/left/camera_left"
    RIGHT_CAMERA_REL_PATH = "sensors/front_hawk/right/camera_right"
    ENVIRONMENT_SCOPE_PATH = "/Environment"

    def __init__(self) -> None:
        """Initialize the navigation SDG demo with default values."""
        self._carter_chassis = None
        self._carter_nav_target = None
        self._dolly = None
        self._dolly_light = None
        self._props = []
        self._cycled_env_urls = None
        self._env_interval = 1
        self._timeline = None
        self._timeline_sub = None
        self._stage_event_sub = None
        self._stage = None
        self._trigger_distance = 2.0
        self._num_frames = 0
        self._frame_counter = 0
        self._writer = None
        self._out_dir = None
        self._render_products = []
        self._use_temp_rp = False
        self._in_running_state = False
        self._completion_event = None

    async def run_async(
        self,
        num_frames: int = 10,
        out_dir: str | None = None,
        env_urls: list[str | None] | None = None,
        env_interval: int = 3,
        use_temp_rp: bool = False,
        seed: int | None = None,
    ) -> None:
        """Run the SDG demo asynchronously and wait for completion."""
        self._completion_event = asyncio.Event()
        self.start(
            num_frames=num_frames,
            out_dir=out_dir,
            env_urls=env_urls,
            env_interval=env_interval,
            use_temp_rp=use_temp_rp,
            seed=seed,
        )
        await self._completion_event.wait()

    def start(
        self,
        num_frames: int = 10,
        out_dir: str | None = None,
        env_urls: list[str | None] | None = None,
        env_interval: int = 3,
        use_temp_rp: bool = False,
        seed: int | None = None,
    ) -> None:
        """Start the SDG demo with the given configuration."""
        print(f"[SDG] Starting")
        if seed is not None:
            rep.set_global_seed(seed)
            random.seed(seed)
        selected_env_urls = env_urls if env_urls is not None else DEFAULT_ENV_URLS
        self._num_frames = num_frames
        self._out_dir = out_dir if out_dir is not None else os.path.join(os.getcwd(), "_out_nav_sdg_demo")
        self._cycled_env_urls = cycle(selected_env_urls)
        self._env_interval = env_interval
        self._use_temp_rp = use_temp_rp
        self._frame_counter = 0
        self._trigger_distance = 2.0
        self._load_env()
        self._randomize_dolly_pose()
        self._randomize_dolly_light()
        self._randomize_prop_poses()
        self._setup_sdg()
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline.play()
        self._timeline_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED), self._on_timeline_event
        )
        self._stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop_by_type(int(omni.usd.StageEventType.CLOSING), self._on_stage_closing_event)
        )
        self._in_running_state = True

    def clear(self) -> None:
        """Reset all state variables and unsubscribe from events."""
        self._cycled_env_urls = None
        self._carter_chassis = None
        self._carter_nav_target = None
        self._dolly = None
        self._dolly_light = None
        self._timeline = None
        self._frame_counter = 0
        if self._stage_event_sub:
            self._stage_event_sub.unsubscribe()
        self._stage_event_sub = None
        if self._timeline_sub:
            self._timeline_sub.unsubscribe()
        self._timeline_sub = None
        self._clear_sdg_render_products()
        self._stage = None
        self._in_running_state = False
        # Signal completion for async waiters
        if self._completion_event:
            self._completion_event.set()
            self._completion_event = None

    def is_running(self) -> bool:
        """Return whether the SDG demo is currently running."""
        return self._in_running_state

    def _is_running_in_script_editor(self) -> bool:
        """Return whether the script is running in the Isaac Sim script editor."""
        return builtins.ISAAC_LAUNCHED_FROM_TERMINAL is True

    def _on_stage_closing_event(self, e: carb.events.IEvent) -> None:
        """Handle stage closing event by clearing state."""
        self.clear()

    def _load_env(self) -> None:
        """Create a new stage and load environment, robot, dolly, light, and props."""
        create_new_stage()
        self._stage = omni.usd.get_context().get_stage()
        rep.functional.physics.create_physics_scene(
            "/PhysicsScene", enableCCD=True, broadphaseType="MBP", enableGPUDynamics=False
        )

        # Environment
        assets_root_path = get_assets_root_path()
        self._load_environment(next(self._cycled_env_urls))

        # Nova Carter
        rep.functional.create.scope(name="NavWorld")
        carter = rep.functional.create.reference(
            position=(0, 0, 0),
            rotation=(0, 0, 0),
            usd_path=assets_root_path + self.CARTER_URL,
            parent="/NavWorld",
            name="CarterNav",
        )

        # Iterate children until targetXform (for navigation target) and chassis_link (for current location) are found
        for child in carter.GetChildren():
            if child.GetName() == "targetXform":
                self._carter_nav_target = child
                break
        for child in carter.GetChildren():
            if child.GetName() == "chassis_link":
                self._carter_chassis = child
                break

        # Dolly
        self._dolly = rep.functional.create.reference(
            position=(0, 0, 0),
            rotation=(0, 0, 0),
            usd_path=assets_root_path + self.DOLLY_URL,
            parent="/NavWorld",
            name="Dolly",
        )

        # Add colliders to the dolly and its geometry primitives
        for desc_prim in self._dolly.GetChildren():
            if desc_prim.IsA(UsdGeom.Gprim):
                rep.functional.physics.apply_rigid_body(desc_prim)

        # Light
        self._dolly_light = rep.functional.create.sphere_light(
            position=(0, 0, 0),
            intensity=250000,
            radius=0.3,
            color=(1.0, 1.0, 1.0),
            parent="/NavWorld",
            name="DollyLight",
        )

        # Props
        props_urls = []
        props_folder_path = assets_root_path + self.PROPS_URL
        result, entries = omni.client.list(props_folder_path)
        if result != omni.client.Result.OK:
            carb.log_error(f"Could not list assets in path: {props_folder_path}")
            return
        for entry in entries:
            _, ext = os.path.splitext(entry.relative_path)
            if ext == ".usd":
                props_urls.append(f"{props_folder_path}/{entry.relative_path}")

        cycled_props_url = cycle(props_urls)
        for i in range(15):
            prop_url = next(cycled_props_url)
            prop_name = os.path.splitext(os.path.basename(prop_url))[0]
            path = f"/NavWorld/Props/Prop_{prop_name}_{i}"
            prim = self._stage.DefinePrim(path, "Xform")
            prim.GetReferences().AddReference(prop_url)
            self._props.append(prim)

    def _randomize_dolly_pose(self) -> None:
        """Set random dolly position ensuring minimum distance from Carter."""
        min_dist_from_carter = 4
        carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
        for _ in range(100):
            x, y = random.uniform(-6, 6), random.uniform(-6, 6)
            dist = (Gf.Vec2f(x, y) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
            if dist > min_dist_from_carter:
                self._dolly.GetAttribute("xformOp:translate").Set((x, y, 0))
                self._carter_nav_target.GetAttribute("xformOp:translate").Set((x, y, 0))
                break
        self._dolly.GetAttribute("xformOp:rotateXYZ").Set((0, 0, random.uniform(-180, 180)))

    def _randomize_dolly_light(self) -> None:
        """Position light above dolly with random color."""
        dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        self._dolly_light.GetAttribute("xformOp:translate").Set(dolly_loc + (0, 0, 3))
        self._dolly_light.GetAttribute("inputs:color").Set(
            (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
        )

    def _randomize_prop_poses(self) -> None:
        """Stack props above the dolly with random horizontal offsets."""
        spawn_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        spawn_loc[2] = spawn_loc[2] + 0.5
        for prop in self._props:
            prop.GetAttribute("xformOp:translate").Set(spawn_loc + (random.uniform(-1, 1), random.uniform(-1, 1), 0))
            spawn_loc[2] = spawn_loc[2] + 0.2

    def _setup_sdg(self) -> None:
        """Configure SDG settings, camera parameters, writer, and render products."""
        rep.orchestrator.set_capture_on_play(False)

        # Set DLSS to Quality mode (2) for best SDG results , options: 0 (Performance), 1 (Balanced), 2 (Quality), 3 (Auto)
        carb.settings.get_settings().set("rtx/post/dlss/execMode", 2)

        # fStop=0 for well-lit sharp images; tickRate=0 forces autotrigger so the sensor
        # cameras stay in sync with rep.orchestrator.step_async under multi-tick rendering.
        for rel_path in (self.LEFT_CAMERA_REL_PATH, self.RIGHT_CAMERA_REL_PATH):
            camera_prim = self._stage.GetPrimAtPath(self._carter_chassis.GetPath().AppendPath(rel_path))
            camera_prim.GetAttribute("fStop").Set(0.0)
            if camera_prim.HasAttribute("omni:sensor:tickRate"):
                camera_prim.GetAttribute("omni:sensor:tickRate").Set(0.0)

        backend = rep.backends.get("DiskBackend")
        backend.initialize(output_dir=self._out_dir)
        print(f"[SDG] Writing data to: {self._out_dir}")
        self._writer = rep.writers.get("BasicWriter")
        self._writer.initialize(backend=backend, rgb=True)
        self._setup_sdg_render_products()

    def _setup_sdg_render_products(self) -> None:
        """Create and attach render products for left and right cameras."""
        print(f"[SDG] Creating SDG render products")
        left_camera_path = self._carter_chassis.GetPath().AppendPath(self.LEFT_CAMERA_REL_PATH)
        rp_left = rep.create.render_product(
            str(left_camera_path),
            (1024, 1024),
            name="left_sensor",
            force_new=True,
        )
        right_camera_path = self._carter_chassis.GetPath().AppendPath(self.RIGHT_CAMERA_REL_PATH)
        rp_right = rep.create.render_product(
            str(right_camera_path),
            (1024, 1024),
            name="right_sensor",
            force_new=True,
        )
        self._render_products = [rp_left, rp_right]
        # For better performance the render products can be disabled when not in use, and re-enabled only during SDG
        if self._use_temp_rp:
            self._disable_render_products()
        self._writer.attach(self._render_products)

    def _clear_sdg_render_products(self) -> None:
        """Detach writer and destroy all render products."""
        print(f"[SDG] Clearing SDG render products")
        if self._writer:
            self._writer.detach()
        for rp in self._render_products:
            rp.destroy()
        self._render_products.clear()
        if self._stage.GetPrimAtPath("/Replicator"):
            omni.kit.commands.execute("DeletePrimsCommand", paths=["/Replicator"])

    def _enable_render_products(self) -> None:
        """Enable texture updates on all render products."""
        print(f"[SDG] Enabling render products for SDG..")
        for rp in self._render_products:
            rp.hydra_texture.set_updates_enabled(True)

    def _disable_render_products(self) -> None:
        """Disable texture updates on all render products."""
        print(f"[SDG] Disabling render products (enabled only during SDG)..")
        for rp in self._render_products:
            rp.hydra_texture.set_updates_enabled(False)

    def _run_sdg(self) -> None:
        """Execute one SDG capture step synchronously."""
        if self._use_temp_rp:
            self._enable_render_products()
        rep.orchestrator.step(rt_subframes=16)
        if self._use_temp_rp:
            self._disable_render_products()

    async def _run_sdg_async(self) -> None:
        """Execute one SDG capture step asynchronously."""
        if self._use_temp_rp:
            self._enable_render_products()
        await rep.orchestrator.step_async(rt_subframes=16)
        if self._use_temp_rp:
            self._disable_render_products()

    def _load_next_env(self) -> None:
        """Replace current environment with the next one from the cycle."""
        self._load_environment(next(self._cycled_env_urls))

    def _load_environment(self, env_url: str | None) -> None:
        """Load the next environment under a shared scope."""
        if self._stage.GetPrimAtPath(self.ENVIRONMENT_SCOPE_PATH):
            omni.kit.commands.execute("DeletePrimsCommand", paths=[self.ENVIRONMENT_SCOPE_PATH])

        rep.functional.create.scope(name="Environment")
        if env_url:
            assets_root_path = get_assets_root_path()
            rep.functional.create.reference(
                usd_path=assets_root_path + env_url, parent=self.ENVIRONMENT_SCOPE_PATH, name="Scene"
            )
            return

        rep.functional.create.dome_light(intensity=500, parent=self.ENVIRONMENT_SCOPE_PATH, name="DomeLight")
        ground = rep.functional.create.plane(
            parent=self.ENVIRONMENT_SCOPE_PATH, name="GroundPlane", scale=(100, 100, 1)
        )
        rep.functional.physics.apply_collider(ground)

    def _on_sdg_done(self, task) -> None:
        """Callback invoked when async SDG step completes."""
        self._setup_next_frame()

    def _setup_next_frame(self) -> None:
        """Prepare scene for next frame or finish if all frames captured."""
        self._frame_counter += 1
        if self._frame_counter >= self._num_frames:
            print(f"[SDG] Finished")
            if self._is_running_in_script_editor():
                task = asyncio.ensure_future(rep.orchestrator.wait_until_complete_async())
                task.add_done_callback(lambda t: self.clear())
            else:
                rep.orchestrator.wait_until_complete()
                self.clear()
            return

        self._randomize_dolly_pose()
        self._randomize_dolly_light()
        self._randomize_prop_poses()
        if self._frame_counter % self._env_interval == 0:
            self._load_next_env()
        # Set a new random distance from which to capture the next frame
        self._trigger_distance = random.uniform(1.75, 2.5)
        self._timeline.play()
        self._timeline_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED), self._on_timeline_event
        )

    def _on_timeline_event(self, e: carb.events.IEvent) -> None:
        """Check distance to dolly and trigger SDG capture when close enough."""
        carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
        dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
        dist = (Gf.Vec2f(dolly_loc[0], dolly_loc[1]) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
        if dist < self._trigger_distance:
            print(f"[SDG] Starting SDG for frame no. {self._frame_counter}")
            self._timeline.pause()
            self._timeline_sub.unsubscribe()
            if self._is_running_in_script_editor():
                task = asyncio.ensure_future(self._run_sdg_async())
                task.add_done_callback(self._on_sdg_done)
            else:
                self._run_sdg()
                self._setup_next_frame()


out_dir = os.path.join(os.getcwd(), "_out_nav_sdg_demo", "")
nav_demo = NavSDGDemo()
asyncio.ensure_future(
    nav_demo.run_async(
        num_frames=NUM_FRAMES,
        out_dir=out_dir,
        env_urls=DEFAULT_ENV_URLS,
        env_interval=ENV_INTERVAL,
        use_temp_rp=USE_TEMP_RP,
        seed=22,
    )
)

```
Copy to clipboard
Code Explanation
This tab describes each section of the larger sample script that is used for this tutorial. By reviewing the descriptions and code snippets you can understand how the script is working and how you might customize it for your use.
The following snippets can be used to load and start the demo scene. Each of the snippets has an explanation that can be expanded. The snippets and explanations are collapsed so that you can control opening them as you read and work through the tutorial for yourself.
**Running the AMR Navigation SDG Demo**
The following snippet is from the end of the code sample, it runs for the given `num_frames` and changes the background environment every `env_interval`. The output is written to the given `out_dir path`. The `use_temp_rp` parameter can be used to optimize performance by creating render products only for the frames when the data is captured. When `--env_urls` is provided it replaces `DEFAULT_ENV_URLS` entirely; otherwise the demo uses the default environment cycle.
The start method loads and runs the demo with the specified parameters, while clear halts the demo and clears any active subscribers and render products. You can use `is_running` to verify whether the demo is still running.
Running the NavSDGDemo Python Script Example

```
out_dir = os.path.join(os.getcwd(), "_out_nav_sdg_demo", "")
selected_env_urls = args.env_urls if args.env_urls is not None else DEFAULT_ENV_URLS
nav_demo = NavSDGDemo()
nav_demo.start(
    num_frames=args.num_frames,
    out_dir=out_dir,
    env_urls=selected_env_urls,
    env_interval=args.env_interval,
    use_temp_rp=args.use_temp_rp,
    seed=22,
)

while simulation_app.is_running() and nav_demo.is_running():
    simulation_app.update()

simulation_app.close()

```
Copy to clipboard
**NavSDGDemo Class and Attributes**
The demo script is wrapped in its own class called `NavSDGDemo`.
NavSDGDemo Class Snippet

```
class NavSDGDemo:
    """Demonstration of synthetic data generation using an AMR navigating towards a target."""

    CARTER_URL = "/Isaac/Samples/Replicator/OmniGraph/nova_carter_nav_only.usd"
    DOLLY_URL = "/Isaac/Props/Dolly/dolly.usd"
    PROPS_URL = "/Isaac/Props/YCB/Axis_Aligned_Physics"
    LEFT_CAMERA_REL_PATH = "sensors/front_hawk/left/camera_left"
    RIGHT_CAMERA_REL_PATH = "sensors/front_hawk/right/camera_right"
    ENVIRONMENT_SCOPE_PATH = "/Environment"

    def __init__(self) -> None:
        """Initialize the navigation SDG demo with default values."""
        self._carter_chassis = None
        self._carter_nav_target = None
        self._dolly = None
        self._dolly_light = None
        self._props = []
        self._cycled_env_urls = None
        self._env_interval = 1
        self._timeline = None
        self._timeline_sub = None
        self._stage_event_sub = None
        self._stage = None
        self._trigger_distance = 2.0
        self._num_frames = 0
        self._frame_counter = 0
        self._writer = None
        self._out_dir = None
        self._render_products = []
        self._use_temp_rp = False
        self._in_running_state = False

```
Copy to clipboard
The attributes of this class include:
  * `self._carter_chassis` and `self._carter_nav_target` prims are used to track Nova Carter and its target Xform in the navigation graph
  * `self._dolly` is used as the target for the navigation target of Nova Carter and to track the distance to Nova Carter
  * `self._dolly_light` randomized light placed above the dolly each captured frame
  * `self._props` list of prop prims to place and simulate above the dolly each captured frame
  * `self._cycled_env_urls` the paths for the background environments to cycle through, including `None` for the generic Replicator-built environment
  * `self._env_interval` is used to determine after how many frames to change the background environment
  * `self._timeline` is used to control (play/pause) the simulation timeline between frame captures
  * `self._timeline_sub` is the subscriber to the timeline ticks. It is used as the feedback loop to trigger the synthetic data generation
  * `self._stage_event_sub` is a subscriber to stage closing events used to clear the demo in case a new stage is opened
  * `self._stage` is used to access the active stage in order to create, access, and delete prims of interest
  * `self._trigger_distance` is used to determine the distance between Nova Carter and the dolly at which the synthetic data generation should trigger, the value is randomized after each capture
  * `self._num_frames` and `self._frame_counter` are used to track and stop the demo after the given number of frames
  * `self._writer` is the writer used to write the synthetic data to disk
  * `self._render_products` are the two render products attached to the left and right camera sensors of Nova Carter, the writer is attached to these to access data from the annotators
  * `self._use_temp_rp` is a flag, which when set to `True`, causes the demo to disable render products when not capturing. Otherwise the render products are always enabled
  * `self._in_running_state` indicates the running state of the demo used to track whether the demo has finished or not
  * The class constant `ENVIRONMENT_SCOPE_PATH` keeps both referenced USD environments and the generic fallback environment under the same `/Environment` scope, which makes switching between them consistent.


**Workflow and Start Function**
The workflow’s main functions are `start` and the `_on_timeline_event` callback functions. `start` resolves the selected environment list, creates a new environment with:
  * navigation specific physics scene
  * Nova Carter
  * navigation graph with the target Xform
  * dolly
  * randomization light
  * props to drop around the dolly


If `env_urls` is `None`, `start` uses `DEFAULT_ENV_URLS`. Environment changes are routed through `_load_environment`, which always rebuilds the shared `/Environment` scope. When the selected environment entry is `None`, the demo creates a generic environment with `rep.functional.create.dome_light`, `rep.functional.create.plane`, and `rep.functional.physics.apply_collider`.
It also creates the timeline subscriber with `_on_timeline_event` as the callback function triggered with each timeline tick. The `_on_timeline_event` function checks if Nova Carter is close enough to the dolly, if so it pauses the simulation, unsubscribes the timeline callback, and triggers the synthetic data generation (SDG). Depending on whether the demo is running in the script editor or as a standalone application it runs the SDG synchronously or asynchronously.
Workflow Snippet

```
def start(
    self,
    num_frames: int = 10,
    out_dir: str | None = None,
    env_urls: list[str | None] | None = None,
    env_interval: int = 3,
    use_temp_rp: bool = False,
    seed: int | None = None,
) -> None:
    """Start the SDG demo with the given configuration."""
    print(f"[SDG] Starting")
    if seed is not None:
        rep.set_global_seed(seed)
        random.seed(seed)
    selected_env_urls = env_urls if env_urls is not None else DEFAULT_ENV_URLS
    self._num_frames = num_frames
    self._out_dir = out_dir if out_dir is not None else os.path.join(os.getcwd(), "_out_nav_sdg_demo")
    self._cycled_env_urls = cycle(selected_env_urls)
    self._env_interval = env_interval
    self._use_temp_rp = use_temp_rp
    self._frame_counter = 0
    self._trigger_distance = 2.0
    self._load_env()
    self._randomize_dolly_pose()
    self._randomize_dolly_light()
    self._randomize_prop_poses()
    self._setup_sdg()
    self._timeline = omni.timeline.get_timeline_interface()
    self._timeline.play()
    self._timeline_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
        event_name=omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
        on_event=self._on_timeline_event,
        observer_name="amr_navigation.NavSDGDemo._on_timeline_event",
    )
    self._stage_event_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
        event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.CLOSING),
        on_event=self._on_stage_closing_event,
        observer_name="amr_navigation.NavSDGDemo._on_stage_closing_event",
    )
    self._in_running_state = True

```
Copy to clipboard

```
def _on_timeline_event(self, e: carb.eventdispatcher.Event):
    """Check distance to dolly and trigger SDG capture when close enough."""
    carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
    dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
    dist = (Gf.Vec2f(dolly_loc[0], dolly_loc[1]) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
    if dist < self._trigger_distance:
        print(f"[SDG] Starting SDG for frame no. {self._frame_counter}")
        self._timeline.pause()
        if self._is_running_in_script_editor():
            import asyncio

            task = asyncio.ensure_future(self._run_sdg_async())
            task.add_done_callback(self._on_sdg_done)
        else:
            self._run_sdg()
            self._setup_next_frame()

```
Copy to clipboard
**Randomizations Explanation**
To randomize the environment before the synthetic data capture, the following functions are used:
  * `_randomize_dolly_pose`: places the dolly at a random pose with a given minimum distance from Nova Carter. After such a pose is found, the navigation target is placed at the dolly’s position.
  * `_randomize_dolly_light`: places the dolly light above the dolly with a new random color.
  * `_randomize_prop_poses`: places the props above the dolly at random locations, which eventually starts to fall after the simulation starts.

Randomizations Snippet

```
def _randomize_dolly_pose(self) -> None:
    """Set random dolly position ensuring minimum distance from Carter."""
    min_dist_from_carter = 4
    carter_loc = self._carter_chassis.GetAttribute("xformOp:translate").Get()
    for _ in range(100):
        x, y = random.uniform(-6, 6), random.uniform(-6, 6)
        dist = (Gf.Vec2f(x, y) - Gf.Vec2f(carter_loc[0], carter_loc[1])).GetLength()
        if dist > min_dist_from_carter:
            self._dolly.GetAttribute("xformOp:translate").Set((x, y, 0))
            self._carter_nav_target.GetAttribute("xformOp:translate").Set((x, y, 0))
            break
    self._dolly.GetAttribute("xformOp:rotateXYZ").Set((0, 0, random.uniform(-180, 180)))

def _randomize_dolly_light(self) -> None:
    """Position light above dolly with random color."""
    dolly_loc = self._dolly.GetAttribute("xformOp:translate").Get()
    self._dolly_light.GetAttribute("xformOp:translate").Set(dolly_loc + (0, 0, 3))
    self._dolly_light.GetAttribute("inputs:color").Set(
        (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1))
    )

def _randomize_prop_poses(self) -> None:
    """Stack props above the dolly with random horizontal offsets."""
    spawn_loc = self._dolly.GetAttribute("xformOp:translate").Get()
    spawn_loc[2] = spawn_loc[2] + 0.5
    for prop in self._props:
        prop.GetAttribute("xformOp:translate").Set(spawn_loc + (random.uniform(-1, 1), random.uniform(-1, 1), 0))
        spawn_loc[2] = spawn_loc[2] + 0.2

```
Copy to clipboard
**Synthetic Data Generation (SDG) Explanation**
When executing the synthetic data generation (SDG) pipeline the `rep.orchestrator.step` function is called to initiate the data capture and the execution of the writer’s write function.
Depending on the value of the `use_temp_rp` flag, the sensor’s render products are handled differently:
  * If set to `True`, the render products are only enabled during data capture.
  * `False` is the default. It renders the render products and processes every frame.


Note
`_setup_sdg` sets `omni:sensor:tickRate = 0` (autotrigger) on the Nova Carter `front_hawk` left and right cameras. Under multi-tick rendering, the per-sensor tick scheduler can fall out of sync with `rep.orchestrator.step_async` and the writer may receive no frames; forcing autotrigger keeps these sensor cameras in step with the orchestrator. This workaround is expected to be removed in a future release. See [Multi-Tick Rendering](https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_multitick_rendering.html#isaac-sim-sensors-multitick-rendering) for details on the `omni:sensor:tickRate` attribute.
Synthetic Data Generation (SDG) Snippet

```
def _run_sdg(self) -> None:
    """Execute one SDG capture step synchronously."""
    if self._use_temp_rp:
        self._enable_render_products()
    rep.orchestrator.step(rt_subframes=16)
    if self._use_temp_rp:
        self._disable_render_products()

```
Copy to clipboard
**Next Frame Explanation**
After the synthetic data generation (SDG) completes, the `_setup_next_frame` function prepares the simulation for the next frame. This involves incrementing the frame counter (`self._frame_counter`), randomizing the dolly, dolly light, and props. Then changing the background environment, if the `env_interval` is reached. Because environment loading now goes through the shared `/Environment` scope, switching between referenced USD environments and the generic `None` environment uses the same update path. Additionally the timeline and its subscriber are re-started.
If the `_num_frames` is reached the demo makes sure the the writer backend is finished with writing the data to disk (`rep.orchestrator.wait_until_complete`) and clears the demo.
Next Frame Snippet

```
def _setup_next_frame(self) -> None:
    """Prepare scene for next frame or finish if all frames captured."""
    self._frame_counter += 1
    if self._frame_counter >= self._num_frames:
        print(f"[SDG] Finished")
        # Make sure the data has been written to disk before clearing the state
        if self._is_running_in_script_editor():
            import asyncio

            task = asyncio.ensure_future(rep.orchestrator.wait_until_complete_async())
            task.add_done_callback(lambda t: self.clear())
        else:
            rep.orchestrator.wait_until_complete()
            self.clear()
        return

    self._randomize_dolly_pose()
    self._randomize_dolly_light()
    self._randomize_prop_poses()
    if self._frame_counter % self._env_interval == 0:
        self._load_next_env()
    # Set a new random distance from which to take capture the next frame
    self._trigger_distance = random.uniform(1.75, 2.5)
    self._timeline.play()
    self._timeline_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
        event_name=omni.timeline.GLOBAL_EVENT_CURRENT_TIME_TICKED,
        on_event=self._on_timeline_event,
        observer_name="amr_navigation.NavSDGDemo._on_timeline_event",
    )

```
Copy to clipboard
