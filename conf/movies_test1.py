# simplest visual task with 2 objects without background and 2 clips/object
# delayed response (wait until object disappears from screen, delay_duration = stim_duratin)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.RPMovies import *
from utils.factorize import *

# define stimulus conditions
probe1_conds = factorize({'probe': [1], 'movie_name': ['obj3v6'], 'movie_duration': [4000], 'clip_number': list(range(1, 3))})
probe2_conds = factorize({'probe': [2], 'movie_name': ['obj1v6'], 'movie_duration': [4000], 'clip_number': list(range(1, 3))})
conditions = sum([probe1_conds, probe2_conds], [])

# define session parameters
session_params = {
    'trial_duration'     : 10000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'delay_duration'     : 4000,
    'response_interval'  : 1000,
    'init_duration'      : 1000,
    'reward_amount'      : 8,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '22:00:00',
    'reward'             : 'water',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, RPMovies, session_params, conditions)
exp.run()

