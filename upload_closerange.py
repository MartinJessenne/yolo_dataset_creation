#!/usr/bin/env python3
"""Upload the close-range batch to the Hub alongside the existing far-range shards.

WHY THIS DOES NOT USE push_to_hub
    push_to_hub deletes every existing file matching the split's shard pattern
    before writing its own. The far-range shards share those split names, so a
    push_to_hub of this batch would delete them. Files are added here through a
    plain commit, which only adds.

WHY THE GENERATOR YIELDS BYTES, NOT PATHS
    datasets' Image feature is lazy: handed a path it stores {"bytes": None,
    "path": ...} and the file contents are inlined only by push_to_hub, via
    embed_table_storage(). Writing parquet by any other route persists the path
    and drops the pixels. The generator therefore reads each file and puts the
    bytes in the table itself, so the parquet is complete by construction and no
    separate embedding step exists to be forgotten.

Two gates enforce that invariant:
    local   every written shard is reopened and asserted to carry non-null,
            PIL-decodable rgb and semantic bytes, before anything is uploaded
    remote  shards are re-downloaded from the Hub after the commit and asserted
            the same, because the local file passing proves nothing about what
            actually landed
"""
import argparse
import io
import json
import os
import random
import sys

import numpy as np
import pyarrow.parquet as pq
from datasets import Dataset, Features, Image, Sequence, Value
from huggingface_hub import CommitOperationAdd, HfApi
from PIL import Image as PILImage

FEATURES = Features({
    "rgb": Image(),
    "depth": Value("binary"),
    "depth_resolution": Sequence(Value("int32"), length=2),
    "semantic": Image(),
    "semantic_labels": Value("string"),
    "camera_aperture": Sequence(Value("float32"), length=2),
    "camera_focal_length": Value("float32"),
    "camera_projection": Sequence(Value("float32"), length=16),
    "camera_view_transform": Sequence(Value("float32"), length=16),
    "camera_resolution": Sequence(Value("int32"), length=2),
    "bbox_3d_x_min": Sequence(Value("float32")),
    "bbox_3d_y_min": Sequence(Value("float32")),
    "bbox_3d_z_min": Sequence(Value("float32")),
    "bbox_3d_x_max": Sequence(Value("float32")),
    "bbox_3d_y_max": Sequence(Value("float32")),
    "bbox_3d_z_max": Sequence(Value("float32")),
    "bbox_3d_transform": Sequence(Sequence(Value("float32"), length=16)),
    "bbox_3d_semantic_id": Sequence(Value("int32")),
    "bbox_3d_class_name": Sequence(Value("string")),
    "bbox_3d_occlusion": Sequence(Value("float32")),
})

# Matches the existing shards on the Hub, which hold 93 rows each.
ROWS_PER_SHARD = 93
SPLIT_FRACTIONS = {"train": 0.8, "validation": 0.1, "test": 0.1}
# Fixed so a re-run reproduces the same split rather than reshuffling frames
# across train and test.
SHUFFLE_SEED = 0


def list_frames(path):
    """Frame basenames present in every modality, sorted.

    A frame missing any one modality is dropped rather than yielded with a hole:
    the writer skips unlabelled frames, so gaps are expected and benign.
    """
    rgb_dir = os.path.join(path, "rgb")
    if not os.path.isdir(rgb_dir):
        sys.exit(f"ABORT: no rgb/ directory under {path}")

    frames = sorted(os.path.splitext(f)[0] for f in os.listdir(rgb_dir)
                    if f.endswith(".png"))
    complete, partial = [], []
    for fr in frames:
        needed = [
            os.path.join(path, "rgb", f"{fr}.png"),
            os.path.join(path, "depth", f"{fr}.npy"),
            os.path.join(path, "semantic", f"{fr}.png"),
            os.path.join(path, "semantic_labels", f"{fr}.json"),
            os.path.join(path, "bbox_3d", f"{fr}.json"),
            os.path.join(path, "camera", f"{fr}.json"),
        ]
        (complete if all(os.path.exists(p) for p in needed) else partial).append(fr)

    if partial:
        print(f"  dropped {len(partial)} incomplete frames, e.g. {partial[:3]}")
    return complete


def generator(path, frames):
    for frame in frames:
        rgb_file = os.path.join(path, "rgb", f"{frame}.png")
        sem_file = os.path.join(path, "semantic", f"{frame}.png")

        # Read the pixels here. See module docstring: a path would persist as
        # {"bytes": None, "path": ...} and the parquet would carry no image.
        with open(rgb_file, "rb") as fh:
            rgb_payload = {"path": f"{frame}.png", "bytes": fh.read()}
        with open(sem_file, "rb") as fh:
            sem_payload = {"path": f"{frame}.png", "bytes": fh.read()}

        depth_arr = np.load(os.path.join(path, "depth", f"{frame}.npy"))

        with open(os.path.join(path, "semantic_labels", f"{frame}.json")) as fh:
            sem_labels_str = fh.read()
        with open(os.path.join(path, "camera", f"{frame}.json")) as fh:
            cam = json.load(fh)
        with open(os.path.join(path, "bbox_3d", f"{frame}.json")) as fh:
            bbox_data = json.load(fh)

        cols = {k: [] for k in ("x_min", "y_min", "z_min", "x_max", "y_max", "z_max")}
        transforms, semantic_ids, class_names, occlusions = [], [], [], []
        for box in bbox_data.get("data", []):
            for k in cols:
                cols[k].append(box[k])
            transforms.append([v for row in box["transform"] for v in row])
            semantic_ids.append(box["semanticId"])
            class_names.append(box.get("className", ""))
            occlusions.append(box["occlusionRatio"])

        yield {
            "rgb": rgb_payload,
            "depth": depth_arr.tobytes(),
            "depth_resolution": list(depth_arr.shape),
            "semantic": sem_payload,
            "semantic_labels": sem_labels_str,
            "camera_aperture": cam["cameraAperture"],
            "camera_focal_length": cam["cameraFocalLength"],
            "camera_projection": cam["cameraProjection"],
            "camera_view_transform": cam["cameraViewTransform"],
            "camera_resolution": cam["renderProductResolution"],
            "bbox_3d_x_min": cols["x_min"],
            "bbox_3d_y_min": cols["y_min"],
            "bbox_3d_z_min": cols["z_min"],
            "bbox_3d_x_max": cols["x_max"],
            "bbox_3d_y_max": cols["y_max"],
            "bbox_3d_z_max": cols["z_max"],
            "bbox_3d_transform": transforms,
            "bbox_3d_semantic_id": semantic_ids,
            "bbox_3d_class_name": class_names,
            "bbox_3d_occlusion": occlusions,
        }


def split_frames(frames):
    """Shuffle before slicing so no split is a contiguous run of one scene.

    Frames are written scene by scene, so a sequential slice would hand one
    warehouse entirely to test and none of it to train.
    """
    shuffled = list(frames)
    random.Random(SHUFFLE_SEED).shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * SPLIT_FRACTIONS["train"])
    n_val = int(n * SPLIT_FRACTIONS["validation"])
    return {
        "train": shuffled[:n_train],
        "validation": shuffled[n_train:n_train + n_val],
        "test": shuffled[n_train + n_val:],
    }


def verify_parquet(local_path, context):
    """Assert every row carries decodable rgb and semantic bytes."""
    table = pq.ParquetFile(local_path).read(columns=["rgb", "semantic"])
    rows = table.num_rows
    if rows == 0:
        sys.exit(f"ABORT: {context} has 0 rows")

    for col in ("rgb", "semantic"):
        missing = sum(1 for v in table[col].to_pylist() if not (v and v.get("bytes")))
        if missing:
            sys.exit(f"ABORT: {context} has {missing}/{rows} rows with empty {col} "
                     f"bytes -- this is the defect that emptied the last upload")

    # Decode the first and last row: non-null bytes could still be truncated.
    for idx in {0, rows - 1}:
        for col in ("rgb", "semantic"):
            raw = table[col][idx].as_py()["bytes"]
            try:
                PILImage.open(io.BytesIO(raw)).load()
            except Exception as exc:
                sys.exit(f"ABORT: {context} row {idx} {col} not decodable: {exc}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset_dir")
    ap.add_argument("--repo-id", default="UItraviolet/industrial_cart")
    ap.add_argument("--tag", default="closerange",
                    help="shard name infix, keeping this batch distinct on the Hub")
    ap.add_argument("--staging", default="./_parquet_closerange")
    ap.add_argument("--dry-run", action="store_true",
                    help="build and verify shards locally, upload nothing")
    ap.add_argument("--max-gb", type=float, default=35.0,
                    help="refuse to commit if the built shards exceed this budget")
    args = ap.parse_args()

    dataset_dir = os.path.abspath(args.dataset_dir)
    os.makedirs(args.staging, exist_ok=True)

    frames = list_frames(dataset_dir)
    print(f"complete frames: {len(frames)}")
    if not frames:
        sys.exit("ABORT: nothing to upload")

    splits = split_frames(frames)
    for name, fr in splits.items():
        print(f"  {name}: {len(fr)}")

    api = HfApi()
    existing = set(api.list_repo_files(args.repo_id, repo_type="dataset"))

    operations, written = [], []
    for split, split_frames_list in splits.items():
        if not split_frames_list:
            continue
        n_shards = max(1, -(-len(split_frames_list) // ROWS_PER_SHARD))
        for i in range(n_shards):
            chunk = split_frames_list[i * ROWS_PER_SHARD:(i + 1) * ROWS_PER_SHARD]
            # One shard at a time, held in memory. Dataset.from_generator would
            # first materialise the whole split as an uncompressed Arrow cache --
            # depth alone is 4.1 MB per frame raw against ~3.3 MB for an entire
            # frame in parquet -- which overruns the disk on a split this size.
            ds = Dataset.from_list(list(generator(dataset_dir, chunk)),
                                   features=FEATURES)
            fname = f"{split}-{args.tag}-{i:05d}-of-{n_shards:05d}.parquet"
            local_path = os.path.join(args.staging, fname)
            ds.to_parquet(local_path)
            del ds

            rows = verify_parquet(local_path, fname)
            size_mb = os.path.getsize(local_path) / 1e6
            print(f"  {fname}  rows={rows}  {size_mb:.1f} MB  [local gate OK]")

            repo_path = f"data/{fname}"
            if repo_path in existing:
                sys.exit(f"ABORT: {repo_path} already exists on the Hub; refusing to "
                         f"overwrite. Change --tag or delete it deliberately first.")
            written.append((repo_path, local_path))

    total_gb = sum(os.path.getsize(l) for _, l in written) / 1e9
    print(f"\nlocal gate passed for {len(written)} shards, {total_gb:.2f} GB total")
    if total_gb > args.max_gb:
        sys.exit(f"ABORT: {total_gb:.2f} GB exceeds the {args.max_gb:.0f} GB budget. "
                 f"Nothing uploaded. Re-run on a frame subset or raise --max-gb.")
    if args.dry_run:
        print("dry run: nothing uploaded")
        return

    operations = [CommitOperationAdd(path_in_repo=r, path_or_fileobj=l)
                  for r, l in written]
    print(f"committing {len(operations)} shards to {args.repo_id} ...")
    res = api.create_commit(
        repo_id=args.repo_id,
        repo_type="dataset",
        operations=operations,
        commit_message=f"Add {len(operations)} {args.tag} shards",
    )
    print("commit:", res.commit_url)

    # Remote gate. The local file passing says nothing about what landed.
    from huggingface_hub import hf_hub_download
    sample = random.Random(1).sample(written, min(3, len(written)))
    print("\nremote gate: re-downloading shards from the Hub")
    for repo_path, _ in sample:
        got = hf_hub_download(args.repo_id, repo_path, repo_type="dataset",
                              force_download=True)
        rows = verify_parquet(got, f"HUB:{repo_path}")
        print(f"  {repo_path}  rows={rows}  [remote gate OK]")

    after = api.list_repo_files(args.repo_id, repo_type="dataset")
    print(f"\nrepo now holds {len(after)} files")
    print(f"  far-range shards still present: "
          f"{sum(1 for f in after if f.endswith('.parquet') and args.tag not in f)}")


if __name__ == "__main__":
    main()
