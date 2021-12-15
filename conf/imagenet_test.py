# Imagenet experiment
import numpy as np
from Experiments.Passive import *
from Stimuli.Images import *
from core.Behavior import *
stim = dj.create_virtual_module('stimuli.py', 'lab_stimuli')

# define session parameters
session_params = {
    'trial_selection'       : 'randperm',
    'setup_conf_idx'        : 2,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

conditions = []
print('empty conditions')

#define params that are same across trials
rng = np.random.default_rng(seed=0)
min_blank = 300
extra_blank = 200

key = {
    'image_class'          : 'imagenet',
    'presentation_time'    : 1000,                        # (ms) image duration
    'intertrial_duration'   : 0,
}

# define train stimulus conditions
images = rng.permutation((stim.ImageImagenet() & 'image_id < 20').fetch('image_id'))
print(images)
blanks = min_blank + extra_blank * rng.random(len(images))
print(blanks)

for img, gap in zip(images, blanks):
    print('inside for loop')
    print(img, gap)
    conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

# define oracle stimulus conditions
images = rng.permutation((stim.ImageImagenet() & 'image_id >= 20 AND image_id < 30').fetch('image_id'))
print(images)
blanks = min_blank + extra_blank * rng.random(len(images))
print(blanks)

repeat_n = 2

for irep in range(0, repeat_n):
    print(irep)
    for img, gap in zip(images, blanks):
        print('inside for loop')
        print(img, gap)
        conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

print(conditions)
# run experiment
exp.push_conditions(conditions)
exp.start()