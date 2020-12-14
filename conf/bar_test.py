# Retinotopic mapping experiment

from Experiments.Passive import *
from Behavior import *
from Stimuli.Bar import *
from utils.Generator import *

# define session parameters
session_params = {
    'trial_selection'    : 'fixed',
    'intensity'          : 255,
    'monitor_distance'   : 10,
    'monitor_aspect'     : 1.77,
    'monitor_size'       : 22,
    'max_res'            : 1000,
    'center_x'           : 0,
    'center_y'           : -0.17,
}

# define stimulus conditions
key = {
    'bar_width'             : 4,  # degrees
    'bar_speed'             : 2,  # degrees/sec
    'flash_speed'           : 2,
    'grat_width'            : 10,  # degrees
    'grat_freq'             : 1,
    'grid_width'            : 10,
    'grit_freq'             : .1,
    'style'                 : 'checkerboard', # checkerboard, grating
    'direction'             : 1,             # 1 for UD LR, -1 for DU RL
    'flatness_correction'   : 1,
    'intertrial_duration'   : 0,
}
repeat_n = 20

conditions = []
for axis in ['horizontal', 'vertical']:
    for rep in range(0, repeat_n):
        conditions += factorize({**key, 'axis'  : axis})

# run experiment
exp = State()
exp.setup(logger, Behavior, FancyBar, session_params, conditions)
exp.run()