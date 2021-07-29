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
conditions = []

rew_locs = ([4, 4], [0, 4])
odors = ((1, 2, 3, 4), (1, 2, 4, 3))
for idx, loc in enumerate(rew_locs):
    conditions += exp.make_conditions(stim_class=VROdors(), conditions={
        'odorant_id'            : odors[idx],
        'delivery_port'         : odors[idx],
        'odor_x'                : (0, 5, 5, 0),
        'odor_y'                : (0, 0, 5, 5),
        'x_sz'                  : 5,
        'y_sz'                  : 5,
        'trial_duration'        : 300000,
        'theta0'                : 0,
        'x0'                    : 2.5,
        'y0'                    : 2.5,
        'reward_loc_x'          : loc[0],
        'reward_loc_y'          : loc[1],
        'response_loc_x'        : (0, 5, 5, 0),
        'response_loc_y'        : (0, 0, 5, 5),
        'fun'                   : 3,
        'radius'                : 0.3,
        'reward_amount'         : 10,
    })

# run experiments
exp.push_conditions(conditions)
exp.start()