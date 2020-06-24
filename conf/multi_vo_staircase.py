# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.SmellyMovies import *
from utils.Generator import *

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
objects = {1: 'obj1v6',
           2: 'obj2v6'}
v_dur = 4000
o_dur = 500
key = {
    'difficulty': 1,
    'odor_idx'           : [[1, 2]],
    'delivery_idx'       : [[1, 2]],
    'clip_number'        : 1,
    'skip_time'          : [0, 1, 2, 3],
    'static_frame'       : False,
    'timeout_duration'   : 4000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 8,
}

for probe in [1, 2]:
    for ratio in odor_ratios[probe]:
        vo_conds += factorize({**key, 'probe'  : probe,
                               'movie_name'    : objects[probe],
                               'dutycycle'     : [ratio],
                               'movie_duration': v_dur,
                               'odor_duration' : o_dur})
        o_conds += factorize({**key, 'probe'   : probe,
                              'movie_name'     : objects[probe],
                              'dutycycle'      : [ratio],
                              'movie_duration' : 0,
                              'odor_duration'  : o_dur})
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe],
                          'dutycycle'     : [[0, 0]],
                          'movie_duration': v_dur,
                          'odor_duration' : 0})

# define stimulus conditions
odor_ratios = {1: [[100, 0], [85, 15], [65, 35], [50, 50]],
               2: [[0, 100], [15, 85], [35, 65], [50, 50]]}
objects = {1: 'obj1v6',
           2: 'obj2v6'}
v_dur = 4000
o_dur = 500
key = {
    'difficulty': 2,
    'odor_idx'           : [[1, 2]],
    'delivery_idx'       : [[1, 2]],
    'clip_number'        : [1, 2],
    'skip_time'          : [0, 1, 2, 3],
    'static_frame'       : False,
    'timeout_duration'   : 4000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 5,
}

for probe in [1, 2]:
    for ratio in odor_ratios[probe]:
        vo_conds += factorize({**key, 'probe'  : probe,
                               'movie_name'    : objects[probe],
                               'dutycycle'     : [ratio],
                               'movie_duration': v_dur,
                               'odor_duration' : o_dur})
        o_conds += factorize({**key, 'probe'   : probe,
                              'movie_name'     : objects[probe],
                              'dutycycle'      : [ratio],
                              'movie_duration' : 0,
                              'odor_duration'  : o_dur})
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe],
                          'dutycycle'     : [[0, 0]],
                          'movie_duration': v_dur,
                          'odor_duration' : 0})

conditions = vo_conds + vo_conds + v_conds + v_conds + o_conds

# run experiment
exp = State()
exp.setup(logger, RPBehavior, SmellyMovies, session_params, conditions)
exp.run()
