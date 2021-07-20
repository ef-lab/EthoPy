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
    'odor_x'                : (4, 6, 6, 4),
    'odor_y'                : (4, 4, 6, 6),
    'x_sz'                  : 2,
    'y_sz'                  : 2,
    'trial_duration'        : 300000,
    'theta0'                : 0,
    'x0'                    : 5,
    'y0'                    : 5,
    'reward_loc_x'          : 6,
    'reward_loc_y'          : 6,
    'response_loc_x'        : (4, 6, 6, 4),
    'response_loc_y'        : (4, 4, 6, 6),
    'fun'                   : 5,
    'radius'                : 0.8,
    'reward_amount'         : 10,
}

# run experiments
conditions = exp.make_conditions(stim_class=VROdors(), conditions=key)
exp.push_conditions(conditions)
exp.start()