import os
import sys
import shutil
import random
import glob

def consolidate_datasets(output_dir, num_scenes):
    """Gather frames from all scene temp directories, shuffle deterministically,
    and write to the final flat output directory for data leakage mitigation."""
    
    print(f"\n>>> Starting consolidation for dataset at: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    # depth_ground_truth_diagnostic is a temporary side-by-side comparison capture from
    # DepthSensorWriter (see generate_dataset_6_0_1.py) - included here so it survives
    # consolidation instead of being deleted with the temp scene dirs.
    subdirs = ["rgb", "depth", "semantic", "semantic_labels", "bbox_3d", "camera",
               "depth_ground_truth_diagnostic"]

    # 1. Gather all (scene_idx, local_frame_idx) pairs
    all_frames = []
    for scene_idx in range(num_scenes):
        temp_dir = os.path.abspath(f"{output_dir}_temp_scene_{scene_idx}")
        rgb_dir = os.path.join(temp_dir, "rgb")
        if not os.path.exists(rgb_dir):
            continue
        for file in os.listdir(rgb_dir):
            name, ext = os.path.splitext(file)
            parts = name.split("_")
            if len(parts) > 0 and parts[-1].isdigit():
                all_frames.append((scene_idx, int(parts[-1])))

    if not all_frames:
        print(">>> No frames found to consolidate. Exiting.")
        return

    # 2. Deterministic shuffle so sequential splits are homogeneous across scenes
    random.seed(42)
    random.shuffle(all_frames)
    print(f">>> Shuffled {len(all_frames)} frames across {num_scenes} scenes (seed=42)")

    # 3. Move and rename files using the shuffled global index
    for global_idx, (scene_idx, local_idx) in enumerate(all_frames):
        temp_dir = os.path.abspath(f"{output_dir}_temp_scene_{scene_idx}")
        prefix = f"frame_{local_idx:06d}"
        for subdir in subdirs:
            subdir_path = os.path.join(temp_dir, subdir)
            if not os.path.exists(subdir_path):
                continue
            for file in os.listdir(subdir_path):
                name, ext = os.path.splitext(file)
                if name == prefix:
                    new_name = f"frame_{global_idx:06d}{ext}"
                elif name.startswith(prefix + "_"):
                    suffix = name[len(prefix):]
                    new_name = f"frame_{global_idx:06d}{suffix}{ext}"
                else:
                    continue
                dest_dir = os.path.join(output_dir, subdir)
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(os.path.join(subdir_path, file), os.path.join(dest_dir, new_name))
                
        if global_idx > 0 and global_idx % 100 == 0:
            print(f">>> Consolidated {global_idx}/{len(all_frames)} frames...")

    # 4. Clean up temp directories
    for scene_idx in range(num_scenes):
        temp_dir = os.path.abspath(f"{output_dir}_temp_scene_{scene_idx}")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f">>> Cleaned up: {temp_dir}")
            except Exception as e:
                print(f"WARNING: Could not remove {temp_dir}: {e}")

    print(f"\n>>> Successfully consolidated {len(all_frames)} shuffled frames to {output_dir}")

if __name__ == "__main__":
    output_dir = os.path.abspath("./_output_dataset_multi_cart")
    
    # Try to infer the number of scenes dynamically based on existing temp directories
    scene_dirs = glob.glob(f"{output_dir}_temp_scene_*")
    if not scene_dirs:
        print(f"ERROR: No temp scene directories found matching {output_dir}_temp_scene_*")
        sys.exit(1)
        
    num_scenes = len(scene_dirs)
    consolidate_datasets(output_dir, num_scenes)
