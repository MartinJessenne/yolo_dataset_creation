---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html
---

# Deploy to Cloud[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html#deploy-to-cloud "Link to this heading")
Replicator is offered as a container that runs locally or on NVIDIA RTX equipped Amazon Web Services (AWS) instances. This cloud-based workload provides the latest RTX graphics and performance to any desktop system without requiring local NVIDIA RTX GPUs.
Note
Deploy to cloud is in its early stages and is expected to mature in both ease of deployment as well as accessability throughout the Omniverse Platform. For now however the process is manual and the instructions are below. If you have trouble or concerns, please make your voice heard on the [Omniverse Forums](https://forums.developer.nvidia.com/c/omniverse/synthetic-data-generation-sdg)
## Container Setup Options[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html#container-setup-options "Link to this heading")
We have the following options available.  
| Cloud Environment  | Link  |  
| --- | --- |  
| AWS  | [Replicator AWS Setup Instructions](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#aws-setup)  |  
## Container Deployment[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html#container-deployment "Link to this heading")
This section describes how to run the Replicator container remotely.
**Steps:**
  1. Connect to the machine via SSH or use your local terminal.
>      * See [Replicator AWS Setup Instructions](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#aws-setup) for a AWS instructions.
  2. Run the command below to confirm your GPU driver version (i.e., 470+).
> 
```
$ nvidia-smi

```
Copy to clipboard
  3. Get access to the [Replicator Container](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/omniverse-replicator) using your NVIDIA Developer Program credentials.
  4. Generate your [NGC API Key](https://docs.nvidia.com/ngc/ngc-overview/index.html#generating-api-key).
  5. Use the command line to log in to NGC before pulling the Replicator container.
> 
```
$ docker login nvcr.io
Username: $oauthtoken
Password: <Your NGC API Key>
WARNING! Your password will be stored unencrypted in /home/username/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store
Login Succeeded

```
Copy to clipboard
  6. Pull the Replicator container:
> 
```
$ docker pull nvcr.io/nvidia/omniverse-replicator:1.4.7-r1

```
Copy to clipboard
  7. Run the Replicator container with an interactive Bash session:
> Note
> Notice the flag “-v” in the console command below. This is to map a volume from the container to the instance. It is important, since this is where the data will be stored. For more info on volumes see this link [Storage Volumes](https://docs.docker.com/storage/volumes/). If you don’t want to map anything you can use [Docker Copy](https://docs.docker.com/engine/reference/commandline/cp/) from within the container. To move data out of the instance into your machine you can use [SCP](https://linuxize.com/post/how-to-use-scp-command-to-securely-transfer-files/).
> 
```
$ docker run --gpus all --entrypoint /bin/bash -it -v /PATH/TO/STORE/DATA/IN/INSTANCE:/_output/ nvcr.io/nvidia/omniverse-replicator:1.4.7-r1

```
Copy to clipboard
  8. Within the interactive session in the container you are ready to run Omniverse Replicator. Create your own Replicator script to run, or alternately, you can use the script shown in: [Running Replicator Headlessly](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/headless_example.html#headless-example) . With the following command:
> 
```
./startup.sh --allow-root --no-window --/omni/replicator/script=test.py

```
Copy to clipboard
> Note 

Basic text editing can be added to the container by running:
    
> 
```
apt-get update
apt-get install vim
vi test.py

```
Copy to clipboard
> To visualize the output data, you can utilize the following instructions detailed on programmatic visualization doc [Visualizing the output folder from Basic Writer()](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/programmatic_visualization.html#programmatic-visualization). If you want to visualize live, we recommend putting the functions of that doc and running a jupyter notebook from the instance.
> The first time loading Replicator will take a while, less than 5 minutes, for the shaders to be cached. Subsequent runs in the container will be faster. Once closing the container you will lose the caching. To accelerate your process go to [Replicator Container](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/omniverse-replicator) where we show how to store the cached shaders.
> Note
> Known Issue: Application shutdown may sometimes crash, but integrity of datasets is unaffected.
  9. Getting content into the container:
> In order to generate good synthetic data you will need access to 3D content. In this section we will show you how you can get access to content. There are three ways to get content into the container:
>      * [Nucleus](https://docs.omniverse.nvidia.com/nucleus/latest/index.html "\(in Omniverse Nucleus\)") enterprise .
>      * [Nucleus Cloud](https://developer.nvidia.com/nvidia-omniverse-platform/nucleus-cloud-eap).
>      * S3 buckets with your content.
> For more information on the first two, please explore their instructions pages and/or enterprise support [Omniverse ETS](https://www.nvidia.com/en-us/omniverse/enterprise/support/).
> For S3 bucket, here is a sample snippet of how you can bring in some content from a public s3 bucket to your script.
> 
```
import omni.replicator.core as rep

with rep.new_layer():

    stage = omni.usd.get_context().get_stage()

    # Load in example asset from S3
    path ="http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Vegetation/Plant_Tropical/Agave.usd"
    agave = rep.create.from_usd(path)

    camera = rep.create.camera(focus_distance=500,f_stop=4)
    render_product  = rep.create.render_product(camera, (1024, 1024))

    # Initialize and attach writer
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_asset_test", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    with rep.trigger.on_frame(num_frames=10):
        with camera:
            rep.modify.pose(position=rep.distribution.uniform((-500, 200, -500), (500, 500, 500)), look_at=(0,0,0))
        with agave:
            rep.modify.pose(rotation=rep.distribution.uniform((-90,0, 0), (-90, 0, 0)))

    rep.orchestrator.run()

```
Copy to clipboard


