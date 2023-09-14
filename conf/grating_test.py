# Orientation discrimination experiment
from Experiments.MatchPort import *
from Stimuli.Grating import *
from Behaviors.MultiPort import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
    'setup_conf_idx'     : 1,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)

# define stimulus conditions
key = {
    'contrast'           : 100,
    'spatial_freq'       : .05,   # cycles/deg
    'square'             : 0,     # squarewave or Guassian
    'temporal_freq'      : 0,     # cycles/sec
    'flatness_correction': 1,     # adjustment of spatiotemporal frequencies based on animal distance
    'duration'           : 5000,
    'difficulty'         : 1,
    'timeout_duration'   : 4000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 0,
    'delay_duration'     : 0,
    'reward_amount'      : 8
}

repeat_n = 1
conditions = []

ports = {1: 0,
         2: 90}

Grating_Stimuli = GratingOld() if session_params['setup_conf_idx'] ==0 else GratingOld()
for port in ports:
    conditions += exp.make_conditions(stim_class=Grating_Stimuli, conditions={**key,
                                                                              'theta'        : ports[port],
                                                                              'reward_port'  : port,
                                                                              'response_port': port})

# run experiments
exp.push_conditions(conditions)
exp.start()