# Imagenet experiment
import numpy as np
from Experiments.Passive import *
from Stimuli.Images import *
from core.Behavior import *
#from Behaviors.HeadFixed import *
stim = dj.create_virtual_module('stimuli.py', 'lab_stimuli')

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 0,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)
#exp.setup(logger, HeadFixed, session_params)

conditions = []

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
images = (stim.ImageImagenet() & 'image_id < 20').fetch('image_id')
blanks = min_blank + extra_blank * rng.random(len(images))

for img, gap in zip(images, blanks):
    conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

# define oracle stimulus conditions
images = (stim.ImageImagenet() & 'image_id >= 20 AND image_id < 30').fetch('image_id')
blanks = min_blank + extra_blank * rng.random(len(images))

repeat_n = 2
for irep in range(0, repeat_n):
    for img, gap in zip(images, blanks):
        conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

# shuffle conditions
conditions = list(rng.permutation(conditions))

# run experiment
exp.push_conditions(conditions)
exp.start()