from Behaviors.MultiPort import *
from Stimuli.RPScreen import *
from Experiments.FreeWater import *

# define session parameters
session_params = {
    'trial_selection'       : 'biased',
    'start_time'            : '00:00:00',
    'stop_time'             : '23:50:00',
    'max_reward'            : 5000,
    'bias_window'           : 5,
    'noresponse_intertrial' : False
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)

conditions = exp.make_conditions(stim_class=RPScreen(), conditions={
    'difficulty'         : 1,
    'timeout_duration'   : 0,
    'trial_duration'     : 30000,
    'intertrial_duration': 500,
    'init_duration'      : 0,
    'delay_duration'     : 0,
    'reward_amount'      : 3,
    'probe'              : (1, 2),
})

# run experiments
exp.push_conditions(conditions)
exp.start()


