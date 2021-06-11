from Experiments.FreeWater import *
from Behavior import *
from utils.Generator import *
from Stimuli.RPScreen import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '00:00:00',
    'stop_time'          : '23:50:00',
    'reward'             : 'water',
    'intensity'          : 64,
    'max_reward'         : 2000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.70,
    'stair_down'         : 0.10,
    'noresponse_intertrial'  : False
}

trial_params1 = {
    'difficulty'         : 1,
    'timeout_duration'   : 0,
    'trial_duration'     : 30000,
    'intertrial_duration': 500,
    'init_duration'      : 0,
    'delay_duration'     : 0,
    'reward_amount'      : 3,
    'probe'              : [[1,2]],
}

trial_params2 = {
    'difficulty'         : 2,
    'timeout_duration'   : 0,
    'trial_duration'     : 10000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 0,
    'reward_amount'      : 3,
    'probe'              : [[1,2]],
}

trial_params3 = {
    'difficulty'         : 3,
    'timeout_duration'   : 0,
    'trial_duration'     : 5000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 200,
    'reward_amount'      : 4,
    'probe'              : [[1,2]],
}

trial_params4 = {
    'difficulty'         : 4,
    'timeout_duration'   : 0,
    'trial_duration'     : 3000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 500,
    'reward_amount'      : 8,
    'probe'              : [[1,2]],
}

conds1 = factorize(trial_params1)
conds2 = factorize(trial_params2)
conds3 = factorize(trial_params3)
conds4 = factorize(trial_params4)

conditions = conds1 + conds2 + conds3 + conds4
# run experiment
exp = State()
exp.setup(logger, DummyProbe, Stimulus, session_params, conditions)
exp.run()


