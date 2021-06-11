# visual task with 2 objects (2 and 3) staircase

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Movies import *
from utils.Generator import *

# define session parameters
session_params = {
    'trial_selection': 'staircase',
    'start_time': '11:00:00',
    'stop_time': '19:00:00',
    'reward': 'water',
    'intensity': 64,
    'max_reward': 2000,
    'bias_window': 5,
    'staircase_window': 20,
    'stair_up': 0.65,
    'stair_down': 0.55,
    'noresponse_intertrial': False,
}

v_conds = []

# define stimulus conditions
objects = {1: 'obj2v6',
           2: 'obj3v6'}
v_dur = 4000
key = {
    'difficulty': 1,
    'clip_number': 1,
    'skip_time': [0],
    'static_frame': False,
    'timeout_duration': 6000,
    'trial_duration': 7000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration': 1000,
    'reward_amount': 4,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe': probe,
                          'movie_name': objects[probe],
                          'movie_duration': v_dur})

# define stimulus conditions
objects = {1: 'obj2v6',
           2: 'obj3v6'}
v_dur = 4000
key = {
    'difficulty': 2,
    'clip_number': 1,
    'skip_time': [0, 0.5, 1, 1.5],
    'static_frame': False,
    'timeout_duration': 3000,
    'trial_duration': 7000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration': 100,
    'reward_amount': 4,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe': probe,
                          'movie_name': objects[probe],
                          'movie_duration': v_dur})

# define stimulus conditions
objects = {1: 'obj2v6',
           2: 'obj3v6'}
v_dur = 4000
key = {
    'difficulty': 3,
    'clip_number': [1, 2],
    'skip_time': [0, 0.5, 1, 1.5],
    'static_frame': False,
    'timeout_duration': 3000,
    'trial_duration': 7000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration': 300,
    'reward_amount': 5,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe': probe,
                          'movie_name': objects[probe],
                          'movie_duration': v_dur})

# define stimulus conditions
objects = {1: 'obj2v6',
           2: 'obj3v6'}
v_dur = 4000
key = {
    'difficulty': 4,
    'clip_number': [1, 2, 3, 4],
    'skip_time': [0, 0.5, 1, 1.5],
    'static_frame': False,
    'timeout_duration': 3000,
    'trial_duration': 7000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration': 350,
    'reward_amount': 5,
}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe': probe,
                          'movie_name': objects[probe],
                          'movie_duration': v_dur})

conditions = v_conds

# run experiment
exp = State()
exp.setup(logger, DummyProbe, Movies, session_params, conditions)
exp.run()


