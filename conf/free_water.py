from Experiments.FreeWater import *
from Behavior import *

# define session parameters
session_params = {
    'trial_duration'     : 10000,
    'intertrial_duration': 0,
    'timeout_duration'   : 0,
    'stim_duration'      : 0,
    'delay_duration'     : 0,
    'response_interval'  : 1000,
    'init_duration'      : 0,
    'reward_amount'      : 10,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '09:00:00',
    'reward'             : 'water',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, Uniform, session_params)
exp.run()

