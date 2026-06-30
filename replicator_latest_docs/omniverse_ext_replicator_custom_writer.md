---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html
---

# Custom Writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html#custom-writer "Link to this heading")
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html#learning-objectives "Link to this heading")
Replicator comes with a basicWriter which provides labeled output. Although the basicWriter is generic enough, Replicator provides a way to create a custom writer to address custom output format requirements. Through this sample shows the process to create a custom writer.
## Making a custom writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html#making-a-custom-writer "Link to this heading")
To implement a custom writer we will need to implement the class Writer. For the specifics of the implementation, a detailed description is below.
### Implementing a Writer[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html#implementing-a-writer "Link to this heading")
To create a custom Write, first we have to implement a Writer class detailed in [API documentation](https://docs.omniverse.nvidia.com/py/replicator) .
In this example we are creating a 2D bounding box writer that is only writing the bounding box information for our desired class, in this case `worker`, for your use case, you might have different classes you are interested in.
First let’s initialize the writer. In this case the only mandatory parameter is the output directory. Notice here the use of `annotators`. Annotators are the types of ground truth annotations created by Replicator.
Also note that controlling and filtering semantics can be further explored in [Adding Semantics to a Scene](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#semantic).

```
def __init__(
    self,
    output_dir,
    rgb: bool = True,
    bounding_box_2d_tight: bool = False,
    image_output_format="png",
):
    self._output_dir = output_dir
    self._backend = BackendDispatch({"paths": {"out_dir": output_dir}})
    self._frame_id = 0
    self._image_output_format = image_output_format

    self.annotators = []

    # RGB
    if rgb:
        self.annotators.append(AnnotatorRegistry.get_annotator("rgb"))

    # Bounding Box 2D
    if bounding_box_2d_tight:
        self.annotators.append(AnnotatorRegistry.get_annotator("bounding_box_2d_tight",
                                                            init_params={"semanticTypes": ["class"]}))

```
Copy to clipboard
Then we have a helper function. Here we check that the bounding box meets minimum size criteria.

```
def check_bbox_area(self, bbox_data, size_limit):
    length = abs(bbox_data['x_min'] - bbox_data['x_max'])
    width = abs(bbox_data['y_min'] - bbox_data['y_max'])

    area = length * width
    if area > size_limit:
        return True
    else:
        return False

```
Copy to clipboard
Lastly we have the most important function `write`. In this case it takes in the data, checks if in `data` dictionary is `rgb` and `bounding_box_2d_tight`. If it is in there then we extract the bounding box information and the labels. We then go through each of the labels, if the label is `worker`, then we write the data in coco like format after we check the size.

```
def write(self, data):
    if "rgb" in data and "bounding_box_2d_tight" in data:
        bbox_data = data["bounding_box_2d_tight"]["data"]
        id_to_labels = data["bounding_box_2d_tight"]["info"]["idToLabels"]

        for id, labels in id_to_labels.items():
            id = int(id)

            if 'worker' in labels:

                target_bbox_data = {'x_min': bbox_data['x_min'], 'y_min': bbox_data['y_min'],
                                    'x_max': bbox_data['x_max'], 'y_max': bbox_data['y_max']}

                if self.check_bbox_area(target_bbox_data, 0.5):
                    width = int(abs(target_bbox_data["x_max"][0] - target_bbox_data["x_min"][0]))
                    height = int(abs(target_bbox_data["y_max"][0] - target_bbox_data["y_min"][0]))

                    if width != 2147483647 and height != 2147483647:
                        filepath = f"rgb_{self._frame_id}.{self._image_output_format}"
                        self._backend.write_image(filepath, data["rgb"])

                        bbox_filepath = f"bbox_{self._frame_id}.json"

                        coco_bbox_data = {"x": int(target_bbox_data["x_max"][0]),
                                        "y": int(target_bbox_data["y_max"][0]),
                                        "width": width,
                                        "height": height}

                        buf = io.BytesIO()
                        buf.write(json.dumps(coco_bbox_data).encode())
                        self._backend.write_blob(bbox_filepath, buf.getvalue())

```
Copy to clipboard
Here is the complete class implemented.

```
import time
import asyncio
import json
import io

import omni.kit
import omni.usd
import omni.replicator.core as rep

from omni.replicator.core import Writer, AnnotatorRegistry, BackendDispatch

class WorkerWriter(Writer):
    def __init__(
        self,
        output_dir,
        rgb: bool = True,
        bounding_box_2d_tight: bool = False,
        image_output_format="png",
    ):
        self._output_dir = output_dir
        self._backend = BackendDispatch({"paths": {"out_dir": output_dir}})
        self._frame_id = 0
        self._image_output_format = image_output_format

        self.annotators = []

        # RGB
        if rgb:
            self.annotators.append(AnnotatorRegistry.get_annotator("rgb"))

        # Bounding Box 2D
        if bounding_box_2d_tight:
            self.annotators.append(AnnotatorRegistry.get_annotator("bounding_box_2d_tight",
                                                                init_params={"semanticTypes": ["class"]}))

    def check_bbox_area(self, bbox_data, size_limit):
        length = abs(bbox_data['x_min'] - bbox_data['x_max'])
        width = abs(bbox_data['y_min'] - bbox_data['y_max'])

        area = length * width
        if area > size_limit:
            return True
        else:
            return False

    def write(self, data):
        if "rgb" in data and "bounding_box_2d_tight" in data:
            bbox_data = data["bounding_box_2d_tight"]["data"]
            id_to_labels = data["bounding_box_2d_tight"]["info"]["idToLabels"]

            for id, labels in id_to_labels.items():
                id = int(id)

                if 'worker' in labels:

                    target_bbox_data = {'x_min': bbox_data['x_min'], 'y_min': bbox_data['y_min'],
                                        'x_max': bbox_data['x_max'], 'y_max': bbox_data['y_max']}

                    if self.check_bbox_area(target_bbox_data, 0.5):
                        width = int(abs(target_bbox_data["x_max"][0] - target_bbox_data["x_min"][0]))
                        height = int(abs(target_bbox_data["y_max"][0] - target_bbox_data["y_min"][0]))

                        if width != 2147483647 and height != 2147483647:
                            filepath = f"rgb_{self._frame_id}.{self._image_output_format}"
                            self._backend.write_image(filepath, data["rgb"])

                            bbox_filepath = f"bbox_{self._frame_id}.json"

                            coco_bbox_data = {"x": int(target_bbox_data["x_max"][0]),
                                            "y": int(target_bbox_data["y_max"][0]),
                                            "width": width,
                                            "height": height}

                            buf = io.BytesIO()
                            buf.write(json.dumps(coco_bbox_data).encode())
                            self._backend.write_blob(bbox_filepath, buf.getvalue())

        self._frame_id += 1

```
Copy to clipboard
### End to end example[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html#end-to-end-example "Link to this heading")
Following the set up steps in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up), you can copy the script below in the editor. After running the script from the editor run replicator following [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running). For a deeper understanding on the randomization piece of the script check out [Randomizing appearance, placement and orientation of an existing 3D assets with a built-in writer](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html#shrub). For more examples of writers, you can check the script defining the BasicWriter and other writers in replicators script folder. To find that folder follow the steps shown in [Scripts for Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#scripts).

```
import time
import asyncio
import json
import io

import omni.kit
import omni.usd
import omni.replicator.core as rep

from omni.replicator.core import Writer, AnnotatorRegistry, BackendDispatch


WORKER = 'omniverse://localhost/NVIDIA/Assets/Characters/Reallusion/Worker/Worker.usd'
PROPS = 'omniverse://localhost/NVIDIA/Assets/Vegetation/Shrub'
ENVS = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Outdoor/Puddles.usd'
SURFACE = 'omniverse://localhost/NVIDIA/Assets/Scenes/Templates/Basic/display_riser.usd'


class WorkerWriter(Writer):
    def __init__(
        self,
        output_dir,
        rgb: bool = True,
        bounding_box_2d_tight: bool = False,
        image_output_format="png",
    ):
        self._output_dir = output_dir
        self._backend = BackendDispatch({"paths": {"out_dir": output_dir}})
        self._frame_id = 0
        self._image_output_format = image_output_format

        self.annotators = []

        # RGB
        if rgb:
            self.annotators.append(AnnotatorRegistry.get_annotator("rgb"))

        # Bounding Box 2D
        if bounding_box_2d_tight:
            self.annotators.append(AnnotatorRegistry.get_annotator("bounding_box_2d_tight",
                                                                init_params={"semanticTypes": ["class"]}))

    def check_bbox_area(self, bbox_data, size_limit):
        length = abs(bbox_data['x_min'] - bbox_data['x_max'])
        width = abs(bbox_data['y_min'] - bbox_data['y_max'])

        area = length * width
        if area > size_limit:
            return True
        else:
            return False

    def write(self, data):
        if "rgb" in data and "bounding_box_2d_tight" in data:
            bbox_data = data["bounding_box_2d_tight"]["data"]
            id_to_labels = data["bounding_box_2d_tight"]["info"]["idToLabels"]

            for id, labels in id_to_labels.items():
                id = int(id)

                if 'worker' in labels:

                    target_bbox_data = {'x_min': bbox_data['x_min'], 'y_min': bbox_data['y_min'],
                                        'x_max': bbox_data['x_max'], 'y_max': bbox_data['y_max']}

                    if self.check_bbox_area(target_bbox_data, 0.5):
                        width = int(abs(target_bbox_data["x_max"][0] - target_bbox_data["x_min"][0]))
                        height = int(abs(target_bbox_data["y_max"][0] - target_bbox_data["y_min"][0]))

                        if width != 2147483647 and height != 2147483647:
                            filepath = f"rgb_{self._frame_id}.{self._image_output_format}"
                            self._backend.write_image(filepath, data["rgb"])

                            bbox_filepath = f"bbox_{self._frame_id}.json"

                            coco_bbox_data = {"x": int(target_bbox_data["x_max"][0]),
                                            "y": int(target_bbox_data["y_max"][0]),
                                            "width": width,
                                            "height": height}

                            buf = io.BytesIO()
                            buf.write(json.dumps(coco_bbox_data).encode())
                            self._backend.write_blob(bbox_filepath, buf.getvalue())

        self._frame_id += 1


rep.WriterRegistry.register(WorkerWriter)

with  rep.new_layer():

    def env_props(size=50):
        instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS), size=size, mode='point_instance')
        with instances:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
                rotation=rep.distribution.uniform((-90, -180, 0), (-90, 180, 0)),
            )
        return instances.node


    def worker():
        worker = rep.create.from_usd(WORKER, semantics=[('class', 'worker')])

        with worker:
            rep.modify.semantics([('class', 'worker')])
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 0, -500), (500, 0, 500)),
                rotation=rep.distribution.uniform((-90, -45, 0), (-90, 45, 0)),
            )
        return worker


    rep.randomizer.register(env_props)
    rep.randomizer.register(worker)

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    # Setup the static elements
    env = rep.create.from_usd(ENVS)
    table = rep.create.from_usd(SURFACE)

    # Setup camera and attach it to render product
    camera = rep.create.camera(
        focus_distance=800,
        f_stop=0.5
    )

    # Setup randomization
    with rep.trigger.on_frame(num_frames=10):
        rep.randomizer.env_props(10)
        rep.randomizer.worker()
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-500, 200, 1000), (500, 500, 1500)), look_at=table)

    render_product = rep.create.render_product(camera, resolution=(1024, 1024))

    # Initialize and attach writer
    # writer = rep.WriterRegistry.get("OmniWriter")
    writer = rep.WriterRegistry.get("WorkerWriter")
    out_dir = "custom_writer_output"
    writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

```
Copy to clipboard
