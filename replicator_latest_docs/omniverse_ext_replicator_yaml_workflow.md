---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html
---

# Replicator YAML[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#replicator-yaml "Link to this heading")
Replicator YAML is a streamlined workflow for creating Synthetic Data with Replicator and Omniverse. The format uses the [YAML format](https://en.wikipedia.org/wiki/YAML), a data interchange format. This tutorial will guide you through generating datasets with Replicator YAML.
You can find more Replicator YAML examples on our [Synthetic Data Examples Github](https://github.com/NVIDIA-Omniverse/synthetic-data-examples).
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#learning-objectives "Link to this heading")
This tutorial includes the following:
  1. Replicator YAML Overview
  2. Running YAML scripts
  3. Example YAML scripts
  4. YAML Manual and Syntax Guide


## Replicator YAML Overview[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#replicator-yaml-overview "Link to this heading")
Replicator YAML is one of the four major workflows for creating synthetic data using Replicator. It focuses on workflows where simplicity, portability, and cloud are favored. As the name implies, scripts are written using YAML which is parsed into Replicator scripts and run to generate synthetic data.
Replicator YAML is intended for:
  * Low or no code users, situations where scripts are easily edited by non technical experts.
  * Where scripts need a high level of portability.
  * Cloud use cases.


## Running YAML Scripts[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#running-yaml-scripts "Link to this heading")
Running a Replicator YAML script is largely the same as the traditional replicator script workflow. YAML scripts can be run using the UI through the _Script Editor_ in Code, Isaac Sim, or other Kit Apps. Alternatively, YAML scripts can also be run headlessly, where the GUI is not shown and the app runs the script as a background process.
**Enable the YAML extension**
First, check whether the **Replicator YAML Extension** is enabled in your Kit App. With Code, you may need to manually enable the extension to use YAML with Replicator. Open the _Extensions_ window using **Menu > Window > Extensions**. Type, **‘YAML’** into the search field, and you should see the **‘REPLICATORYAML’** extension. Verify it is enabled. Enable it, if it is not.
![../_images/ext_replicator_yaml_extension.jpg](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator_yaml_extension.jpg)
**Running a script using the UI**
For both Code and Isaac Sim, when the UI mode is enabled:
  1. Open Isaac Sim, Code or other Kit App with the UI enabled mode.
  2. Open the _Script Editor_ from **Menu > Window > Script Editor**
  3. Paste the script from below in the _Script Editor_. Please change the file path details where the corresponding YAML file is stored.
  4. Click on the **Run** button to execute the script.
  5. Use the **Replicator Menu** for needed actions such as **Preview** , **Step**..etc.



```
from omni.replicator.replicator_yaml import parse
parser = parse(r"path_to_YAML_file")

```
Copy to clipboard
**Running a script Headlessly**
Running replicator scripts headlessly is covered in [Running Replicator Headlessly](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#headless-example). However there are some differences for using YAML files as arguments.

```
.\omni.code.bat --no-window --/omni/replicator/replicatorYaml/yamlPath=<path_to_yaml_file>

```
Copy to clipboard
For Isaac Sim, running the Replicator YAML workflow in headless mode is done the following way:
![../_images/ext_replicator_isaacsim_yaml_args.jpg](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator_isaacsim_yaml_args.jpg)
  1. Specify path of the YAML file as an **Extra Args** as follows:

```
--/omni/replicator/replicatorYaml/yamlPath=<path_to_yaml_file>

```
Copy to clipboard
  2. Following additional arguments can also be specified

```
"/omni/replicator/replicatorYaml/nucleusServer"
"/omni/replicator/replicatorYaml/rootDir"

```
Copy to clipboard


For containers similar changes are required. In section 8, of the [Deploy to Cloud](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html#headless-container) page, you would instead use this command:

```
./startup.sh --allow-root --no-window --/omni/replicator/replicatorYaml/yamlPath=<path_to_yaml_file>

```
Copy to clipboard
## Example YAML Scripts[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#example-yaml-scripts "Link to this heading")
We have numerous Replicator YAML examples available. All are available on the [Synthetic Data Examples Github](https://github.com/NVIDIA-Omniverse/synthetic-data-examples).
  * Tutorial Basic Functionality
  * Tutorial Randomizer Colors
  * Tutorial Randomizer Dome Light
  * Tutorial Randomizer Instantiate
  * Tutorial Randomizer Light
  * Tutorial Randomizer Materials
  * Tutorial Randomizer Pose
  * Tutorial Randomizer Scatter Surface
  * Tutorial Randomize Textures
  * Multiple Cameras With Basic Writer
  * Randomize Camera Position List
  * Randomize Camera Position Uniformly


Below is the `Tutorial Basic Functionality` YAML script.

```
stage_unit_setting:
   settings.set_stage_meters_per_unit:
      meters_per_unit: 1

stage_up_axis_setting:
   settings.set_stage_up_axis:
      up_axis: "Z"

light:
   create.light:
      light_type: "distant"

camera:
   create.camera:
      position: [10, 0, 0]

render_product:
   create.render_product:
      camera: camera
      resolution: [1024, 1024]

torus:
   create.torus:
      semantics: [["class", "torus"]]
      position: [1, 0, -2]

sphere:
   create.sphere:
      semantics: [["class", "sphere"]]
      position: [1, 0, 1]

cube:
   create.cube:
      semantics: [["class", "cube"]]
      position: [1, 1, -2]

group:
   create.group:
      items: [torus, sphere, cube]

trigger:
   trigger.on_frame:
      max_execs: 10

with_trigger:
   with.trigger:
      with.group:
         modify.pose:
         position:
            distribution.uniform:
               lower: [-1, -1, -1]
               upper: [2, 2, 2]
         scale:
            distribution.uniform:
               lower: 0.1
               upper: 2

writer:
   writers.get:
      name: "BasicWriter"
      init_params:
         output_dir: "_output_yaml/TutorialBasicFunctionality/"
         rgb: True
         bounding_box_2d_tight: True

writer_attach:
   writer.attach:
      render_products: render_product

```
Copy to clipboard
When run, the outputs should look like:
![../_images/ext_replicator_isaacsim_script_editor_yaml.jpg](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator_isaacsim_script_editor_yaml.jpg)
## Replicator YAML Manual and Syntax Guide[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html#replicator-yaml-manual-and-syntax-guide "Link to this heading")
The [Replicator YAML Manual](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html#replicator-yaml-manual) is a guide on the Replicator YAML syntax and structure. Topics discussed are:
  * Syntax
  * Valid Examples
  * Functions
  * Blocks
  * Inheritance
  * Global Parameters


