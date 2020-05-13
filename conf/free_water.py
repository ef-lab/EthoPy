from Experiments.FreeWater import *
from Behavior import *
from Stimuli.RPMovies import *

# define session parameters
session_params = {
    'trial_duration'     : 10000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'stim_duration'      : 3000,
    'delay_duration'     : 500,
    'response_interval'  : 1000,
    'init_duration'      : 0,
    'reward_amount'      : 10,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '18:00:00',
    'reward'             : 'water',
}

# run experiment
exp = State()
exp.setup(logger, RPBehavior, Uniform, session_params)
exp.run()

