# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.SmellyMovies import *
from utils.Generator import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '08:00:00',
    'stop_time'          : '22:00:00',
    'reward'             : 'water',
    'intensity'          : 64,
    'min_reward'         : 100,
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
    'noresponse_intertrial': True,
}

vo_conds = [];
v_conds = [];
o_conds = []

# define stimulus conditions
odor_ratios = {2: [[100, 0]],
               1: [[0, 100]]}
objects = {1: 'obj4v6',
           2: 'obj3v6'}
v_dur = 4000
o_dur = 500

trial_params = {
    'difficulty': 1,
    'timeout_duration': 6000,
    'trial_duration': 5000,
    'intertrial_duration': 500,
    'init_duration': 100,
    'delay_duration': 500,
    'reward_amount': 3,
}

v_params = {
    'clip_number': 1,
    'skip_time': [0],
    'static_frame': False,
    'movie_duration': 4000,
}

o_params = {
    'odor_id': [[1, 3]],
    'delivery_port': [[1, 2]],
    'odor_duration': 500
}

for probe in [1, 2]:
    vo_conds += factorize({**trial_params, **o_params, **v_params,
                           'probe': probe,
                           'movie_name': objects[probe],
                           'dutycycle': odor_ratios[probe]})
    o_conds += factorize({**trial_params, **o_params,
                          'probe': probe,
                          'movie_name': objects[probe],
                          'dutycycle': odor_ratios[probe],
                          'clip_number': 1,
                          'skip_time': 0,
                          'static_frame': False,
                          'movie_duration': 0})
    v_conds += factorize({**trial_params, **v_params,
                          'probe': probe,
                          'movie_name': objects[probe],
                          'odor_id': [[1, 3]],
                          'delivery_port': [[1, 2]],
                          'dutycycle': [[0, 0]],
                          'odor_duration': 0})

# define stimulus conditions
odor_ratios = {2: [[100, 0], [85, 15], [65, 35], [50, 50]],
               1: [[0, 100], [15, 85], [35, 65], [50, 50]]}
objects = {1: 'obj4v6',
           2: 'obj3v6'}

trial_params = {
    'difficulty': 2,
    'timeout_duration': 3000,
    'trial_duration': 5000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration': 500,
    'reward_amount': 4,
}

v_params = {
    'clip_number': 1,
    'skip_time': [0, 0.5, 1],
    'static_frame': False,
    'movie_duration': 4000,
}

o_params = {
    'odor_id': [[1, 3]],
    'delivery_port': [[1, 2]],
    'odor_duration': 500
}

for probe in [1, 2]:
    vo_conds += factorize({**trial_params, **o_params, **v_params,
                           'probe': probe,
                           'movie_name': objects[probe],
                           'dutycycle': odor_ratios[probe]})
    o_conds += factorize({**trial_params, **o_params,
                          'probe': probe,
                          'movie_name': objects[probe],
                          'dutycycle': odor_ratios[probe],
                          'clip_number': 1,
                          'skip_time': 0,
                          'static_frame': False,
                          'movie_duration': 0})
    v_conds += factorize({**trial_params, **v_params,
                          'probe': probe,
                          'movie_name': objects[probe],
                          'odor_id': [[1, 3]],
                          'delivery_port': [[1, 2]],
                          'dutycycle': [[0, 0]],
                          'odor_duration': 0})

conditions = vo_conds + v_conds + o_conds

# run experiment
exp = State()
exp.setup(logger, DummyProbe, SmellyMovies, session_params, conditions)
exp.run()

