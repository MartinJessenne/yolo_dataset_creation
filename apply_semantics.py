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
INPUT_PATH  = os.path.join(MESHES_DIR, "picanolcart.usdc")
OUTPUT_PATH = os.path.join(MESHES_DIR, "picanolcart.usd")

# ── Semantic label map ────────────────────────────────────────────────────────
# Keys are the USD prim paths (as authored by Blender).
# Values are the semantic class labels Isaac Sim Replicator will output.
SEMANTICS = {
    "/root/cart_body":    "cart_body",
    "/root/left_handle":  "left_handle",
    "/root/right_handle": "right_handle",
}

# Blender-default prims that serve no purpose in simulation
PRIMS_TO_REMOVE = [
    "/root/Light",
    "/root/Light_001",
    "/root/Camera",
    "/root/Camera_001",
    "/root/env_light",
]

# ─────────────────────────────────────────────────────────────────────────────

print(f"\n>>> Opening: {INPUT_PATH}")
if not os.path.exists(INPUT_PATH):
    raise FileNotFoundError(
        f"picanolcart.usdc not found at {INPUT_PATH}.\n"
        "Export from Blender first."
    )

stage = Usd.Stage.Open(INPUT_PATH)

# ── 1. Verify metadata ────────────────────────────────────────────────────────
up_axis = UsdGeom.GetStageUpAxis(stage)
mpu     = UsdGeom.GetStageMetersPerUnit(stage)
print(f"    Up Axis       : {up_axis}  (expected Z)")
print(f"    metersPerUnit : {mpu}  (expected 1.0)")
assert str(up_axis).upper() in ("Z", "Z_UP"), f"Wrong up axis: {up_axis}"
assert abs(mpu - 1.0) < 1e-4, f"Wrong metersPerUnit: {mpu}"

# ── 2. Remove Blender-default scene prims ────────────────────────────────────
print("\n>>> Removing Blender-default scene prims ...")
for path in PRIMS_TO_REMOVE:
    prim = stage.GetPrimAtPath(path)
    if prim.IsValid():
        stage.RemovePrim(path)
        print(f"    Removed: {path}")
    else:
        print(f"    Not found (already absent): {path}")

# ── 3. Bake semantic attributes ───────────────────────────────────────────────
# Isaac Sim / Omniverse Kit reads semantic labels from these two custom
# attributes on a prim:
#   semantics:params:semanticType  → "class"
#   semantics:params:semanticData  → <the label string>
print("\n>>> Baking semantic attributes ...")
for prim_path, label in SEMANTICS.items():
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        print(f"    WARNING: prim not found: {prim_path} – skipping.")
        continue

    # Create or update the two semantic attributes
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

    print(f"    {prim_path}  →  class: \"{label}\"")

# ── 4. Save as .usd ───────────────────────────────────────────────────────────
print(f"\n>>> Saving to: {OUTPUT_PATH}")
stage.GetRootLayer().Export(OUTPUT_PATH)
print(">>> Done.\n")

# ── 5. Quick readback verification ────────────────────────────────────────────
print(">>> Verification readback:")
verify_stage = Usd.Stage.Open(OUTPUT_PATH)
for prim_path, expected_label in SEMANTICS.items():
    prim = verify_stage.GetPrimAtPath(prim_path)
    if prim.IsValid():
        label = prim.GetAttribute("semantics:params:semanticData").Get()
        status = "OK" if label == expected_label else f"MISMATCH (got {label})"
        print(f"    {prim_path}  →  {label}  [{status}]")
    else:
        print(f"    {prim_path}  →  NOT FOUND")
