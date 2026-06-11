#!/usr/bin/env python3
"""
Upload script for pushing cart docking perception datasets to Hugging Face Hub.
Requires: pip install huggingface_hub
"""

import os
import argparse
from huggingface_hub import HfApi, login

def main():
    parser = argparse.ArgumentParser(description="Upload dataset to Hugging Face Hub")
    parser.add_argument(
        "--dataset_dir", 
        type=str, 
        required=True, 
        help="Path to the local dataset directory (e.g., ./_output_dataset_picanol)"
    )
    parser.add_argument(
        "--repo_id", 
        type=str, 
        default="UItraviolet/nxtbot-cart-picanol",
        help="Target Hugging Face repository ID (default: UItraviolet/nxtbot-cart-picanol)"
    )
    parser.add_argument(
        "--token", 
        type=str, 
        default=os.environ.get("HF_TOKEN"), 
        help="Hugging Face write token (falls back to HF_TOKEN environment variable)"
    )
    parser.add_argument(
        "--private", 
        action="store_true", 
        help="Create the repository as private if it does not already exist"
    )
    args = parser.parse_args()

    # 1. Authentication
    if args.token:
        print(">>> Logging into Hugging Face Hub...")
        login(token=args.token)
    else:
        print(">>> Warning: No token provided. Attempting to use existing huggingface-cli credentials...")

    api = HfApi()

    # 2. Verify or create repository
    try:
        api.repo_info(repo_id=args.repo_id, repo_type="dataset")
        print(f">>> Found existing Hugging Face dataset repository: {args.repo_id}")
    except Exception:
        print(f">>> Repository {args.repo_id} not found. Creating a new one...")
        try:
            api.create_repo(
                repo_id=args.repo_id, 
                repo_type="dataset", 
                private=args.private, 
                exist_ok=True
            )
            print(f">>> Repository created successfully.")
        except Exception as e:
            print(f"ERROR: Failed to create repository: {e}")
            return

    # 3. Upload folder
    print(f">>> Starting upload of '{args.dataset_dir}' to 'https://huggingface.co/datasets/{args.repo_id}'...")
    try:
        api.upload_folder(
            folder_path=args.dataset_dir,
            repo_id=args.repo_id,
            repo_type="dataset",
            commit_message="Add generated simulation dataset frames"
        )
        print(">>> Upload completed successfully! 🎉")
    except Exception as e:
        print(f"ERROR: Upload failed: {e}")

if __name__ == "__main__":
    main()
