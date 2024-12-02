# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.PsychoBar import *
from Behaviors.HeadFixed import *

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 0,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, HeadFixed, session_params)

# define stimulus conditions
key = {
    'center_x'              : 0,
    'center_y'              : 0,
    'max_res'               : 1000,
    'bar_width'             : 4,  # degrees
    'bar_speed'             : 5,  # degrees/sec
    'flash_speed'           : 2,
    'grat_width'            : 3,  # degrees
    'grat_freq'             : 3,
    'grid_width'            : 15,
    'grit_freq'             : 1,
    'style'                 : 'checkerboard', # checkerboard, grating
    'direction'             : 1,             # 1 for UD LR, -1 for DU RL
    'flatness_correction'   : 0,
    'intertrial_duration'   : 0,
}

repeat_n = 10

block = exp.Block(difficulty=0, next_up=0, next_down=0, trial_selection='fixed')
conditions = []
for axis in ['horizontal', 'vertical']:
    for rep in range(0, repeat_n):
        conditions += exp.make_conditions(stim_class=Bar(), conditions={**block.dict(),**key, 'axis': axis})


# run experiments
exp.push_conditions(conditions)
exp.start()