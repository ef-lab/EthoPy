from Experiments.Navigate import *
from Behaviors.VRBall import *
from Stimuli.VROdors import *

# define session parameters
session_params = {
    'trial_selection'        : 'staircase',
    'noresponse_intertrial'  : True,
    'max_reward'             : 2500,
    'bias_window'            : 5,
    'staircase_window'       : 10,
    'stair_up'               : 0.7,
    'stair_down'             : 0.6,
    'setup_conf_idx'         : 1,
}

exp = Experiment()
exp.setup(logger, VRBall, session_params)
conditions = []

non_resp = .1
radius = 2**.5*2.5-non_resp

def_key = {
        'odor_x'                : (0, 5, 5, 0),
        'odor_y'                : (0, 0, 5, 5),
        'x_sz'                  : 5,
        'y_sz'                  : 5,
        'trial_duration'        : 300000,
        'theta0'                : 0,
        'x0'                    : 2.5,
        'y0'                    : 2.5,
        'response_loc_x'        : (0, 5, 5, 0),
        'response_loc_y'        : (0, 0, 5, 5),
        'extiction_factor'      : 2,
        'radius'                : radius,
        'reward_amount'         : 10,
        'reward_loc_x'          : 2.5,
        'odorant_id'            : (1, 2, 3, 4),
        'delivery_port'         : (1, 2, 3, 4),
    }


conditions += exp.make_conditions(stim_class=VROdors(), conditions={**def_key,
                              'difficulty'     : 1,
                              'reward_loc_y'   : 2.5 + radius + .1})

conditions += exp.make_conditions(stim_class=VROdors(), conditions={**def_key,
                              'difficulty'     : 2,
                              'reward_loc_y'   : 2.5 + radius + .2})

# run experiments
exp.push_conditions(conditions)
exp.start()