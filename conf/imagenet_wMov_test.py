# Imagenet experiment
import numpy as np
from Experiments.Passive import *
from Stimuli.Images import *
from Stimuli.Movies import *
from core.Behavior import *
stim = dj.create_virtual_module('stimuli.py', 'lab_stimuli')

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 2,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

conditions = []
image_conditions = []
movie_conditions = []

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
    print('inside for loop')
    print(img, gap)
    image_conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

# define test oracle stimulus conditions
images = (stim.ImageImagenet() & 'image_id >= 20 AND image_id < 30').fetch('image_id')
blanks = min_blank + extra_blank * rng.random(len(images))

repeat_n = 2
for irep in range(0, repeat_n):
    print(irep)
    for img, gap in zip(images, blanks):
        image_conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img, 'pre_blank_period': gap})

image_conditions = list(rng.permutation(image_conditions))

# define movies (oracle) conditions
movies = (stim.Movie() & 'movie_class = "cinema"' & 'movie_name = "MadMax" OR movie_name = "matrix" OR movie_name = "matrixan"').fetch('movie_name')
key = {
    'clip_number'        : [20],
    'skip_time'          : [0],
    'movie_duration'     : 2000,
    'static_frame'       : False,
    'intertrial_duration': 0,
}

for mov in movies:
    movie_conditions += exp.make_conditions(stim_class=Movies(), conditions={**key, 'movie_name': mov})
movie_conditions = list(rng.permutation(movie_conditions))

#combine all conditions
conditions = image_conditions[0:10] + [movie_conditions[0]] + image_conditions[10:20] + [movie_conditions[1]] + image_conditions[20:30] + [movie_conditions[2]] + image_conditions[30:40]

# run experiment
exp.push_conditions(conditions)
exp.start()