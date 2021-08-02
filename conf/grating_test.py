# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.Grating import *
from core.Behavior import *

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 1,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

# define stimulus conditions
key = {
    'theta'    : [0, 45],
    'contrast' : 20,
    'square'   : 1,
}

repeat_n = 1
conditions = []
for rep in range(0, repeat_n):
    conditions += exp.make_conditions(stim_class=Grating(), conditions={**key})


# run experiments
exp.push_conditions(conditions)
exp.start()