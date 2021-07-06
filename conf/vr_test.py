from typing import Any, Callable

# import numpy as np
from Experiments.Navigate import *
from Behaviors.VRBall import *
from Stimuli.VROdors import *
from utils.Generator import *

conditions = []

# define session parameters
session_params = {
    'trial_selection'        : 'random',
    'reward'                 : 'water',
    'noresponse_intertrial'  : True,
    'resp_cond'              : 'correct_loc',
    'max_reward'             : 3000,
    'staircase_window'       : 10,
    'bias_window'            : 5,
    'stair_up'               : 0.7,
    'stair_down'             : 0.6
}

# define environment conditions
key = {
    'init_ready'            : 0,
    'delay_ready'           : 0,
    'resp_ready'            : 0,
    'intertrial_duration'   : 0,
    'response_duration'     : 30000,
    'reward_amount'         : 8,
    'reward_duration'       : 2000,
    'punish_duration'       : 1000,
    'x_max'                 : 10,
    'x_min'                 : 0,
    'y_max'                 : 10,
    'y_min'                 : 0,
}

np.random.seed(0)
conditions += factorize({**key,
                        'difficulty'          : 1,
                        'odor_id'             : (1, 2, 3, 4),
                        'delivery_port'       : (1, 2, 3, 4),
                        'probe'               : 1,
                        'theta0'              : 0,
                        'x0'                  : 5,
                        'y0'                  : 5,
                        'reward_loc_x'        : 5,
                        'reward_loc_y'        : 7,
                        'response_loc_x'      : (0, 10, 10, 0),
                        'response_loc_y'      : (0, 0, 10, 10),
                        'trial_duration'      : 300000,
                        'intertrial_duration' : 0,
                        'fun'                 : 2,
                        'radius'              : 0.8,
                        'response_duration'   : 240000})


# run experiments
exp = State()
exp.setup(logger, VRBehavior, VROdors, session_params, conditions)
exp.run()