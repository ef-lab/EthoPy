# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Movies import *
from utils.factorize import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '00:00:00',
    'stop_time'          : '23:55:00',
    'reward'             : 'water',
    'max_reward'         : 3000,
}

v_conds = []

# define stimulus conditions
odor_ratios = [[[100, 0]],
               [[0, 100]]]
objects = ['obj1v6', 'obj2v6']
v_dur = 4000
key = {
    'difficulty'         : 1,
    'clip_number'        : 1,
    'timeout_duration'   : 4000,
    'trial_duration': 5000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration'     : 0,
    'reward_amount'      : 10}

for probe in [1, 2]:
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe - 1],
                          'dutycycle'     : [[0, 0]],
                          'movie_duration': v_dur,
                          'odor_duration' : 0})

# define stimulus conditions
odor_ratios = [[[100, 0], [85, 15], [65, 35], [50, 50]],
               [[0, 100], [15, 85], [35, 65], [50, 50]]]
objects = ['obj1v6', 'obj2v6']
v_dur = 4000
key = {
    'difficulty'         : 2,
    'clip_number': [1, 2],
    'timeout_duration'   : 4000,
    'trial_duration': 5000,
    'intertrial_duration': 0,
    'init_duration': 100,
    'delay_duration'     : 0,
    'reward_amount'      : 1}
for probe in [1, 2]:
    v_conds += factorize({**key, 'probe'  : probe,
                          'movie_name'    : objects[probe - 1],
                          'dutycycle'     : [[0, 0]],
                          'movie_duration': v_dur,
                          'odor_duration' : 0})


logger.log_session(session_params, v_conds, '2AFC')
logger.log_conditions(['MovieCond', 'RewardCond'], v_conds)
conditions = v_conds + v_conds

# run experiment
exp = State()
exp.setup(logger, DummyProbe, Movies, session_params, conditions)
exp.run()

