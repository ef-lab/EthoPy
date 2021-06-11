# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Movies import *
from utils.Generator import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '00:00:00',
    'stop_time'          : '23:59:00',
    'reward'             : 'water',
    'intensity'          : 64,
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
    'noresponse_intertrial': True,
}

v_conds = []

# define stimulus conditions
objects = {1: 'obj1v6',
           2: 'obj2v6'}
v_dur = 2000
key = {
    'difficulty': 1,
    'clip_number'        : 1,
    'skip_time'          : [0],
    'static_frame'       : False,
    'timeout_duration'   : 1000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 8,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe],
                          'movie_duration': v_dur})

# define stimulus conditions
objects = {1: 'obj1v6',
           2: 'obj2v6'}
v_dur = 2000
key = {
    'difficulty': 2,
    'clip_number'        : [1, 2],
    'skip_time'          : [0, 2, 4, 6],
    'static_frame'       : False,
    'timeout_duration'   : 1000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 5,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe],
                          'movie_duration': v_dur})

conditions = v_conds + v_conds

# run experiment
exp = State()
exp.setup(logger, DummyProbe, Movies, session_params, conditions)
exp.run()
