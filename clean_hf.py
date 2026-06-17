from huggingface_hub import HfApi, CommitOperationDelete

# --- Configuration ---
REPO_ID = "UItraviolet/cart_dataset"
REPO_TYPE = "dataset"

api = HfApi()

print(f"Fetching file list for {REPO_ID}...")
# 1. List all files in the repository
repo_files = api.list_repo_files(repo_id=REPO_ID, repo_type=REPO_TYPE, )

# 2. Filter for files that are strictly in the root directory
# We look for files that do not contain a slash '/'
root_files_to_delete = [f for f in repo_files if "/" not in f]

# Safety Check: Exclude critical configuration files you want to keep at the root
CRITICAL_FILES = {".gitattributes", "README.md", "dataset_info.json"}
root_files_to_delete = [f for f in root_files_to_delete if f not in CRITICAL_FILES]

if not root_files_to_delete:
    print("No stray files found in the root directory.")
    exit()

print(f"Found {len(root_files_to_delete)} files to delete from the root.")
print("First 5 files to delete:", root_files_to_delete[:5])

# Confirm before destructive action
confirm = input("Are you sure you want to delete these files? (y/N): ")
if confirm.lower() != 'y':
    print("Aborted.")
    exit()

# 3. Prepare the batch deletion operations
operations = [
    CommitOperationDelete(path_in_repo=file_path) 
    for file_path in root_files_to_delete
]

# 4. Commit the changes in bulk
print("Sending batch deletion commit to Hugging Face...")
api.create_commit(
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    operations=operations,
    commit_message=f"Clean up {len(root_files_to_delete)} stray files from root"
)

print("Cleanup complete. Subfolders remain untouched.")