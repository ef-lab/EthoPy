from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.RPMovies import *
from utils.factorize import *

# define stimulus conditions
probe1_conds = factorize({'probe': [1], 'movie_name': ['o3bgv6'], 'clip_number': list(range(1, 10))})
probe2_conds = factorize({'probe': [2], 'movie_name': ['o1bgv6'], 'clip_number': list(range(1, 10))})
conditions = sum([probe1_conds, probe2_conds], [])

# define session parameters
session_params = {
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'stim_duration'      : 500,
    'delay_duration'     : 500,
    'response_interval'  : 1000,
    'init_duration'      : 500,
    'reward_amount'      : 5,
    'randomization'      : 'bias',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, RPMovies, session_params, conditions)
exp.run()

