---
source: https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html
---

# Distribution Examples[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#distribution-examples "Link to this heading")
Within replicator there are multiple off-the-shelf distributions to control the appearance or selection of data. Often they are combined with Randomizers.
Below are a few examples of the use of distributions applied on a scene using Replicator APIs.
## Learning Objectives[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#learning-objectives "Link to this heading")
Through this page you will see some highlighted distributions and how to use them. However, for all distribution information available consult the [API documentation](https://docs.omniverse.nvidia.com/py/replicator) .
## Set up[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#set-up "Link to this heading")
Each of the distributions shown below are standalone scripts that can be run following the set up described in [Setting up the Script Editor](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#set-up) and [Running and Previewing Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/getting_started.html#running).
## Uniform Distribution[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#uniform-distribution "Link to this heading")
The uniform distribution selects a number within a range uniformly. If 1 to 10 is given, any value between those numbers can be selected with an equal probability.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(1.0, 2000, 0.0), look_at=(0,0,0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    for i in range(50):
        rep.create.sphere(semantics=[('class', 'sphere')], scale=(0.1, 0.1, 0.1))

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.modify.pose(
                position=rep.distribution.uniform((-500, 50, -500), (500, 50, 500)))
        return shapes.node

    rep.randomizer.register(get_shapes)

    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_ReplicatorTutorial_DistributionUniform", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    # Setup randomization
    with rep.trigger.on_frame(num_frames=1):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Normal Distribution[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#normal-distribution "Link to this heading")
Returns a value based on a normal distribution. Mean and Standard Deviation values are used as inputs.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(501.0, 500, 500.0), look_at=(500.0,0,500.0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    for i in range(50):
        rep.create.sphere(semantics=[('class', 'sphere')], scale=(0.1, 0.1, 0.1))

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.modify.pose(
                position=rep.distribution.normal((500.0, 0.0, 500.0), (10, 0.0, 50)))
        return shapes.node

    rep.randomizer.register(get_shapes)

    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_ReplicatorTutorial_DistributionNormal", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    # Setup randomization
    with rep.trigger.on_frame(num_frames=1):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Choice Distribution[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#choice-distribution "Link to this heading")
The choice distribution selects data from a list. If no weights are given, all weights are assumed equal, and one choice from the list is selected each time.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(1.0, 2000, 0.0), look_at=(0,0,0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    #Red, Green, Blue, White Colors
    choices=[(1.0,0.0,0.0),(0.0,1.0,0.0),(0.0,0.0,1.0),(1.0,1.0,1.0)]
    weights = [1.0,0.5,0.25,0.1]

    for i in range(20):
        rep.create.sphere(semantics=[('class', 'sphere')], scale=(0.1, 0.1, 0.1))

    def get_shapes():
        shapes = rep.get.prims(semantics=[('class', 'cube'), ('class', 'sphere')])
        with shapes:
            rep.modify.pose(position=rep.distribution.uniform((-500, 0.0, -500), (500, 0.0, 500)))
            rep.randomizer.color(colors=rep.distribution.choice(choices,weights))
        return shapes.node

    rep.randomizer.register(get_shapes)

    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_ReplicatorTutorial_DistributionChoice", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    # Setup randomization
    with rep.trigger.on_frame(num_frames=10):
        rep.randomizer.get_shapes()

```
Copy to clipboard
## Sequence Distribution[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#sequence-distribution "Link to this heading")
Iterates through a sequence of data in order. When it reaches the end of the sequence, it will loop. This example shows three positions assigned to the cube each frame, iterating in sequence. When the sequence reaches the end, it will loop, as demonstrated by the output on frames 4, 5 and 6.

```
import omni.replicator.core as rep

with rep.new_layer():

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    camera = rep.create.camera(position=(500, 500, 500), look_at=(0,0,0))

    cube = rep.create.cube(semantics=[('class', 'cube')],  position=(0, 0, 0))
    render_product  = rep.create.render_product(camera, (1024, 1024))

    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir="_ReplicatorTutorial_DistributionSequence", rgb=True, bounding_box_2d_tight=True)
    writer.attach([render_product])

    # 6 frames to show looping of the sequence
    with rep.trigger.on_frame(num_frames=6):
        with cube:
            rep.modify.pose(position=rep.distribution.sequence([(0.0, 0.0, 200.0), (0.0, 200.0, 0.0), (200.0, 0.0, 0.0)]))

```
Copy to clipboard
## Combining Distributions[#](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/distribution_examples.html#combining-distributions "Link to this heading")
You can combine distributions to gain greater control over your data. For example, a choice distribution choosing from other distributions.

```
import omni.replicator.core as rep

# Add Default Light
distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

with rep.trigger.on_frame():
    with rep.create.cube():
        rep.modify.pose(
        position=rep.distribution.choice([
            rep.distribution.uniform((0., 0., 0.), (10., 10., 10.)),
            rep.distribution.normal((100., 100., 100.), (50., 50., 50.))
        ])
    )

```
Copy to clipboard
