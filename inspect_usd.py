# inspect_usd.py
# Diagnostic script to inspect USD mesh properties (Scale, Bounds, Orientation)

from isaacsim import SimulationApp
import sys

# Configure unbuffered stdout/stderr
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Start SimulationApp headless
simulation_app = SimulationApp({"headless": True})

import os
from pxr import Usd, UsdGeom, Gf

usd_path = os.path.abspath("./meshes/colruyt_cart.usd")
print(f"\n>>> Opening stage: {usd_path}")

if not os.path.exists(usd_path):
    print(f"ERROR: File {usd_path} not found.")
    simulation_app.close()
    exit(1)

stage = Usd.Stage.Open(usd_path)

# 1. Read metadata details (Up Axis and Units)
up_axis = UsdGeom.GetStageUpAxis(stage)
meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
print(f"Stage Up Axis: {up_axis}")
print(f"Meters Per Unit: {meters_per_unit} (1.0 = meters, 0.01 = centimeters, 0.001 = millimeters)")

# 2. Inspect root prim and hierarchy
root_prim = stage.GetDefaultPrim()
if root_prim.IsValid():
    print(f"Default Prim: {root_prim.GetPath()} ({root_prim.GetTypeName()})")
else:
    print("WARNING: Stage has no default prim set.")

# 3. Compute bounding boxes for all meshes
print("\n>>> Bounding Boxes of meshes:")
for prim in stage.Traverse():
    if prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Xform):
        geom_prim = UsdGeom.Imageable(prim)
        # Compute bounding box in local space, specifying the "default" purpose explicitly
        bbox = geom_prim.ComputeLocalBound(Usd.TimeCode.Default(), ["default"])
        box_range = bbox.GetRange()
        if not box_range.IsEmpty():
            size = box_range.GetMax() - box_range.GetMin()
            print(f"Prim: {prim.GetPath()} ({prim.GetTypeName()})")
            print(f"  Min Bounds: {box_range.GetMin()}")
            print(f"  Max Bounds: {box_range.GetMax()}")
            print(f"  Computed Size (X, Y, Z): {size}")

simulation_app.close()
