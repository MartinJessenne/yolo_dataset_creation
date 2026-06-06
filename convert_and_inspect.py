#!/usr/bin/env python3
# convert_and_inspect.py
# ─────────────────────────────────────────────────────────────────────────────
# Standalone diagnostic: converts picanolcart.dae → picanolcart.usd using
# omni.kit.asset_converter (the same path as generate_dataset.py) and then
# immediately inspects the resulting USD stage for:
#   - Up axis & metersPerUnit metadata
#   - Default prim path and type
#   - Bounding boxes of all meshes (to catch scale/orientation issues)
#
# Run on daman via Apptainer:
#   apptainer exec --overlay ~/isaac_overlay.img \
#       /path/to/isaac.sif \
#       python convert_and_inspect.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Disable RTX driver verification check for driver compatibility on daman host
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

import os
from isaacsim import SimulationApp

# ── 1. Boot Isaac Sim headless ────────────────────────────────────────────────
simulation_app = SimulationApp({"headless": True})

from isaacsim.core.utils.extensions import enable_extension
from pxr import Usd, UsdGeom

# ── 2. Enable the asset converter extension ───────────────────────────────────
enable_extension("omni.kit.asset_converter")
import omni.kit.asset_converter

# ── 3. Paths ──────────────────────────────────────────────────────────────────
cart_dae_path = os.path.abspath("./meshes/picanolcart.dae")
cart_usd_path = os.path.abspath("./meshes/picanolcart.usd")

print(f"\n>>> Input  DAE : {cart_dae_path}")
print(f">>> Output USD : {cart_usd_path}")

if not os.path.exists(cart_dae_path):
    print(f"\nERROR: picanolcart.dae not found at {cart_dae_path}")
    simulation_app.close()
    sys.exit(1)

# ── 4. Convert DAE → USD ──────────────────────────────────────────────────────
# Delete any stale USD so the converter always runs fresh.
if os.path.exists(cart_usd_path):
    print(">>> Removing stale picanolcart.usd to force a fresh conversion.")
    os.remove(cart_usd_path)

print("\n>>> Starting omni.kit.asset_converter DAE → USD conversion ...")
converter_manager = omni.kit.asset_converter.get_instance()
context = omni.kit.asset_converter.AssetConverterContext()
# Preserve the DAE's existing Z-up / meter convention.
# (AssetConverterContext has no axis-flip flag for DAE; it reads the <asset>
#  metadata in the COLLADA file automatically.)
task = converter_manager.create_converter_task(
    cart_dae_path, cart_usd_path, None, context
)

import asyncio
future = asyncio.ensure_future(task.wait_until_finished())
while not future.done():
    simulation_app.update()

success = future.result()
if not success:
    print("\nERROR: omni.kit.asset_converter conversion FAILED.")
    simulation_app.close()
    sys.exit(1)

print(">>> Conversion SUCCESS – USD file written.")

# ── 5. Inspect the resulting USD stage ───────────────────────────────────────
print("\n" + "=" * 60)
print("  USD INSPECTION REPORT")
print("=" * 60)

if not os.path.exists(cart_usd_path):
    print("ERROR: USD file not found after conversion. Aborting inspection.")
    simulation_app.close()
    sys.exit(1)

stage = Usd.Stage.Open(cart_usd_path)

# 5a. Stage-level metadata
up_axis = UsdGeom.GetStageUpAxis(stage)
meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
print(f"\n[Stage Metadata]")
print(f"  Up Axis       : {up_axis}  (expected: Z)")
print(f"  metersPerUnit : {meters_per_unit}  (expected: 1.0 for meters)")

# 5b. Default prim
root_prim = stage.GetDefaultPrim()
if root_prim.IsValid():
    print(f"\n[Default Prim]")
    print(f"  Path : {root_prim.GetPath()}")
    print(f"  Type : {root_prim.GetTypeName()}")
else:
    print("\n[Default Prim] WARNING: No default prim set on stage.")

# 5c. Bounding boxes
print("\n[Mesh Bounding Boxes]")
found_any = False
for prim in stage.Traverse():
    if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Xform):
        geom = UsdGeom.Imageable(prim)
        bbox = geom.ComputeLocalBound(Usd.TimeCode.Default(), "default")
        box_range = bbox.GetRange()
        if not box_range.IsEmpty():
            found_any = True
            size = box_range.GetMax() - box_range.GetMin()
            print(f"\n  Prim : {prim.GetPath()}  ({prim.GetTypeName()})")
            print(f"    Min  : {box_range.GetMin()}")
            print(f"    Max  : {box_range.GetMax()}")
            print(f"    Size : {size}")

if not found_any:
    print("  WARNING: No non-empty bounding boxes found – mesh may be empty or invisible!")

# 5d. Quick sanity verdict
print("\n" + "-" * 60)
print("  SANITY VERDICT")
print("-" * 60)
verdict_ok = True

if str(up_axis).upper() not in ("Z", "Z_UP"):
    print(f"  [FAIL] Up axis is '{up_axis}', expected Z. Mesh will appear sideways in Isaac Sim.")
    verdict_ok = False
else:
    print(f"  [OK]   Up axis is Z.")

if abs(meters_per_unit - 1.0) > 1e-4:
    print(f"  [WARN] metersPerUnit is {meters_per_unit:.4f}, not 1.0.")
    print(f"         A value of 0.01 means the mesh is in centimetres -- will appear 100x smaller.")
    verdict_ok = False
else:
    print(f"  [OK]   metersPerUnit = {meters_per_unit} (meters).")

if not found_any:
    print("  [FAIL] No mesh geometry detected – USD stage is empty.")
    verdict_ok = False

if verdict_ok:
    print("\n  OK: USD looks correct. picanolcart.usd is ready for generate_dataset.py.")
else:
    print("\n  FAIL: Issues detected. Pre-process the DAE in Blender before re-running.")

print("=" * 60 + "\n")

simulation_app.close()
