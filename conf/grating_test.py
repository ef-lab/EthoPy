# Orientation discrimination experiment
from Experiments.Passive import *
from Stimuli.Grating import *
from core.Behavior import *
from Interfaces.Photodiode import *

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
    'setup_conf_idx'     : 0,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)
#phd = Photodiode(exp=exp)
block = exp.Block(difficulty=0, next_up=0, next_down=0, trial_selection='fixed')

# define stimulus conditions
key = {
    'contrast'           : 100,
    'spatial_freq'       : .05,   # cycles/deg
    'square'             : 0,     # squarewave or Guassian
    'temporal_freq'      : 1,     # cycles/sec
    'flatness_correction': 1,     # adjustment of spatiotemporal frequencies based on animal distance
    'duration'           : 5000,
    'timeout_duration'   : 1000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 0,
    'delay_duration'     : 0,
}

repeat_n = 1
conditions = []

ports = {1: 0,
         2: 90}

Grating_Stimuli = Grating() #if session_params['setup_conf_idx'] ==0 else GratingOld()
Grating_Stimuli.photodiode = 'parity'
Grating_Stimuli.rec_fliptimes = True
Grating_Stimuli.fill_colors.ready = []
for port in ports:
    conditions += exp.make_conditions(stim_class=Grating_Stimuli, conditions={**block.dict(), **key,
                                                                              'theta'        : ports[port],
                                                                              'reward_port'  : port,
                                                                              'response_port': port})

# run experiments
exp.push_conditions(conditions)
exp.start()
#phd.cleanup()