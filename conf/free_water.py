from Experiments.FreeWater import *
from Behavior import *

# define session parameters
session_params = {
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'timeout_duration'   : 0,
    'stim_duration'      : 0,
    'delay_duration'     : 0,
    'response_interval'  : 1000,
    'init_duration'      : 200,
    'reward_amount'      : 8,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '20:00:00',
    'reward'             : 'water',
    'max_reward'         : 2000,
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, Uniform, session_params)
exp.run()

