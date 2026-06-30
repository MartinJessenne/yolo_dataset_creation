---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html
---

# Replicator[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#replicator "Link to this heading")
Omniverse Replicator is a framework for developing custom synthetic data generation pipelines and services. Developers can generate physically accurate 3D synthetic data that serves as a valuable way to enhance the training and performance of AI perception networks used in [autonomous vehicles](https://developer.nvidia.com/blog/using-synthetic-data-to-address-novel-viewpoints-for-autonomous-vehicle-perception/), [robotics](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html) and [intelligent video analytics applications](https://developer.nvidia.com/metropolis).
Replicator is designed to easily integrate with existing pipelines using open-source standards like [Universal Scene Description (USD)](https://developer.nvidia.com/usd), [PhysX](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/index.html "\(in Omni Physics\)"), and [Material Definition Language (MDL)](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html "\(in Omniverse Materials and Rendering\)"). An extensible registry of annotators and writers is available to address specific requirements for training AI models.
Omniverse Replicator is exposed as a set of extensions, content, and examples in [Isaac Sim](https://docs.isaacsim.omniverse.nvidia.com/latest/index.html). For a detailed presentation of Replicator, check out [this talk](https://reg.rainfocus.com/flow/nvidia/gtcspring2022/aplive/page/ap/session/1638329095495001V74p).
The [Replicator Tutorials](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#replicator-tutorials) section below covers high level aspects of getting started developing with Synthetic Data and Replicator.
## Theory Behind Training with Synthetic Data[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#theory-behind-training-with-synthetic-data "Link to this heading")
To train a deep neural network (DNN) for perception tasks, large sets of annotated images are needed. The DNNs are then trained for the perception tasks such as detection, classification and segmentation. To achieve the required KPIs, hyperparameters are fine-tuned through an iterative process. In most cases, this may not be sufficient, requiring a “data-centric” approach where new and diverse types of data may be needed to increase the desired performance of the model. However, collecting and annotating new data manually is an expensive process.
![_images/ext_replicator-theory_behind_sdg-typical_DNN_training_02.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator-theory_behind_sdg-typical_DNN_training_02.png)
In such scenarios where data is limited, restricted, or simply doesn’t exist, [synthetic data](https://blogs.nvidia.com/blog/what-is-synthetic-data/) can help bridge that gap for developers in a cost-effective manner. Furthermore, synthetic data generation also addresses challenges related to long tail anomalies and edge use cases that are impossible to collect in the real-world.
Some more difficult perception tasks require annotations of images that are extremely difficult to do manually (e.g. images with occluded objects). Programmatically generated synthetic data can address this very effectively since all generated data is perfectly labeled. The programmatic nature of data generation also allows the creation of non-standard annotations and indirect features that can be beneficial to DNN performance.
![_images/ext_replicator-theory_behind_sdg-replicator-addresses.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator-theory_behind_sdg-replicator-addresses.png)
As described above, synthetic data generation has many advantages. However, there are a set of challenges that need to be addressed for it to be effective.
## Closing the Simulation to Real Gap[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#closing-the-simulation-to-real-gap "Link to this heading")
To bridge the gap between simulation and reality in synthetic data generation, we must address two distinct challenges known as the domain gap: the appearance gap and the content gap.
>   * **Appearance Gap:** This pertains to disparities at the pixel level between real and synthetic images. Such differences can arise from variations in object intricacy, materials used, or limitations of the rendering system employed in synthetic data creation.
>   * **Content Gap:** This encompasses variations in the domains themselves. Factors such as the quantity of objects present in a scene, the diversity in their types and placements, and other contextual elements contribute to the content gap between synthetic and real-world data.
> 

Closing these gaps is vital to ensure that synthetic datasets accurately reflect real-world scenarios, enabling more effective training of AI models. Addressing the appearance gap involves refining rendering techniques and material representation, while mitigating the content gap requires enhancing the diversity and complexity of simulated scenes. By narrowing these gaps, we can improve the fidelity and applicability of synthetic data for training AI systems across various domains.
Overcoming domain gaps is crucial, and domain randomization plays a key role in this endeavor. By expanding the range of synthetic data generated, we aim to closely mirror real-world scenarios, including rare occurrences. This broader dataset distribution enables neural networks to better grasp the full complexity of the problem, enhancing their ability to generalize effectively.
Addressing the appearance gap involves leveraging high-fidelity 3D assets and advanced rendering techniques like ray-tracing or path-tracing. Physically based materials, such as those defined with the MDL material language, contribute to realism. Additionally, validated sensor models and randomized parameters aid in narrowing the appearance gap further.
To ensure content relevance, a diverse pool of assets tailored to the scene is indispensable. Platforms like Omniverse offer connectors to various 3D applications, facilitating asset integration. Developers can also devise tools to generate varied domain scenes pertinent to their specific context.
![_images/ext_replicator-theory_behind_sdg-iterative_learning.png](https://docs.omniverse.nvidia.com/extensions/latest/_images/ext_replicator-theory_behind_sdg-iterative_learning.png)
However, training with synthetic data introduces complexity, as it’s challenging to ascertain whether the randomizations adequately represent the real domain. Testing the network on real data is essential to validate its performance. Prioritizing a data-centric approach allows for fine-tuning the dataset before considering adjustments to model architecture or hyperparameters, addressing any performance issues effectively.
## Core Components[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#core-components "Link to this heading")
Replicator is composed of six components that enable you to generate synthetic data:
>   * **Semantics Schema Editor** Semantic annotations (data “of interest” pertaining to a given mesh) are required to properly use the synthetic data extension. These annotations inform the extension about what objects in the scene need bounding boxes, pose estimations, etc… The Semantics Schema Editor provides a way to apply these annotations to prims on the stage through a UI.
>   * **Visualizer** The Replicator visualizer enables you to visualize the semantic labels for 2D/3D bounding boxes, normals, depth and more.
>   * **Randomizers:** Replicator’s randomization tools allow developers to easily create domain randomized scenes, quickly sampling from assets, materials, lighting, and camera positions.
>   * **Omni.syntheticdata:** Omni.syntheticdata is the lowest level component of the Replicator software stack, and it will ship as a built-in extension in all future versions of the Omniverse Kit SDK. The omni.syntheticdata extension provides low level integration with the RTX renderer, and the OmniGraph computation graph system.This is the component that powers the computation graphs for Replicator’s Ground Truth extraction Annotators, passing Arbitrary Output Variables or AOVs from the renderer through to the Annotators.
>   * **Annotators:** The annotation system itself ingests the AOVs and other output from the omni.syntheticdata extension to produce precisely labeled annotations for DNN training.
>   * **Writers:** Writers process the images and other annotations from the annotators, and produce DNN specific data formats for training. Writers can output to local storage, over the network to cloud based storage backends such as SwiftStack, and in the future we will provide backends for live on-GPU training, allowing generated data to stay on the GPU for training and avoiding any additional IO at all.
> 

Throughout generation of a dataset the most common workflow is to randomize a scene, select your annotators, and then write to your desired format. However, if needed for more customization you have access to omni.synthetic data.
## API documentation and Changelogs[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#api-documentation-and-changelogs "Link to this heading")
Python API Documentation for Omniverse Replicator is in the [Omniverse Replicator Python API documentation](https://docs.omniverse.nvidia.com/py/replicator).
Changelogs for Omniverse Replicator are available at this [link](https://docs.omniverse.nvidia.com/py/replicator/1.9.8/source/extensions/omni.replicator.core/docs/CHANGELOG.html).
## Replicator Examples on Github[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#replicator-tutorials "Link to this heading")
We now offer convenient [Replicator Examples on Github](https://github.com/NVIDIA-Omniverse/synthetic-data-examples). There are snippets, full scripts, and USD scenes where content examples are needed. This repo will grow as we add to it.
## Courses and Videos[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#courses-and-videos "Link to this heading")
  * Tutorial: [Defect Detection Model Trained on Synthetic Data](https://www.nvidia.com/en-us/on-demand/playlist/playList-827595a0-3c57-4c7f-af9f-1c80c6292d09/)
  * Course: [Synthetic Data Generation for Training Computer Vision Models](https://courses.nvidia.com/courses/course-v1:DLI+S-OV-10+V1/)


## Replicator Tutorials[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#id3 "Link to this heading")
To help you get started with Replicator, we have created a handful of hands-on tutorials.
  * [Getting started with Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html)
  * [Core functionalities - "Hello World" of Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/basic_functionalities.html)
  * [Camera Examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/camera_examples.html)
  * [Running Replicator headlessly](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html)
  * [Adding semantics with Semantics Schema Editor and programmatically](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/semantics_schema_editor.html)
  * [Interactive live visualization](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/visualization.html)
  * [Randomizers examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/randomizer_details.html)
  * [Data Augmentation](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html)
  * [Replicator Materials](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_materials.html)
  * [Annotating with Transparent Materials](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotations_with_transparency.html)
  * [Annotators information](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/annotators_details.html)
  * [Visualizing output folder with annotated data programmatically](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html)
  * [Using existing 3D assets with Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/using_existing_assets.html)
  * [Using Replicator with a fully developed scene](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/apis_with_fully_developed_scene.html)
  * [Using physics with Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/physics_example.html)
  * [Randomizing appearance, placement and orientation of existing 3D assets with a built-in writer](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/shrubs_and_worker_example.html)
  * [Writer Examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/writer_examples.html)
  * [Create a custom writer](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/custom_writer.html)
  * [Distribution Examples](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html)
  * [Rendering with Subframes](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html)
  * [I/O Optimization Guide](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/io_guidelines.html)
  * [Advanced Scattering](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/advanced_scattering.html)
  * [Working with Layers](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/replicator_using_layers.html)
  * [Replicator YAML](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_workflow.html)
  * [Replicator YAML Manual and Syntax Guide](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html)


## Replicator On Cloud[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#replicator-on-cloud "Link to this heading")
Instructions are given for setting up Replicator on cloud below.
  * [Container Setup](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html)
  * [AWS Setup](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html)


## Known Issues[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#known-issues "Link to this heading")
  * Materials or textures will sometimes not be loaded in time for capture when in `RTX - Real-Time` mode. If this occurs, you can increase the interval between captures by setting the `/omni/replicator/RTSubframes` flag (default=3). To set in Python, `carb.settings.get_settings().set(<new value>)`. Similarly, capture speed can be increased if no materials are randomized by setting the value to its minimum of 1.
  * Errors in annotator visualization and data generation may occur when running on a system with multi-GPU. To disable multi-GPU, launch with the `--/renderer/multiGpu/enabled=false` flag.
  * In scenes with a large number of 3D bounding boxes, the visualizer flickers due to the rendering order of the boxes. This rendering issue is purely aesthetic and will not have any effect when writing the data.
  * Tiled Sensor artifacts present in RGB output when assets are positioned on the up axis at 0.0 units.


## Questions and Help[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html#questions-and-help "Link to this heading")
  * Synthetic Data Forums: [Log feature requests or workflow issues and get expert guidance from Omniverse developers and the community on the Omniverse forums](https://forums.developer.nvidia.com/c/omniverse/synthetic-data-generation-sdg/595)
  * Discord: [Join the Omniverse Discord community and our Omniverse developers to ask questions and share tips and tricks](https://discord.gg/nvidiaomniverse)


