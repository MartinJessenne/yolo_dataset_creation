# discover_assets.py
# Standalone, lightweight Nucleus asset inventory tool for Isaac Sim 6.0.1.
#
# Lists what's actually available under the Isaac asset catalog on this asset server
# (Environments, Simple_Warehouse/Props, and the broader Props catalog), so
# generate_dataset_6_0_1.py's WAREHOUSE_SCENES / prop_urls lists can be extended from a
# real inventory instead of guessed filenames. Does no rendering or scene loading, so it's
# cheap to run on rented GPU time compared to the full generator.
#
# Usage: <isaac_sim_python> discover_assets.py

import os
import sys
import json

os.environ["OMNICLIENT_HUB_MODE"] = "disabled"
os.environ["OMNICLIENT_USE_HUB"] = "0"

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Same host-compatibility workaround used in generate_dataset_6_0_1.py
sys.argv.append("--/rtx/verifyDriverVersion/enabled=false")

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import omni.client
from isaacsim.storage.native import get_assets_root_path

omni.client.set_log_level(omni.client.LogLevel.ERROR)

assets_root = get_assets_root_path()
if not assets_root:
    print("\nERROR: get_assets_root_path() returned None. Cannot resolve Isaac assets. "
          "Check Nucleus/asset server connectivity.")
    simulation_app.close()
    exit(1)

ISAAC_ASSETS = f"{assets_root}/Isaac"

USD_EXTS = (".usd", ".usda", ".usdc", ".usdz")

# Folders to inventory, keyed by a human-readable label
TARGET_FOLDERS = {
    "environments": f"{ISAAC_ASSETS}/Environments",
    "simple_warehouse_props": f"{ISAAC_ASSETS}/Environments/Simple_Warehouse/Props",
    "props": f"{ISAAC_ASSETS}/Props",
}

MAX_RECURSION_DEPTH = 4


def list_usd_files(folder_url, depth=0):
    """Recursively list all USD files under folder_url via omni.client.list().

    Pattern taken from replicator_latest_docs/isaacsim_replicator_tutorials_tutorial_replicator_amr_navigation.md
    (omni.client.list returns (result, entries), each entry has .relative_path).
    """
    result, entries = omni.client.list(folder_url)
    if result != omni.client.Result.OK:
        print(f"    WARNING: could not list {folder_url} (result={result})")
        return []

    files = []
    for entry in entries:
        name = entry.relative_path
        full_url = f"{folder_url}/{name}"
        _, ext = os.path.splitext(name)
        if ext.lower() in USD_EXTS:
            files.append(full_url)
        elif ext == "" and depth < MAX_RECURSION_DEPTH:
            # No extension -> treat as a subfolder and recurse
            files.extend(list_usd_files(full_url, depth + 1))
    return files


inventory = {}
for label, folder_url in TARGET_FOLDERS.items():
    print(f"\n>>> Listing '{label}': {folder_url}")
    files = sorted(list_usd_files(folder_url))
    inventory[label] = files
    print(f">>> Found {len(files)} USD file(s) under '{label}'")
    for f in files[:20]:
        print(f"    {f}")
    if len(files) > 20:
        print(f"    ... and {len(files) - 20} more (see asset_inventory.json)")

output_path = os.path.abspath("./asset_inventory.json")
with open(output_path, "w") as fp:
    json.dump(inventory, fp, indent=2)

print(f"\n>>> Wrote full inventory ({sum(len(v) for v in inventory.values())} files total) "
      f"to {output_path}")

simulation_app.close()
