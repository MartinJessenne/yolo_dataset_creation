# `generate_dataset_6_0_1.py` — Isaac Sim 6.0.1 Fix Pass

Notes on the changes made to get the synthetic cart dataset generator running on Isaac Sim 6.0.1 (rented vast.ai GPU), why each change was made, and what to expect when it runs. Companion to the approved plan at `.claude/plans/ok-so-here-is-delightful-barto.md`.

## 1. Background

`generate_dataset_6_0_1.py` generates synthetic RGB-D + semantic + 3D-bbox training data for three cart types (picanol, colruyt, leanflow) across four warehouse scenes, for a downstream 6D pose estimation pipeline. It's the Isaac Sim 6.0.1 port of a working 4.5-era script (`generate_dataset.py`). The port was incomplete: git history shows four incremental commits ("upgrade test" → "almost working" → "keep working" → "trying on 6.0.1"), and the project vault states plainly: *"The script just won't work."*

Debugging happens on billed rented-GPU time (no RTX-capable GPU locally), so this pass focused on resolving as much as possible by cross-referencing the code against Isaac Sim 6.0 docs, the pre-6.0.1 script, and external research — rather than trial-and-error on the GPU.

## 2. What was actually wrong

Two real problems, plus assorted rough edges:

1. **ROS2 bridge writers** (`LdrColorSDROS2PublishImage`, `DistanceToImagePlaneSDROS2PublishImage`) were publishing every generated frame to live ROS2 topics, including one literally named `camera/aligned_depth_to_color/image_raw` — a hint that ROS2 was only there to get depth registered to the color camera's frame (mimicking the real D455's `align_depth` feature). For an offline headless batch job with no ROS2 node graph listening, this added DDS-discovery hang risk for zero benefit.
2. **Depth was ground-truth, not sensor-realistic.** The script rendered `distance_to_image_plane` (Replicator's noise-free, perfect depth) from the same camera used for RGB. That's fine for geometry but defeats the point of using a D455 *digital twin*: the whole reason to simulate the real sensor is to inherit its noise characteristics (stereo-matching artifacts, holes, quantization) and narrow the sim2real gap for the downstream pose pipeline. The **pre-6.0.1** script actually understood this — it used `SingleViewDepthCameraSensor` (then under the old `omni.isaac.sensor` namespace) for exactly this reason. The 6.0.1 port dropped that sensor in favor of a plain camera + ROS2, which was a regression, not an upgrade.

Everything else (semantics API import path, `get_assets_root_path()` fallback, unvalidated `CartFrame` lookups, un-guarded cleanup calls) was papering over these two core issues and made failures harder to diagnose.

## 3. Design choices

### 3.1 Drop ROS2 entirely, keep the D455 preset

Removed the `enable_extension("isaacsim.ros2.bridge")` call and both ROS2 writers (`generate_dataset_6_0_1.py`, old lines 576–595) along with their `.detach()` calls. The official D455 USD prim loading (`prim_utils.create_prim(..., usd_path=d455_usd_path)`) stays — that's what gives "the D455 camera preset directly inside Isaac Sim," it just no longer needs a ROS2 transport to be useful.

**Why not keep ROS2 as an optional/best-effort path?** There's no reason to keep it around at all for this use case — it was solving a problem (depth alignment) that has a better, native solution (§3.2). Confirmed with you directly: ROS2 isn't needed here.

### 3.2 `SingleViewDepthCameraSensor` for realistic, pre-aligned depth

Added:

```python
from isaacsim.sensors.experimental.rtx import RtxCamera, SingleViewDepthCameraSensor
...
depth_rtx_camera = RtxCamera(rgb_camera_path)
depth_sensor = SingleViewDepthCameraSensor(
    depth_rtx_camera,
    resolution=(1280, 800),
    annotators=["depth_sensor_distance"],
)
depth_sensor.set_enabled_post_processing(True)
depth_render_product = depth_sensor.render_product
```

This wraps the **same RGB camera prim** already used for color, rather than a second physically-offset camera. Per Isaac Sim docs, `SingleViewDepthCameraSensor` simulates stereo depth (disparity, baseline, Gaussian/shot noise, outlier removal) as seen from one camera's own viewpoint, driving a `depth_sensor_distance` annotator. Because it's *single-view*, the output is already registered to that camera's frame and resolution by construction — no cross-camera baseline/extrinsic reprojection math is needed (unlike a real depth-vs-color sensor pair, or a naive two-render-product approach). The D455 USD asset is expected to carry its own baseline/focal-length configuration on an embedded render-product prim that this sensor class auto-detects.

**Why this over reimplementing `rs2::align` in Python?** An earlier draft of this plan proposed a custom numpy reimplementation of Intel's `rs2::align` (deproject via depth intrinsics → transform via baseline → reproject via color intrinsics → z-buffer occlusion resolution). That approach is geometrically sound but throws away the actual goal — realistic sensor *noise* — since Isaac Sim's own ground-truth depth annotator has none. `SingleViewDepthCameraSensor` was chosen instead because it's the tool built for this exact purpose, and is the one your own pre-6.0.1 script already relied on.

**Known risk, called out in-code:** this is not well documented for the D455 specifically — NVIDIA's own developer forum response to a near-identical question was *"we don't have a full example for your sensor."* Two things are unverified until run on GPU:
- Whether `RtxCamera(rgb_camera_path)` can wrap an **already-loaded** prim by path, or only create+load a fresh one (`RtxCamera.create(...)`).
- Whether the shipped `rsd455.usd` actually carries the embedded `OmniSensorDepthSensorSingleViewAPI` config this sensor expects to auto-detect, and whether `depth_sensor.render_product` is the right way to retrieve its output render product.

### 3.3 Fallback + diagnostic capture, not a silent guess

`DepthSensorWriter` (new writer class, `generate_dataset_6_0_1.py:329-385`) registers **both** annotators — `depth_sensor_distance` (noisy, primary) and `distance_to_image_plane` (ground truth) — on the depth render product:

- Ground truth always gets saved to `depth_ground_truth_diagnostic/frame_XXXX.npy`, so you can visually compare noisy vs. ground truth for the same frame once you have data.
- `depth/frame_XXXX.npy` (the file the rest of the pipeline actually consumes) gets the noisy sensor output when present; if `depth_sensor_distance` comes back empty, it falls back to ground truth with a loud `WARNING` printed per-frame, rather than silently producing an empty dataset.

This means a first `--frames 2` test run produces *something usable* either way, and tells you unambiguously (via the warning, or its absence) whether the noisy sensor path is actually working — without needing a dedicated smoke-test CLI mode.

**Why not just fail hard if `depth_sensor_distance` is empty?** Given the unverified wiring above, a hard failure on an undocumented API would burn GPU-rental time on a `--frames 2` sanity check that gives you nothing to look at. The fallback trades a small amount of silent-failure risk (mitigated by the per-frame warning) for a guaranteed non-empty first result.

`consolidate_dataset.py` was updated to include `depth_ground_truth_diagnostic` in its known subdirectories list — otherwise its existing cleanup step (`shutil.rmtree` on each temp scene dir after moving known subdirs) would have silently deleted the diagnostic captures before you could inspect them.

### 3.4 Robustness fixes (fail loud, fail early)

| Issue | Old behavior | New behavior | Why |
|---|---|---|---|
| Semantics import path | Hardcoded `isaacsim.core.experimental.utils.semantics` | Try experimental, fall back to `isaacsim.core.utils.semantics` | Isaac Sim 6.0 docs show both paths in different examples — likely an in-flight deprecation; the fallback survives either. |
| `get_assets_root_path()` returns `None` | Silently fell back to a hardcoded Isaac **4.5** S3 URL | Fails fast with a clear error | A 6.0.1 script silently pulling 4.5-era warehouse/sensor assets is a worse failure mode than an immediate, explicit error. |
| Missing `CartFrame` prim | Printed a `WARNING` and continued | Aborts the run | A cart generated with no semantic label doesn't fail loudly downstream — it silently corrupts the dataset (unlabeled cart instances). A multi-hour generation run discovering this after the fact is far more costly than an immediate crash. |
| Final `.detach()`/`.destroy()` cleanup | Direct calls, would raise if a writer/render-product never attached | Wrapped per-item, logs a warning and continues | So a partial setup failure earlier in the script doesn't also mask the *original* error with a secondary `AttributeError` during cleanup. |

### 3.5 Explicitly left unchanged

- **`RTSubframes=12` and the denoiser settings** (`/rtx/indirectDiffuse/denoiser/enabled`, `/rtx/reflections/denoiser/enabled`, `/rtx/pathtracing/optixDenoiser/enabled`) — the vault documented a grain/noise blocker with a proposed fix (revert to 4 subframes, drop denoiser overrides), but you confirmed that issue was a local daman-host driver mismatch, not reproducible on the rented vast.ai GPU where rendering already works correctly. Touching this now would be fixing a problem that doesn't exist on the target hardware.
- **No `--smoke_test` CLI flag or staged-run mode.** The vault's own debugging notes proposed incremental validation (camera alone → one cart → one labeled sample → full randomization) given how costly blind GPU debugging is. That instinct is sound, but you'd rather drive it manually with the existing `--frames`/`--scene_idx` flags than have a new CLI surface to maintain.

## 4. Expected results

### Output contract (unchanged downstream)

```
_output_dataset_multi_cart_temp_scene_<N>/
├── rgb/frame_XXXX.png
├── depth/frame_XXXX.npy                      # noisy depth_sensor_distance, or GT fallback
├── depth_ground_truth_diagnostic/frame_XXXX.npy   # always ground truth, for comparison
├── semantic/frame_XXXX.png
├── semantic_labels/frame_XXXX.json
├── bbox_3d/frame_XXXX.json
└── camera/frame_XXXX.json
```

`consolidate_dataset.py` shuffles and merges all scene temp dirs (including the diagnostic folder) into `_output_dataset_multi_cart/`, then deletes the temp dirs — same as before, just with one more preserved subfolder. `upload_dataset.py` is unaffected; it only reads `rgb/`, `depth/`, `semantic_labels/`, `bbox_3d/`, `camera/`.

### Two plausible outcomes on first GPU run

**Best case:** `SingleViewDepthCameraSensor` wires up cleanly, `depth_sensor_distance` produces plausible noisy depth per frame, no `WARNING` lines in the log. `depth/` and `depth_ground_truth_diagnostic/` should show the same overall cart/scene geometry, but the former has visible sensor-realistic noise (edge fuzz, occasional holes, quantization) the latter lacks. This is the target state — ROS2-free, sim2real-realistic depth, aligned to RGB by construction.

**Fallback case:** `RtxCamera(rgb_camera_path)` or `SingleViewDepthCameraSensor(...)` raises at setup (wrong constructor usage), or `depth_sensor_distance` comes back empty per-frame. You'll see either a Python traceback pointing at `generate_dataset_6_0_1.py:659-666`, or repeated `>>> WARNING: depth_sensor_distance produced no data for frame_XXXX; falling back to ground-truth...` lines. In the latter case the run still completes and produces a valid (if not sim2real-realistic) dataset — nothing blocks on this. The fix at that point is narrowly scoped to those ~8 lines (how `RtxCamera`/`SingleViewDepthCameraSensor` are constructed and how the render product is retrieved), not a redesign.

### What "done" looks like for this fix pass

No ROS2-related errors in the log, `rgb/`, `semantic/`, `semantic_labels/`, `bbox_3d/`, `camera/`, and `depth/` all populate for every requested frame, and either the noisy-depth path is confirmed working or you've made a deliberate decision to run with the ground-truth fallback for now.

## 5. Validation plan

1. **On next GPU rental**, run `--frames 2 --scene_idx 0` first (cheapest possible signal). Check for absence of ROS2 errors, presence of all six output subfolders, and whether the `depth_sensor_distance` fallback warning fires.
2. Visually diff one frame's `depth/` against its `depth_ground_truth_diagnostic/` counterpart — same scene structure, noisy version should show sensor-realistic artifacts if the primary path is working.
3. If the noisy path isn't working within roughly the first hour of GPU time, don't chase it further in this session — run with the ground-truth fallback (it already happens automatically) and revisit `RtxCamera`/`SingleViewDepthCameraSensor` wiring separately, informed by whatever error Isaac Sim actually surfaces.
4. Once confirmed working, drop the `distance_to_image_plane` diagnostic annotator from `DepthSensorWriter` to cut output size, then run the full multi-scene generation.
