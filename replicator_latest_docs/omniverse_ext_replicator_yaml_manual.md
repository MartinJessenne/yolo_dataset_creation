---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html
---

# Replicator YAML Manual[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html#replicator-yaml-manual "Link to this heading")
Replicator YAML is built on a new syntax that is easy to transfer from yaml to python. New features in `omni.replicator.core` do not require modification of Replicator YAML to integrate.
## Syntax[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html#syntax "Link to this heading")

```
group_name:
        module_name.function_name:
                func_arg1: fun_arg_val_1
                func_arg2: func_arg_val_2

```
Copy to clipboard
One valid example looks like this:

```
camera:
   create.camera:
      focus_distance: 800
      f_stop: 0.5

```
Copy to clipboard
There is some syntax that is worth noting:
  1. There is always a `group_name` for a block of code. This is for conveniently referring to the code in other places. For example:



```
camera:
   create.camera:
      focus_distance: 800
      f_stop: 0.5

render_product:
   create.render_product:
      camera: camera
      resolution: [512, 512]

```
Copy to clipboard
In render_product block, it refers to camera block.
  2. The syntax of a function is always `module_name.function_name`. The parser will only parse it as a function if that key meets that syntax.
  3. Function argument can be nested with functions. For example:



```
camera:
   create.camera:
      focus_distance: 800
      f_stop: 0.5
         position:
            distribution.uniform:
               lower: [-500, 0, -500]
               upper: [500, 0, 500]

```
Copy to clipboard
  4. If a function does not take any argument, the value would just be null.


A special kind of block is registering custom function to `omni.replicator.core`. The python syntax looks like this:

```
import omni.replicator.core as rep

PROPS = 'omniverse://your-nucleus-server/NVIDIA/Assets/Vegetation/Shrub'

def env_props(size=50):
   instances = rep.randomizer.instantiate(rep.utils.get_usd_files(PROPS), size=size, mode='point_instance')

   return instances.node

rep.randomizer.register(env_props)

# Calling the function
rep.randomizer.env_props(size=10)

```
Copy to clipboard
The equivalent yaml looks like this:

```
register_env_props:
   randomizer.register:
      env_props:
         inputs:
            size: 50
         instances:
            randomizer.instantiate:
               paths:
                  utils.get_usd_files:
                     path: "omniverse://your-nucleus-server/NVIDIA/Assets/Vegetation/Shrub"
               size: size # Default size, can be replaced
               mode: "point_instance"

# Calling the function
load_env_props:
   randomizer.env_props: null

```
Copy to clipboard
It’s worth noting here that the syntax of a registering block is always like this:

```
group_name:
   randomizer.register:  # Always randomizer.register
      register_func_name:
         inputs:  # This indicates the input names and default value of the args that you can replace
            input_arg_name: default_arg_val

         rand_group_name: # This group is only with the scope of `register_func_name`
            module.func_name:
               arg_name: input_arg_name  # This refers to the arg_name in inputs block

```
Copy to clipboard
The `with` statement is another special block. The syntax looks like this:

```
camera:
   create.camera:
      focus_distance: 800
      f_stop: 0.5

modify_camera:
   with.camera:  # The syntax is with.group_name for group name you created eariler
      modify.pose:
         position:
            distribution.uniform:
               lower: [-500, 200, 100]
               upper: [500, 500, 1500]
      modify.semantics:
         semantics: [["class", "camera"]]

      # Within a with statement, multiple parallel functions can be called.

```
Copy to clipboard
## Inheritance[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/yaml_manual.html#inheritance "Link to this heading")
First, you have to specify under the block `profiles` to let the parser know what parent yaml files you want to inherit from. For example:

```
profiles:
   - PATH_YAML_FILE_1
   - PATH_YAML_FILE_2

```
Copy to clipboard
Inside your main yaml file, if you want to inherit a group from `YAML_FILE_1`, you should have a `inherit` keyword inside that group. For example:

```
objs:
   inherit: flying_objs
   randomizer.instantiate:
      size: 5
      mode: "reference"

```
Copy to clipboard
And inside `YAML_FILE_1`, it looks like:

```
flying_objs:
   randomizer.instantiate:
      paths: PATH_TO_ASSETS
      mode: "scene_instance"

```
Copy to clipboard
Notice that the parser will combine the two group (`objs` and `flying_objs`) together. If there is a key that is both present in `objs` and `flying_objs`, the value of `objs` will overwrite value of `flying_objs`. So the final yaml looks like:

```
objs:
   randomizer.instantiate:
      size: 5
      paths: PATH_TO_ASSETS
      mode: "reference"

```
Copy to clipboard
When accessing group names from parent yaml, you can access group names defined in parent yaml. For example:

```
flying_objs:
   randomizer.instantiate:
      paths: warehouse_assets

profiles:
   - /warehouse_assets.yaml

```
Copy to clipboard
And inside warehouse_assets.yaml, it looks like this:

```
warehouse_assets:
   - omniverse://your-nucleus-server/NVIDIA/Assets/Isaac/2022.1/Isaac/Props/Dolly/dolly.usd
   - omniverse://your-nucleus-server/NVIDIA/Assets/Isaac/2022.1/Isaac/Props/Flip_Stack/flip_stack.usd

```
Copy to clipboard
**Global Parameters**
In the old composer feature, there is a feature called Global Parameters. For example:

```
# global parameters
obj_rot: Uniform((0, 0, 0), (360, 360, 360))

obj_horiz_fov_loc: Uniform(-1, 1)
obj_vert_fov_loc: Uniform(-0.7, 1)

obj_metallicness: Uniform(0.1, 0.8)
obj_reflectance: Uniform(0.1, 0.8)

```
Copy to clipboard
Any groups that are missing these keywords will have these as their parameters.
In the Replicator YAML this is integrated with the inheritance syntax, since the building blocks are basically functions. For example:

```
objs:
   randomizer.instantiate:
      path: PATH_TO_ASSETS
   size:
      distribution.uniform:
            lower: 5
            upper: 15

modify_objs:
   with_objs:
      inherit: general_modification

general_modification:
   modify.pose_camera_relative:
      distance:
            distribution.uniform:
               lower: 4
               upper: 20
      camera: camera
      render_product: render_products
      horizontal_location:
            distribution.uniform:
               lower: -1
               upper: 1
      vertical_location:
            distribution.uniform:
               lower: -0.7
               upper: 1

```
Copy to clipboard
Where `PATH_TO_ASSETS` is defined in other yaml file.
**Limitations of Inheritance Syntax**
  1. Only blocks defined in a group can be inherited.
  2. Current inheritance syntax does not support duplicate group names.


