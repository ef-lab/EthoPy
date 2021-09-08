#from Behaviors.MultiPort import *
from Behaviors.VRBall import *
#from Stimuli.RPScreen import *
from Stimuli.VROdors import *
from Experiments.FreeWater import *

# define session parameters
session_params = {
    'trial_selection'       : 'bias',
    'start_time'            : '00:00:00',
    'stop_time'             : '23:50:00',
    'max_reward'            : 5000,
    'bias_window'           : 5,
    'noresponse_intertrial' : False,
    'setup_conf_idx'        : 1,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)

conditions = exp.make_conditions(stim_class=RPScreen(), conditions={
    'difficulty'         : 1,
    'timeout_duration'   : 0,
    'intertrial_duration': 500,
    'init_duration'      : 0,
    'delay_duration'     : 0,
    'reward_amount'      : 10,
    'reward_port': -1,
    'response_port': -1,
})

conditions = exp.make_conditions(stim_class=VROdors(), conditions = {
    'x0'            : 2.5,
    'y0'            : 2.5,
    'radius'        : 5,
    'response_loc_x': (0, 5, 5, 0),
    'response_loc_y': (0, 0, 5, 5),
    'reward_loc_x'  : 2.5,
    'reward_loc_y'  : 2.5,
    'reward_amount' : 10
})

# run experiments
exp.push_conditions(conditions)
exp.start()


