---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html
---

# Replicator AWS Setup Instructions[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#replicator-aws-setup-instructions "Link to this heading")
## Getting started with AWS[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#getting-started-with-aws "Link to this heading")
Through this document you will learn how to generate synthetic data in AWS headlessly.
### AWS Requirements[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#aws-requirements "Link to this heading")
Here are the requirements for running Replicator on Amazon Web Services (AWS):
  1. An AWS account that is able to launch an EC2 instance with RTX GPU support.
  2. An AWS EC2 Instance with the following specifications:
>      * **Instance Type** : g5.xlarge or higher
>      * **AMI** : NVIDIA Omniverse GPU-Optimized AMI


### Setup[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/aws_setup.html#setup "Link to this heading")
Follow these steps below to launch an AWS EC2 instance:
  1. Create your Key Pair PEM file by following the eight steps in this [Key Pair Guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/get-set-up-for-amazon-ec2.html#create-a-key-pair).
Note
Follow these steps to prevent permission errors when trying to SSH into the AWS instance:
     * On Linux, remember to use `chmod 400 yourkey.pem` as instructed in the link above.
     * On Windows, right-click the `yourkey.pem` file and select **Properties** :
       1. Go to the **Security** tab and click **Advanced**.
       2. Click **Disable inheritance**.
       3. Set ownership of the file to the current user and give full permissions to only that user.
  2. From your AWS EC2 Console, click **Launch Instance** , in the section **Application and OS Images (Amazon Machine Image)** , search for “Omniverse”, and select the only AMI in the official Marketplace. The direct link to the AMI can be found here [NVIDIA Omniverse GPU-Optimized AMI](https://aws.amazon.com/marketplace/pp/prodview-4gyborfkw4qjs?sr=0-1&ref_=beagle&applicationId=AWSMPContessa).
> Note
> This AMI may not be visible to Hong Kong, Africa Cape Town, Middle East Bahrain, and Milan zones.
> ![AWS AMI selection screen for Omniverse GPU optimization](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_choose_ami.png)
  3. Scroll down to the **Instance Type** section and pick a GPU instance (g5.xlarge or higher). Click **Next: Configure Instance Details** at the bottom right corner.
> ![AWS EC2 instance type selection for GPU g5.xlarge](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_instance_type.png)
  4. In the **Key pair** (login) section, click Create new key pair to create a new pem file if you skipped step 1, else select an existing key pair.
> ![AWS key pair login selection during instance creation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_key_pair.png)
  5. In the **Network Settings** section, click Edit
> ![AWS network settings inbound security rules configuration](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_network_settings1.png)
  6. Next, set Inbound security groups rules to All traffic for “Type” and My IP for “Source type”.
> ![AWS network settings all traffic security group setup](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_network_settings2.png)
  7. Click **Add Storage** at the bottom right. Set the **Root** volume size to 100GB or more.
> Note
> Replicator can operate on an Instance with 30GB, but you may run out of space when running a large scene.
> ![AWS storage configuration for 100GB root volume](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_configure_storage.png)
  8. Click **Review and Launch** , then **Launch**. Point to your existing PEM key or create a new PEM key; creating a new PEM key will save the key in your browser Download folder). Select **Acknowledge**.
Click **Launch Instance** , which will produce a link (e.g. _i-0edc9523b2fff2e44_). Click the instance link.
> ![AWS instance launch summary and confirmation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_summary.png)
  9. Now you are ready to connect to our instance.
For more information as to how to connect you can follow this link: [Connect to your instance](https://docs.aws.amazon.com/AWSEC2/latest/WindowsGuide/connecting_to_windows_instance.html)
  10. Follow these steps to SSH into the AWS instance:
    1. As shown above, on Linux or Windows, run this command from where your PEM key folder is. Replace `ubuntu@ec2-52-53-177-94.us-west-1.compute.amazonaws.com` with your instance:
> 
```
$ ssh -i "yourkey.pem" ubuntu@ec2-52-53-177-94.us-west-1.compute.amazonaws.com

```
Copy to clipboard
    1. On Windows, you can also use Putty to SSH:
Convert your PEM key to a Putty key. See [Connecting to Your Linux Instance from Windows Using PuTTY](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/putty.html) for more details.
Put your instance name above in the host name:
> ![PuTTY SSH client connection interface](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_putty1.png)
Select **SSH/Auth** , point **Browse** to your converted Putty key, then click **Open** and **Yes**. You should be able to SSH into the AWS instance now.
> ![PuTTY SSH authentication key selection dialog](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_aws_putty2.png)
  11. Proceed to [Deploy to Cloud](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/container_setup.html#headless-container).


