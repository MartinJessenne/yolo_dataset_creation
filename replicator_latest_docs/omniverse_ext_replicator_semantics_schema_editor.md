---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html
---

# Adding Semantics to a Scene[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#adding-semantics-to-a-scene "Link to this heading")
## Semantics Schema Editor[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#semantics-schema-editor "Link to this heading")
In order to generate annotations such as segmentation and bounding boxes, semantic information such as the class for different objects in the scene must be specified. The Semantics Schema Editor tool allows user to assign semantic labels to those objects.
Semantics Schema Editor is an Omniverse extension, accessible via Extension manager. Go to Window->Extensions to find the extension. Then find the Semantics Schema Editor as shown bellow to enable it. There are two ways to assign semantic labels to objects.
Note
If you are using [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html), you will find the semantic schema editor extension already downloaded. To use it, click on Replicator tab in the top left and click on Semantics schema Editor.
![../_images/Replicator_basic_labeling.gif](https://docs.omniverse.nvidia.com/extensions/latest/_images/Replicator_basic_labeling.gif)
**Apply semantic data on selected objects**
[![../_images/isaac_camera_semantic_schema_editor_0.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/isaac_camera_semantic_schema_editor_0.png) ](https://docs.omniverse.nvidia.com/extensions/latest/_images/isaac_camera_semantic_schema_editor_0.png)
As the title suggests, select a group of objects and then for each object, specify the Type field as class and the Data field as the semantic label.
**Apply semantic data using prim names**
[![../_images/isaac_camera_semantic_schema_editor_1.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/isaac_camera_semantic_schema_editor_1.png) ](https://docs.omniverse.nvidia.com/extensions/latest/_images/isaac_camera_semantic_schema_editor_1.png)
A heuristic-based approach is used to assign semantic labels to different objects in the scene using their prim names as references. To avoid including specialization prefixes or suffixes in the semantic label, acronyms such as SM (Static Mesh), SK (Skeletal Mesh), MI (Material Instance), etc., the user can specify a list of prefixes and suffixes to be removed from the prim’s name before assigning the resulting semantic label value. The label type of the semantic key-value pair can be specified by the user in the Label type field, by default being class.
There are 3 types of writing behaviors that can be chosen: New - where a new semantic key-value is added to the object, Overwrite - where if the semantic key already exists its value will be overwritten, Skip - where if the key already exists, the prim will be skipped.
In the Prim types filter field the user can specify which USD object types will be taken into consideration when applying semantic labels. If the field is left empty, all USD object types will be considered.
By selecting Remove numerical ending any numerical values will be removed from the end of the prim name before further processing it. For example, if the prim name is SM_Car_T_01, the resulting name will be SM_Car_T.
The values in the Remove prefixes and Remove suffixes are the prefixes and suffixes that will be removed from the prim name. For example, if the prim name is SM_Car_T and the Remove prefixes field contains SM, the resulting name will be Car_T. If the Remove suffixes field also contains T, the resulting name will be Car.
If the Apply cumulatively checkbox is ticked each prefix and suffix is re-taken into consideration after each removal. For example, if the prim name is SM_L_Car_T_Mat and the Remove prefixes field contains L and SM and the resulting name will be Car_T_Mat. If the Remove suffixes field also contains Mat and T, the resulting name will be Car.
If the Remove separators checkbox is ticked, the underscores (_) from the resulting name are removed. For example Large_Car will become LargeCar.
The Preview checkbox enables a “simulation” of the changes that will be applied to the scene. If the checkbox is ticked, the semantic labels will not be applied to the scene but will be shown in the Output field.
The Apply to selection chooses to apply the rules to the Selected prims or the whole Stage.
The Add button will perform the semantic labeling based on the rules specified in the fields. The Remove button will clear any semantic data of the given Label type and Prim types filter, whereas Remove All removes all semantic data (equivalent to Remove with Label type and Prim types filter set to empty).
## Programmatically defining Semantics[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#programmatically-defining-semantics "Link to this heading")
To add semantics you need to modify the semantics of the mesh, or reference you want label. In the code below we show how to add a semantic class, but you could have any other semantics you wanted. You would just modify the tuple.

```
rep.modify.semantics([('class', 'avocado')])

```
Copy to clipboard
Bellow a script moving around an avocado from the NVIDIA library of assets and adding the semantic class avocado. To run it follow the same instructions as in [Getting started with Omniverse Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#getting-started).

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    # Defining a plane to place the avocado
    plane = rep.create.plane(scale=100, visible=True)

    # Defining the avocado starting from the NVIDIA residential provided assets. Position and semantics of this asset are modified.
    AVOCADO = 'omniverse://localhost/NVIDIA/Assets/ArchVis/Residential/Food/Fruit/Avocado01.usd'
    avocado = rep.create.from_usd(AVOCADO)
    with avocado:
        rep.modify.semantics([('class', 'avocado')])
        rep.modify.pose(
                position=(-50, 0, -50),
                rotation=(-90,-45, 0)
                )

    # Setup camera and attach it to render product
    camera = rep.create.camera(focus_distance=80)
    render_product = rep.create.render_product(camera, resolution=(1024, 1024))

    # Creating 30 frames with the camera changing positions around the avocado
    with rep.trigger.on_frame(num_frames=30):
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-20, 20, 80), (20, 50, 100)), look_at=avocado)

```
Copy to clipboard
## Semantics Filtering[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#semantics-filtering "Link to this heading")
Semantics in Omniverse are defined as key-value pairs. More specifically, a Semantic Type paired with a Semantic Value. Eg. “class”: “car”
By specifying a semantic filter predicate, complex filtering can be performed to extract only the desired groundtruth. Semantic Filters are applied globally using the following syntax:

```
from omni.syntheticdata import SyntheticData
SyntheticData.Get().set_instance_mapping_semantic_filter(semantic_filter_predicate)

```
Copy to clipboard
The grammar of the semantic filter predicate is described below:
`semToken = [a-zA-Z0-9_]+`
`semLabel = [!]?(semToken)`
`semLabelConjunction = (semLabel)(&(semLabel))*`
`semLabelDisjunction = (semLabelConjunction)(\|(semLabelConjunction))*`
`semType = [!]?(semToken):(semLabelDisjunction)`
`semTypeConjunction = (semType)(,(semType))*`
`semDisjunctiveNormalForm = (semTypeConjunction)(;(semTypeConjunction))*`
**Examples**
Filter for class: vehicles and persons
`"class:vehicle|person"` or `"class:vehicle; class:person"`
Retrieve all semantics with class label except trees
`"class:*&!tree"`
Filter for class: vehicle and retrieve vehicle_type
`"class:vehicle,vehicle_type:*"`
Filter for class: vehicles but not trucks
`"class:vehicle,vehicle_type:!truck"`
Filter for class: vehicles that also have class: sports_car
`"class:vehicle&sports_car"`
Filter for class: vehicles but exclude class: sports_car
`"class:vehicle&!sports_car"`
Include all semantics
`"*:*"`
Retrieve all semantics with a class label
`"class:*"`
Exclude class: sports_car
`"!class:sports_car"`
Exclude class: sports_car and class:person
`"!class:sports_car&person"`
Exclude semantic type vehicle_type
`"vehicle_type:!*"`
## Visualize Semantics[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html#visualize-semantics "Link to this heading")
See the [Visualizing Semantic Data](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/visualization.html#visualization) tutorial for how to use and visualize semantics applied with this extension.
