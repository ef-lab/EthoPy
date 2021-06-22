# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.Bar import *
from core.Behavior import *


# define session parameters
session_params = {
    'setup_conf_idx'        : 1,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 1,
}

# define stimulus conditions
key = {
    'center_x'              : 0,
    'center_y'              : -0.17,
    'max_res'               : 1000,
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
        conditions += exp.make_conditions(Bar, {**key, 'axis'  : axis})


# run experiments
exp.push_conditions(conditions)
exp.start()