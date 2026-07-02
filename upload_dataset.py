import os
import sys
import json
import numpy as np
from datasets import Dataset, Features, Image, Value, Sequence

# Call it with:
# uv run upload_dataset.py ./_output_dataset_picanol
if len(sys.argv) < 2:
    print("Usage: uv run upload_dataset.py <dataset_directory>")
    sys.exit(1)

dataset_dir = os.path.abspath(sys.argv[1])

# Define the strong-typed feature schema tailored to the actual Isaac Sim Replicator output
features = Features({
    "rgb": Image(),
    "depth": Value("binary"),                          # Raw float32 depth map array bytes
    "depth_resolution": Sequence(Value("int32"), length=2),  # (height, width) of the depth array;
                                                               # not assumed equal to camera_resolution
    "semantic": Image(),                               # Colorized semantic segmentation map PNG
    
    # Decoded semantic labels RGBA-to-class color map (stored as raw JSON string per frame)
    "semantic_labels": Value("string"),
    
    # Camera projection and view transforms
    "camera_aperture": Sequence(Value("float32"), length=2),
    "camera_focal_length": Value("float32"),
    "camera_projection": Sequence(Value("float32"), length=16),      # Flat 4x4 matrix
    "camera_view_transform": Sequence(Value("float32"), length=16),  # Flat 4x4 matrix
    "camera_resolution": Sequence(Value("int32"), length=2),
    
    # 3D bounding box features (supports multiple objects per frame)
    "bbox_3d_x_min": Sequence(Value("float32")),
    "bbox_3d_y_min": Sequence(Value("float32")),
    "bbox_3d_z_min": Sequence(Value("float32")),
    "bbox_3d_x_max": Sequence(Value("float32")),
    "bbox_3d_y_max": Sequence(Value("float32")),
    "bbox_3d_z_max": Sequence(Value("float32")),
    "bbox_3d_transform": Sequence(Sequence(Value("float32"), length=16)), # List of flat 4x4 matrices
    "bbox_3d_semantic_id": Sequence(Value("int32")),
    "bbox_3d_class_name": Sequence(Value("string")),   # e.g. "picanol"/"colruyt"/"leanflow" per box
    "bbox_3d_occlusion": Sequence(Value("float32"))
})

def generator(path):
    rgb_dir = os.path.join(path, "rgb")
    depth_dir = os.path.join(path, "depth")
    sem_dir = os.path.join(path, "semantic")
    sem_labels_dir = os.path.join(path, "semantic_labels")
    bbox_dir = os.path.join(path, "bbox_3d")
    cam_dir = os.path.join(path, "camera")

    # Get sorted frame basenames based on rgb files
    frames = sorted([
        os.path.splitext(f)[0] 
        for f in os.listdir(rgb_dir) 
        if f.endswith(".png")
    ])

    for frame in frames:
        # 1. Resolve paths
        rgb_file = os.path.join(rgb_dir, f"{frame}.png")
        depth_file = os.path.join(depth_dir, f"{frame}.npy")
        sem_file = os.path.join(sem_dir, f"{frame}.png")
        sem_labels_file = os.path.join(sem_labels_dir, f"{frame}.json")
        bbox_file = os.path.join(bbox_dir, f"{frame}.json")
        cam_file = os.path.join(cam_dir, f"{frame}.json")

        # 2. Serialize raw depth array to bytes, keeping its actual shape -- not assumed
        #    equal to camera_resolution (they coincide today only because of the single-view
        #    depth sensor design; don't bake that coincidence into the schema).
        depth_arr = np.load(depth_file)
        depth_bytes = depth_arr.tobytes()
        depth_resolution = list(depth_arr.shape)

        # 3. Read semantic labels map as a raw JSON string
        with open(sem_labels_file, "r") as f:
            sem_labels_str = f.read()

        # 4. Parse camera matrix parameters from JSON
        with open(cam_file, "r") as f:
            cam_data = json.load(f)
        
        aperture = cam_data["cameraAperture"]
        focal_length = cam_data["cameraFocalLength"]
        projection = cam_data["cameraProjection"]
        view_transform = cam_data["cameraViewTransform"]
        resolution = cam_data["renderProductResolution"]

        # 5. Parse bounding boxes (dynamic list)
        with open(bbox_file, "r") as f:
            bbox_data = json.load(f)
            
        x_min, y_min, z_min = [], [], []
        x_max, y_max, z_max = [], [], []
        transforms = []
        semantic_ids = []
        class_names = []
        occlusions = []

        for box in bbox_data.get("data", []):
            x_min.append(box["x_min"])
            y_min.append(box["y_min"])
            z_min.append(box["z_min"])
            x_max.append(box["x_max"])
            y_max.append(box["y_max"])
            z_max.append(box["z_max"])
            # Flatten the 4x4 transform matrix to a 1D list of 16 floats
            flat_transform = [val for row in box["transform"] for val in row]
            transforms.append(flat_transform)
            semantic_ids.append(box["semanticId"])
            # .get() with a fallback: older generator output predates this field
            class_names.append(box.get("className", ""))
            occlusions.append(box["occlusionRatio"])

        yield {
            "rgb": rgb_file,
            "depth": depth_bytes,
            "depth_resolution": depth_resolution,
            "semantic": sem_file,
            "semantic_labels": sem_labels_str,
            "camera_aperture": aperture,
            "camera_focal_length": focal_length,
            "camera_projection": projection,
            "camera_view_transform": view_transform,
            "camera_resolution": resolution,
            "bbox_3d_x_min": x_min,
            "bbox_3d_y_min": y_min,
            "bbox_3d_z_min": z_min,
            "bbox_3d_x_max": x_max,
            "bbox_3d_y_max": y_max,
            "bbox_3d_z_max": z_max,
            "bbox_3d_transform": transforms,
            "bbox_3d_semantic_id": semantic_ids,
            "bbox_3d_class_name": class_names,
            "bbox_3d_occlusion": occlusions
        }

print(f"Loading dataset from: {dataset_dir}")
dataset = Dataset.from_generator(
    generator, 
    gen_kwargs={"path": dataset_dir}, 
    features=features
)

print("Uploading dataset to Hugging Face Hub (UItraviolet/cart_dataset)...")
dataset.push_to_hub("UItraviolet/cart_dataset", private=True)
print("Dataset upload completed successfully!")