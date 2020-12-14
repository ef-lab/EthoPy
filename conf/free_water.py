from Experiments.Center2AFC import *
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
    'max_reward'         : 1000,
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
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 0,
    'reward_amount'      : 3,
    'probe'              : [[1,2]],
}

trial_params3 = {
    'difficulty'         : 3,
    'timeout_duration'   : 0,
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 100,
    'reward_amount'      : 3,
    'probe'              : [[1,2]],
}

trial_params4 = {
    'difficulty'         : 4,
    'timeout_duration'   : 0,
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 200,
    'reward_amount'      : 3,
    'probe'              : [[1,2]],
}

trial_params5 = {
    'difficulty'         : 5,
    'timeout_duration'   : 0,
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 300,
    'reward_amount'      : 5,
    'probe'              : [[1,2]],
}

trial_params6 = {
    'difficulty'         : 6,
    'timeout_duration'   : 0,
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 400,
    'reward_amount'      : 5,
    'probe'              : [[1,2]],
}

trial_params7 = {
    'difficulty'         : 7,
    'timeout_duration'   : 0,
    'trial_duration'     : 2000,
    'intertrial_duration': 500,
    'init_duration'      : 200,
    'delay_duration'     : 500,
    'reward_amount'      : 8,
    'probe'              : [[1,2]],
}

conds1 = factorize(trial_params1);
conds2 = factorize(trial_params2);
conds3 = factorize(trial_params3);
conds4 = factorize(trial_params4);
conds5 = factorize(trial_params5);
conds6 = factorize(trial_params6);
conds7 = factorize(trial_params7);

conditions = conds1 + conds2 + conds3 + conds4 + conds5 + conds6 + conds7

# run experiment
exp = State()
exp.setup(logger, RPProbe, RPScreen, session_params, conditions)
exp.run()


