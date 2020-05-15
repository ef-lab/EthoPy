# simplest olfactory task with 2 odors
# delayed response (wait until odor stimulation stops, delay_duration = stim_duratin)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Odors import *
from utils.factorize import *

# define stimulus conditions
probe1_conds = factorize({'probe': [1], 'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'duration': [[2000, 2000]],
                          'dutycycle': [[100, 0], [90, 10], [80, 20], [70, 30], [60, 40], [50, 50]]})
probe2_conds = factorize({'probe': [2], 'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'duration': [[2000, 2000]],
                          'dutycycle': [[100, 0], [90, 10], [80, 20], [70, 30], [60, 40], [50, 50]]})
conditions = sum([probe1_conds, probe2_conds], [])

# define session parameters
session_params = {
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'stim_duration'      : 2000,
    'delay_duration'     : 2000,
    'response_interval'  : 1000,
    'init_duration'      : 1000,
    'reward_amount'      : 8,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '18:00:00',
    'reward': 'water',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, Odors, session_params, conditions)
exp.run()


