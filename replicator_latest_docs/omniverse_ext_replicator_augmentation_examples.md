---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html
---

# Data Augmentations[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#data-augmentations "Link to this heading")
## Pixellation[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#pixellation "Link to this heading")
`output = upsample(boxFilter(input))`
The data augmentation blurs the image with a box filter first where each output value is the average of the pixel values in the filter window resulting in a downsampled version of the input image. A resizing operation is needed to restore the resolution using a nearest-neighbour upsampling. This results in the same color value copied over in the original image in the corresponding blur window. In summary, the box filter is slided across the image with each pixel value changed to the average in the filter window.
![Pixellation augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_pixellation.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugPixellateExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugPixellateExp", kernelSize=8))
#augment annotator product
ldr_color = ldr_color.augment("AugPixellateExp")

```
Copy to clipboard
## Motion Blur[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#motion-blur "Link to this heading")
`output = conv2D(input, blurfilter)`
Motion blur is simulated using a 2D kernel (also called filter) but the user can choose the angle and direction — whether it is going forward or backward — as well as the kernel size. The kernel is then used to convolve the 2D image to produce motion blur like effects.
![Motion blur augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_motion_blur.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugMotionBlurExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugMotionBlurExp", alpha=0.7, kernelSize=11))
#augment annotator product
ldr_color = ldr_color.augment("AugMotionBlurExp")

```
Copy to clipboard
## Glass Blur[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#glass-blur "Link to this heading")
`output = glassBlur(input)`
To simulate glass blur, we choose a delta parmeter, which captures the maximum window size inside which two pixel locations are chosen and their color values swapped.
![Glass blur augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_glass_blur.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugGlassBlur", augmentation=rep.Augmentation.from_function(rep.aug_glass_blur, data_out_shape=(-1, 4), delta=rep.random.choice([1, 2, 3, 4])))
#augment annotator product
ldr_color = ldr_color.augment("AugGlassBlur")

```
Copy to clipboard
## Rand Conv[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#rand-conv "Link to this heading")
`output = conv2D(input, randomFilter)`
The image is convolved with a random k x k filter generated on the fly. The weights are sampled from classic He-initialisation used in deep learning. It provides various color changes the image can undergo.
![Random convolution augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_random_convolution.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugConv2dExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugConv2dExp", alpha=0.7, kernelWidth=3))
#augment annotator product
ldr_color = ldr_color.augment("AugConv2dExp")

```
Copy to clipboard
## RGB ↔ HSV[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#rgb-hsv "Link to this heading")
Converts the standard RGB color palette into a polar HSV color palette. Various augmentations can then be applied in this space and converted back to RGB.
![RGB to HSV color space conversion](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_rgb_to_hsv.png)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugRGBtoHSV", augmentation=rep.Augmentation.from_function(rep.aug_rgb_to_hsv, data_out_shape=(-1, 4)))

rep.AnnotatorRegistry.register_augmentation(name="AugHSVtoRGB", augmentation=rep.Augmentation.from_function(rep.aug_hsv_to_rgb, data_out_shape=(-1, 4)))

#augment annotator product
ldr_color = ldr_color.augment("AugRGBtoHSV")
ldr_color = ldr_color.augment("AugHSVtoRGB")

```
Copy to clipboard
## CutMix[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#cutmix "Link to this heading")
`output = ( 1 - mask) inputImage + mask randomImage`
The augmentation takes in a random rectangular patch from another image and superimposes it on the input image. The rectangular patch is encoded in a binary mask where the pixels belonging to the rectangle have a mask value of 1 and 0 otherwise.
![CutMix augmentation with rectangular patch](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_cut_mix.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugCutMixExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugCutMixExp", folderpath="/folder/to/random/ims/"))
#augment annotator product
ldr_color = ldr_color.augment("AugCutMixExp")

```
Copy to clipboard
## Random Blend[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#random-blend "Link to this heading")
`output = ( 1 - randomFactor) inputImage + randomFactor randomImage`
Two images are blended in with a random blending factor to generate an image that contains the data from both images. This is basically linearly interpolating two images.
![Random blend augmentation between two images](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_random_blend.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugImgBlendExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugImgBlendExp", folderpath="/folder/to/random/ims/"))
#augment annotator product
ldr_color = ldr_color.augment("AugImgBlendExp")

```
Copy to clipboard
## Background Randomization[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#background-randomization "Link to this heading")
`output = ( 1 - backgroundAlpha) inputImage + backgroundAlpha randomImage`
The blank background of an image is replaced with an arbitrary image. The alpha channel is used to combine the images, with precise alpha compositing at the edges between foreground and background. Provided a folder of background images of arbitrary size, each execution of the node samples a preloaded image from the folder.
![Background randomization augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_random_blend.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugBgRandExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugBgRandExp", folderpath="/folder/to/background/ims/"))
#augment annotator product
ldr_color = ldr_color.augment("AugBgRandExp")

```
Copy to clipboard
## Contrast[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#contrast "Link to this heading")
`output = inputImage*(1-enhancement)+mean(inputImage)*enhancement`
Standard color augmentation to alter image contrast.
![Contrast augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_contrast.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugContrastExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugContrastExp", contrastFactorIntervalMin=0.2,contrastFactorIntervalMax=5))
#augment annotator product
ldr_color = ldr_color.augment("AugContrastExp")

```
Copy to clipboard
## Brightness[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#brightness "Link to this heading")
`output = inputImage +brightnessFactor`
Standard color augmentation to alter image brightness.
![Brightness augmentation effect](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_brightness.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugBrightness", augmentation=rep.Augmentation.from_function(rep.aug_brightness, data_out_shape=(-1, 4), seed=31, brightness_factor=rep.distribution.uniform(-100, 100)))
#augment annotator product
ldr_color = ldr_color.augment("AugBrightness")

```
Copy to clipboard
## Rotate[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#rotate "Link to this heading")
`output = rotate(inputImage, angle)`
Random rotation of the image about its center.
![Image rotation augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_rotate.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugRotateExp",augmentation=rep.Augmentation.from_node("omni.replicator.core.AugRotateExp", rotateDegrees=40.0))
#augment annotator product
ldr_color = ldr_color.augment("AugRotateExp")

```
Copy to clipboard
## Crop and Resize[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#crop-and-resize "Link to this heading")
`output = resize(crop(inputImage, xmin, xmax, ymin, xmax))`
Random crop of the image in each x and y direction, and resize (i.e. zoom) back to original shape using warp.
![Crop and resize augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_resize.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugCropResizeExp", augmentation=rep.Augmentation.from_node("omni.replicator.core.AugCropResizeExp", minPercent=0.5))
#augment annotator product
ldr_color = ldr_color.augment("AugCropResizeExp")

```
Copy to clipboard
## Adjust Sigmoid[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#adjust-sigmoid "Link to this heading")
`output = exp(1+gain*(cutoff-inputImage))^-1`
Provided a cutoff and a gain, adjust the sigmoid of the image.
![Adjust sigmoid augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_adjust_sigmoid.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugAdjustSigmoid", augmentation=rep.Augmentation.from_function(rep.aug_adjust_sigmoid, data_out_shape=(-1, 4), cutoff=0.5, gain=rep.distribution.uniform(5, 15)))
#augment annotator product
ldr_color = ldr_color.augment("AugAdjustSigmoid")

```
Copy to clipboard
## Speckle Noise[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#speckle-noise "Link to this heading")
`output = inputImage + (sigma * noiseArray ⊙ inputImage)`
Provided a noise scaling factor sigma, add speckle noise to each pixel of the image.
![Speckle noise augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_speckle_noise.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugSpeckleNoise", augmentation=rep.Augmentation.from_function(rep.aug_speckle_noise, data_out_shape=(-1, 4),sigma=rep.distribution.uniform(0, 5)))
#augment annotator product
ldr_color = ldr_color.augment("AugSpeckleNoise")

```
Copy to clipboard
## Shot Noise[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/augmentation_examples.html#shot-noise "Link to this heading")
`output = inputImage + noiseArray ⊙ √(inputImage)/√(sigma)`
Provided a noise scaling factor sigma, add shot noise to each pixel of the image.
![Shot noise augmentation](https://docs.omniverse.nvidia.com/extensions/latest/_images/replicator_augmentation_shot_noise.gif)

```
#sample code:
#register augmentation
rep.AnnotatorRegistry.register_augmentation(name="AugShotNoise",augmentation=rep.Augmentation.from_function(rep.aug_shot_noise, data_out_shape=(-1, 4), sigma=rep.distribution.normal(20, 5)))
#augment annotator product
ldr_color = ldr_color.augment("AugShotNoise")

```
Copy to clipboard
**Notes**
  * All augmentations with suffix -Exp do not support replicator distribution sampling (e.g. `rep.distribution.normal(20, 5)`. For these nodes, either specify the distribution parameters if provided or sample externally.


