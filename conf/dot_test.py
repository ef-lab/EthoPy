# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.Dot import *
from core.Behavior import *
import random

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 2,
    'intertrial_duration'   : 0,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

# define stimulus conditions
key = {
    'bg_level'              : [[255, 255, 255]],
    'dot_level'             : [[0, 0, 0]],
    'dot_x'                 : [-.5, -.4, -.3, -.2, -.1, 0, .1, .2, .3, .4, .5],
    'dot_y'                 : [-.3, -.2, -.1, .1, .2, .3],
    'dot_xsize'             : .1,
    'dot_ysize'             : .1,
    'dot_shape'             : 'rect',
    'dot_time'              : .25,
}

repeat_n = 10

conditions = []
for rep in range(0, repeat_n):
    conditions += exp.make_conditions(stim_class=Dot(), conditions=key)

# randomize conditions
random.seed(0)
random.shuffle(conditions)

# run experiments
exp.push_conditions(conditions)
exp.start()