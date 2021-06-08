# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Odors import *
from utils.generator import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '10:00:00',
    'stop_time'          : '22:00:00',
    'reward'             : 'water',
    'intensity'          : 64,
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
}

vo_conds = []; v_conds = []; o_conds = []

# define stimulus conditions
odor_ratios = {1: [[100, 0]],
               2: [[0, 100]]}
v_dur = 4000
o_dur = 500
key = {
    'difficulty': 1,
    'odor_id'            : [[1, 2]],
    'delivery_port'      : [[1, 2]],
    'timeout_duration'   : 4000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 8,
}

for probe in [1, 2]:
    for ratio in odor_ratios[probe]:
        o_conds += factorize({**key, 'probe'   : probe,
                              'dutycycle'      : [ratio],
                              'odor_duration'  : o_dur})

# define stimulus conditions
odor_ratios = {1: [[100, 0], [85, 15], [65, 35], [50, 50]],
               2: [[0, 100], [15, 85], [35, 65], [50, 50]]}
o_dur = 500
key = {
    'difficulty': 2,
    'odor_id'            : [[1, 2]],
    'delivery_port'      : [[1, 2]],
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 5,
}

for probe in [1, 2]:
    for ratio in odor_ratios[probe]:
        o_conds += factorize({**key, 'probe'   : probe,
                              'dutycycle'      : [ratio],
                              'odor_duration'  : o_dur})


conditions = o_conds

# run experiment
exp = State()
exp.setup(logger, RPBehavior, Odors, session_params, conditions)
exp.run()
