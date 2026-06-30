---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html
---

# Visualizing the output folder from Basic Writer()[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html#visualizing-the-output-folder-from-basic-writer "Link to this heading")
After generating data, it is always useful to visualize the outputs. In this tutorial, we give you a couple of helper functions to visualize the output of basic writer.
## Generating all data types available with Basic Writer()[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html#generating-all-data-types-available-with-basic-writer "Link to this heading")
First generate data, you can use any script you have built with replicator that uses the Basic_writer. For the simplest example, follow the steps of the [Core Functions - “Hello World” of Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#hello-world). To write all data types available by the Basic_writer, replace the initialize the writer with all the data flags set to True.

```
writer.initialize(
    output_dir="out_dir_test_visualization",
    rgb=True,
    bounding_box_2d_tight=True,
    bounding_box_2d_loose=True,
    semantic_segmentation=True,
    instance_segmentation=True,
    distance_to_camera=True,
    distance_to_image_plane=True,
    bounding_box_3d=True,
    occlusion=True,
    normals=True,
)

```
Copy to clipboard
For simplicity, below is the modified Hello World script, ready to generate data:

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(0, 0, 1000))
    render_product = rep.create.render_product(camera, (1024, 1024))

    torus = rep.create.torus(semantics=[('class', 'torus')] , position=(0, -200 , 100))
    sphere = rep.create.sphere(semantics=[('class', 'sphere')], position=(0, 100, 100))
    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(100, -200 , 100) )

    with rep.trigger.on_frame(num_frames=10):
        with rep.create.group([torus, sphere, cube]):
            rep.modify.pose(
                position=rep.distribution.uniform((-100, -100, -100), (200, 200, 200)),
                scale=rep.distribution.uniform(0.1, 2))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(
        output_dir="out_dir_test_visualization",
        rgb=True,
        bounding_box_2d_tight=True,
        bounding_box_2d_loose=True,
        semantic_segmentation=True,
        instance_segmentation=True,
        distance_to_camera=True,
        distance_to_image_plane=True,
        bounding_box_3d=True,
        occlusion=True,
        normals=True,
    )

    writer.attach([render_product])

    rep.orchestrator.run()

```
Copy to clipboard
Now that you have generated the dataset, which you will find in HOME/out_dir_test_visualization if you didn’t modify the output folder above. There you will find all of the anotations from replicator. Before we are able to visualize the output we need a couple of helper functions.
## Helper visualization functions[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html#helper-visualization-functions "Link to this heading")
The functions bellow help you visualize the output. These functions are simple visualization helpers. For bounding boxes it colors and labels the bounding box, for segmentation it colors the output and shows the semantic tag, and for depth it shows the depth with colors representing the depth.

```
import asyncio
from dis import dis
import os
import json

import hashlib
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches


'''
Takes in the data from a specific label id and maps it to the proper color for the bounding box
'''
def data_to_colour(data):
    if isinstance(data, str):
        data = bytes(data, "utf-8")
    else:
        data = bytes(data)
    m = hashlib.sha256()
    m.update(data)
    key = int(m.hexdigest()[:8], 16)
    r = ((((key >> 0) & 0xFF) + 1) * 33) % 255
    g = ((((key >> 8) & 0xFF) + 1) * 33) % 255
    b = ((((key >> 16) & 0xFF) + 1) * 33) % 255

    # illumination normalization to 128
    inv_norm_i = 128 * (3.0 / (r + g + b))

    return (int(r * inv_norm_i) / 255, int(g * inv_norm_i) / 255, int(b * inv_norm_i) / 255)

'''
Takes in the path to the rgb image for the background, then it takes bounding box data, the labels and the place to store the visualization. It outputs a colorized bounding box.
'''
def colorize_bbox_2d(rgb_path, data, id_to_labels, file_path):

    rgb_img = Image.open(rgb_path)
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(rgb_img)
    for bbox_2d in data:
        id = bbox_2d["semanticId"]
        color = data_to_colour(id)
        labels = id_to_labels[str(id)]
        rect = patches.Rectangle(
            xy=(bbox_2d["x_min"], bbox_2d["y_min"]),
            width=bbox_2d["x_max"] - bbox_2d["x_min"],
            height=bbox_2d["y_max"] - bbox_2d["y_min"],
            edgecolor=color,
            linewidth=2,
            label=labels,
            fill=False,
        )
        ax.add_patch(rect)

    plt.legend(loc="upper left")

    plt.savefig(file_path)

'''
Takes the depth data and colorizes it.
'''
def colorize_depth(depth_data):
    near = 0.01
    far = 100
    depth_data = np.clip(depth_data, near, far)
    # depth_data = depth_data / far
    depth_data = (np.log(depth_data) - np.log(near)) / (np.log(far) - np.log(near))
    # depth_data = depth_data / far
    depth_data = 1.0 - depth_data

    depth_data_uint8 = (depth_data * 255).astype(np.uint8)

    return Image.fromarray(depth_data_uint8)


'''
Takes the segmentation images, the color for the labels and the output path to visualize the segmentation output
'''

def create_segmentation_legend(segmentation_img, color_to_labels, file_path):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(segmentation_img)

    color_patch_list = []
    for color, labels in color_to_labels.items():
        color_val = eval(color)
        color_patch = patches.Patch(color=[i / 255 for i in color_val], label=labels)
        color_patch_list.append(color_patch)

    ax.legend(handles=color_patch_list)

    plt.savefig(file_path)

```
Copy to clipboard
## Visualizing the Output[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html#visualizing-the-output "Link to this heading")
**RGB Visualization**
The output of replicator comes with RGB, there is no need to do anything extra to visualize it. However, for the rest of the samples we will use it as a background. This is how to load it:

```
out_dir = PATH_TO_REPLICATOR_OUTPUT_DIR
rgb = "rgb_0.png" # to be changed by you
rgb_path = os.path.join(out_dir, rgb_file_name)
rgb_image = Image.open(rgb_path)

```
Copy to clipboard
**Normal Visualization**
Normals is very similart to RGB, the PNG is already stored as nomals_n.png

```
normals_file_name = "normals_0.png"
normals_image = Image.open(os.path.join(out_dir, normals_file_name))
normals_image.save(os.path.join(vis_out_dir, "normals.png"))

```
Copy to clipboard
**Bounding Box 2D tight and loose**
For this one we use the bounding_box_2d_loose_N.npy. We load that numpy array, then we get the label from the bounding_box_2d_loose_labels_N.json. For tight bounding boxes, change the names to bounding_box_2d_tight_labels_N.json and bounding_box_2d_tight_labels_N.npy. Otherwise the code is identical. Note here we use the visulatization functions from above.

```
bbox2d_loose_file_name = "bounding_box_2d_loose_0.npy"
data = np.load(os.path.join(out_dir, bbox2d_loose_file_name))

# Check for labels
bbox2d_loose_labels_file_name = "bounding_box_2d_loose_labels_0.json"
with open(os.path.join(out_dir, bbox2d_loose_labels_file_name), "r") as json_data:
    bbox2d_loose_id_to_labels = json.load(json_data)

# colorize and save image
colorize_bbox_2d(rgb_path, data, bbox2d_loose_id_to_labels, os.path.join(vis_out_dir, "bbox2d_loose.png"))

```
Copy to clipboard
**Distance to Camera or Image plane**
Here you need the numpy array distance_to_camera_N.npy or distance_to_image_plane_N.npy depending on whether you want camera or image plane distance respectively. Then, use the helper function colorize_depth.

```
distance_to_camera_file_name = "distance_to_camera_0.npy"
distance_to_camera_data = np.load(os.path.join(out_dir, distance_to_camera_file_name))
distance_to_camera_file_name = np.nan_to_num(distance_to_camera_data, posinf=0)

distance_to_camera_image = colorize_depth(distance_to_camera_data)
distance_to_camera_image.save(os.path.join(vis_out_dir, "distance_to_camera.png"))

```
Copy to clipboard
**Instance or semantic Segmentation**
Here we pass the instance_segmentation_N.png and instance_segmentation_mapping_N.json. The png gives us the labeling of each pixel, the json file maps it. For semantic segmentation replace the file name with semantic instead of instance

```
instance_seg_file_name = "instance_segmentation_0.png"
instance_seg_img = Image.open(os.path.join(out_dir, instance_seg_file_name))

# Check labels
instance_seg_labels_file_name = "instance_segmentation_mapping_0.json"
with open(os.path.join(out_dir, instance_seg_labels_file_name), "r") as json_data:
    instance_seg_color_to_labels = json.load(json_data)

create_segmentation_legend(
    instance_seg_img, instance_seg_color_to_labels, os.path.join(vis_out_dir, "instance_seg.png"))

```
Copy to clipboard
