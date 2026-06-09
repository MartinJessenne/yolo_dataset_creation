# /// script
# requires-python = ">=3.10"
# dependencies = ["usd-core"]
# ///
"""
apply_semantics.py
──────────────────
Preprocessing script to run LOCALLY (no Isaac Sim needed):
  1. Opens the raw Blender-exported picanolcart.usdc
  2. Removes Blender-default Camera / Light prims (not needed in simulation)
  3. Bakes Isaac Sim-compatible semantic attributes onto each cart part prim:
       /root/cart_body     → class: "cart_body"
       /root/left_handle   → class: "left_handle"
       /root/right_handle  → class: "right_handle"
  4. Saves the result as picanolcart.usd (renames from .usdc)

Run with:
    uv run apply_semantics.py
"""

import os
from pxr import Usd, Sdf, UsdGeom

MESHES_DIR = os.path.join(os.path.dirname(__file__), "meshes")

# Configurations for each cart type
CONFIGS = [
    {
        "name": "Picanol Cart",
        "input": "picanolcart.usdc",
        "output": "picanolcart.usd",
        "semantics": {
            "/root/cart_body":    "cart_body",
            "/root/left_handle":  "left_handle",
            "/root/right_handle": "right_handle",
        }
    },
    {
        "name": "Colruyt Cart",
        "input": "colruyt.usdc",
        "output": "colruyt.usd",
        "semantics": {
            "/root/colruyt_cart": "cart_body",
        }
    }
]

# Blender-default prims that serve no purpose in simulation
PRIMS_TO_REMOVE = [
    "/root/Light",
    "/root/Light_001",
    "/root/Camera",
    "/root/Camera_001",
    "/root/env_light",
]

def process_cart(config):
    input_path = os.path.join(MESHES_DIR, config["input"])
    output_path = os.path.join(MESHES_DIR, config["output"])
    
    if not os.path.exists(input_path):
        print(f"\n>>> Skipping {config['name']}: Input file not found at {input_path}")
        return

    print(f"\n>>> Processing {config['name']} ...")
    print(f"    Opening: {input_path}")
    stage = Usd.Stage.Open(input_path)

    # ── 1. Verify metadata ────────────────────────────────────────────────────────
    up_axis = UsdGeom.GetStageUpAxis(stage)
    mpu     = UsdGeom.GetStageMetersPerUnit(stage)
    print(f"    Up Axis       : {up_axis}  (expected Z)")
    print(f"    metersPerUnit : {mpu}  (expected 1.0)")
    assert str(up_axis).upper() in ("Z", "Z_UP"), f"Wrong up axis: {up_axis}"
    assert abs(mpu - 1.0) < 1e-4, f"Wrong metersPerUnit: {mpu}"

    # ── 2. Remove Blender-default scene prims ────────────────────────────────────
    print("    Removing Blender-default scene prims ...")
    for path in PRIMS_TO_REMOVE:
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            stage.RemovePrim(path)
            print(f"      Removed: {path}")

    # ── 3. Bake semantic attributes ───────────────────────────────────────────────
    print("    Baking semantic attributes ...")
    for prim_path, label in config["semantics"].items():
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            print(f"      WARNING: prim not found: {prim_path} – skipping.")
            continue

        type_attr = prim.CreateAttribute(
            "semantics:params:semanticType",
            Sdf.ValueTypeNames.String,
            custom=True,
        )
        type_attr.Set("class")

        data_attr = prim.CreateAttribute(
            "semantics:params:semanticData",
            Sdf.ValueTypeNames.String,
            custom=True,
        )
        data_attr.Set(label)
        print(f"      {prim_path}  ➔  class: \"{label}\"")

    # ── 4. Save as .usd ───────────────────────────────────────────────────────────
    print(f"    Saving to: {output_path}")
    stage.GetRootLayer().Export(output_path)

    # ── 5. Quick readback verification ────────────────────────────────────────────
    print("    Verifying output:")
    verify_stage = Usd.Stage.Open(output_path)
    for prim_path, expected_label in config["semantics"].items():
        prim = verify_stage.GetPrimAtPath(prim_path)
        if prim.IsValid():
            label = prim.GetAttribute("semantics:params:semanticData").Get()
            status = "OK" if label == expected_label else f"MISMATCH (got {label})"
            print(f"      {prim_path}  ➔  {label}  [{status}]")
        else:
            print(f"      {prim_path}  ➔  NOT FOUND")

for config in CONFIGS:
    process_cart(config)

print("\n>>> All processing complete.\n")
