# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.Dot import *
from core.Behavior import *
import random

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 0,
    'intertrial_duration'   : 0,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

# define stimulus conditions
key = {
    'bg_level'              : [[1, 1, 1]],
    'dot_level'             : [[0, 0, 0]],
    'dot_x'                 : list(np.linspace(-.45, .45, 10)),
    'dot_y'                 : list(np.linspace(-.27, .27, 6)),
    'dot_xsize'             : .1,
    'dot_ysize'             : .1,
    'dot_shape'             : 'rect',
    'dot_time'              : .25,
}
repeat_n = 1
conditions = []
dot = Dot()
dot.photodiode = False
dot.rec_fliptimes = False
for rep in range(0, repeat_n):
    conditions += exp.make_conditions(stim_class=dot, conditions=key)

# randomize conditions
random.seed(0)
random.shuffle(conditions)

# run experiments
exp.push_conditions(conditions)
exp.start()