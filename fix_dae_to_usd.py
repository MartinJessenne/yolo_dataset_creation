#!/usr/bin/env python3
# fix_dae_to_usd.py
# ─────────────────────────────────────────────────────────────────────────────
# Blender headless script: imports picanolcart.dae and exports a clean
# picanolcart.usd with:
#   - Z-up axis  (Isaac Sim / USD native convention)
#   - metersPerUnit = 1.0  (geometry in meters, not cm or mm)
#   - All transforms applied (no hidden scale factors)
#   - No animations, no armatures, no materials (pure geometry)
#
# Usage:
#   blender --background --python fix_dae_to_usd.py -- \
#       /path/to/picanolcart.dae \
#       /path/to/picanolcart.usd
#
# If no arguments are provided, falls back to defaults relative to this script.
# ─────────────────────────────────────────────────────────────────────────────

import bpy
import sys
import os
import math

# ── Parse CLI arguments ───────────────────────────────────────────────────────
# Blender passes everything after "--" to the script.
argv = sys.argv
try:
    sep_idx = argv.index("--")
    script_args = argv[sep_idx + 1:]
except ValueError:
    script_args = []

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if len(script_args) >= 2:
    INPUT_DAE = os.path.abspath(script_args[0])
    OUTPUT_USD = os.path.abspath(script_args[1])
else:
    # Defaults: look for meshes/ folder next to this script
    INPUT_DAE = os.path.join(SCRIPT_DIR, "meshes", "picanolcart.dae")
    OUTPUT_USD = os.path.join(SCRIPT_DIR, "meshes", "picanolcart.usd")

print(f"\n>>> Input  DAE : {INPUT_DAE}")
print(f">>> Output USD : {OUTPUT_USD}")

if not os.path.exists(INPUT_DAE):
    print(f"ERROR: DAE file not found at {INPUT_DAE}")
    sys.exit(1)

# ── 1. Wipe the default scene (cube, camera, light) ──────────────────────────
print("\n>>> Clearing default scene ...")
bpy.ops.wm.read_factory_settings(use_empty=True)

# ── 2. Set scene units to Metric / Meters ────────────────────────────────────
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0  # 1 Blender unit = 1 metre

# ── 3. Import the COLLADA (.dae) file ────────────────────────────────────────
print(">>> Importing COLLADA (DAE) ...")
bpy.ops.wm.collada_import(
    filepath=INPUT_DAE,
    import_units=True,          # Respect the DAE's <unit meter="1"/> tag
    fix_orientation=False,      # The DAE is already Z-up; don't flip
    find_chains=False,
    auto_connect=False,
)

imported_objects = list(bpy.data.objects)
print(f"    Imported {len(imported_objects)} object(s): {[o.name for o in imported_objects]}")

if not imported_objects:
    print("ERROR: No objects were imported from the DAE file. Aborting.")
    sys.exit(1)

# ── 4. Select all objects and apply all transforms ───────────────────────────
# This bakes location/rotation/scale into the mesh vertex coordinates so the
# USD has no residual transform stack that could confuse Isaac Sim.
print(">>> Applying all transforms ...")
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = imported_objects[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ── 5. Sanity-check bounding box in Blender (should be ~2.5m × 0.8m × 0.75m) ─
print("\n>>> Blender-side bounding box check:")
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        world_bbox = [obj.matrix_world @ v.co for v in obj.data.vertices]
        if world_bbox:
            xs = [v.x for v in world_bbox]
            ys = [v.y for v in world_bbox]
            zs = [v.z for v in world_bbox]
            sx = max(xs) - min(xs)
            sy = max(ys) - min(ys)
            sz = max(zs) - min(zs)
            print(f"    Object '{obj.name}':")
            print(f"      X range : [{min(xs):.4f}, {max(xs):.4f}]  size = {sx:.4f} m")
            print(f"      Y range : [{min(ys):.4f}, {max(ys):.4f}]  size = {sy:.4f} m")
            print(f"      Z range : [{min(zs):.4f}, {max(zs):.4f}]  size = {sz:.4f} m")

# ── 6. Export to USD ──────────────────────────────────────────────────────────
# Isaac Sim expects Z-up (which matches Blender's native Z-up).
# metersPerUnit = 1.0 is Blender's default USD export value.
print(f"\n>>> Exporting to USD: {OUTPUT_USD}")
os.makedirs(os.path.dirname(OUTPUT_USD), exist_ok=True)

bpy.ops.wm.usd_export(
    filepath=OUTPUT_USD,
    # ── Geometry ──────────────────────────────────────────────────────────────
    export_meshes=True,
    export_normals=True,
    export_uvmaps=True,
    # ── Materials – export basic materials (no textures for now) ──────────────
    export_materials=True,
    export_textures=False,          # Avoids missing-texture warnings on daman
    # ── Transforms ───────────────────────────────────────────────────────────
    # Blender is natively Z-up. We keep Z-up to match Isaac Sim's expectation.
    # No axis conversion needed.
    # ── Hierarchy ─────────────────────────────────────────────────────────────
    export_hierarchy=True,          # Preserve the prim hierarchy from the DAE
    use_instancing=False,           # Simpler output without USD instanceables
    # ── Animation / Rigging (not needed for a static cart mesh) ───────────────
    export_animation=False,
    export_hair=False,
    export_particles=False,
)

print(">>> USD export complete.")

# ── 7. Quick post-export metadata check (via pxr if available) ───────────────
try:
    from pxr import Usd, UsdGeom
    print("\n>>> Verifying exported USD metadata via pxr ...")
    stage = Usd.Stage.Open(OUTPUT_USD)
    up_axis = UsdGeom.GetStageUpAxis(stage)
    mpu = UsdGeom.GetStageMetersPerUnit(stage)
    print(f"    Up Axis       : {up_axis}  (expected: Z)")
    print(f"    metersPerUnit : {mpu}  (expected: 1.0)")
    if str(up_axis).upper() in ("Z", "Z_UP") and abs(mpu - 1.0) < 1e-4:
        print("    VERDICT: OK – USD metadata is correct.")
    else:
        print("    VERDICT: WARN – metadata mismatch, check output manually.")
except ImportError:
    print("    pxr not available in this Python env – skip metadata check.")

print(f"\n>>> Done. USD written to: {OUTPUT_USD}\n")
