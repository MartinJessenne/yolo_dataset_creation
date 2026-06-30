---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html
---

# Getting started with Omniverse Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#getting-started-with-omniverse-replicator "Link to this heading")
Omniverse Replicator is created as an Omniverse Kit extension and conveniently distributed through Isaac Sim and any Kit app.
Generating synthetic data with Omniverse Replicator is a two step process. The first step brings assets into the scene, defines and registers randomizers, annotators and writers. It also defines the event triggers for randomizers to execute. Under the hood this first step builds [OmniGraph](https://docs.omniverse.nvidia.com/extensions/latest/ext_omnigraph.html) nodes to execute these steps efficiently. Once the OmniGraph nodes are built, the second step executes these nodes to generate the data, annotations and writes output to the disk in the desired form. Replicator APIs abstract these complexities from the users.
## Setting up the Script Editor[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#setting-up-the-script-editor "Link to this heading")
To get started with the Replicator API, you can use the [Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_script-editor.html). The video below shows you how to find it in a Kit application. Note that the [Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_script-editor.html) extension is available in all Omniverse applications through the Extension manager.
Note
If you are using [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html), you will find the script editor under the top tab **Window** -> **Script Editor**. Make sure to enable it and it will pop up. It will look identical to the one shown in the gif below.
![Replicator Script Editor location and interface](https://docs.omniverse.nvidia.com/extensions/latest/_images/Replicator_script_editor.gif)
## Running and Previewing Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running-and-previewing-replicator "Link to this heading")
Running a script (see [Core Functions - “Hello World” of Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html#hello-world) for an example) through the [Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_script-editor.html) builds a replicator OmniGraph, but does not run the actual execution or logic. You can see the generated graph in the stage under Replicator/SDGPipeline. Once an Omni.Replicator graph has been created, typically by running a script in the Script Editor, data generation can be controlled through the Replicator menu item. Click on Replicator –> Run as shown in the figure below to run the generation, or Replicator -> Stop to stop it. Clicking on Replicator –> Preview performs a single iteration of randomizations and prevents data from being written to disk.
![Replicator run preview menu controls](https://docs.omniverse.nvidia.com/extensions/latest/_images/Replicator_run_preview.gif)
Note
You can do this programatically too, using `rep.orchestrator.run()`. For more information refer to API docs.
## Scripts for Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#scripts-for-replicator "Link to this heading")
The Replicator Extension comes with a couple of scripts that will be useful for your development experience. For example, in the scripts folder you will find our implementation of BasicWriter or Kitti writer, which you might use as a template for your own development. Below you can see where you will find the scripts.
![Replicator scripts folder location and discovery in file browser](https://docs.omniverse.nvidia.com/extensions/latest/_images/Replicator_scripts_discovery.gif)
In the gif we use VS Code, but instead you can click the folder icon and it will open the folder where the scripts are.
