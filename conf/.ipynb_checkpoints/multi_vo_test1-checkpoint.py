# simplest visual-olfactory task with 2 objects without background and 2 clips/object and 2 odors
# delayed response (wait until object disappears from screen, delay_duration = stim_duratin)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.VO import * 
from utils.factorize import *

# define stimulus conditions
probe1_conds = factorize({'probe': [1], 'movie_name': ['obj3v6'], 'clip_number': list(range(1, 2)), 
                         'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'duration': [[2000, 2000]],
                         'dutycycle': [[100, 0], [90, 10], [80, 20], [70, 30], [60, 40], [50, 50]]})
probe2_conds = factorize({'probe': [2], 'movie_name': ['obj1v6'], 'clip_number': list(range(1, 2)), 
                          'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'duration': [[2000, 2000]],
                          'dutycycle': [[100, 0], [90, 10], [80, 20], [70, 30], [60, 40], [50, 50]]})
conditions = sum([probe1_conds, probe2_conds], [])

# define session parameters
session_params = {
    'trial_duration'     : 10000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'stim_duration'      : 4000,
    'delay_duration'     : 4000,
    'response_interval'  : 1000,
    'init_duration'      : 1000,
    'reward_amount'      : 8,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '18:00:00',
    'reward'             : 'water',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, VO, session_params, conditions) 
exp.run()

