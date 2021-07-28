from Experiments.Navigate import *
from Behaviors.VRBall import *
from Stimuli.VROdors import *

# define session parameters
session_params = {
    'trial_selection'        : 'random',
    'noresponse_intertrial'  : True,
    'setup_conf_idx'         : 1,
}

exp = Experiment()
exp.setup(logger, VRBall, session_params)

# define environment conditions
key = {
    'odorant_id'            : (1, 2, 3, 4),
    'delivery_port'         : (1, 2, 3, 4),
    'odor_x'                : (0, 5, 5, 0),
    'odor_y'                : (0, 0, 5, 5),
    'x_sz'                  : 5,
    'y_sz'                  : 5,
    'trial_duration'        : 300000,
    'theta0'                : 0,
    'x0'                    : 2.5,
    'y0'                    : 2.5,
    'reward_loc_x'          : 4,
    'reward_loc_y'          : 4,
    'response_loc_x'        : (0, 5, 5, 0),
    'response_loc_y'        : (0, 0, 5, 5),
    'extiction_factor'      : 3,
    'radius'                : 0.3,
    'reward_amount'         : 10,
}

# run experiments
conditions = exp.make_conditions(stim_class=VROdors(), conditions=key)
exp.push_conditions(conditions)
exp.start()