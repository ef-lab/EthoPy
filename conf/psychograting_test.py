# Orientation discrimination experiment
from Experiments.Passive import *
from Stimuli.PsychoGrating import *
from core.Behavior import *
from Interfaces.Photodiode import *

# define session parameters
session_params = {
    'trial_selection'    : 'fixed',
    'setup_conf_idx'     : 0,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)
block = exp.Block(difficulty=0, next_up=0, next_down=0, trial_selection='fixed')

# define stimulus conditions
key = {
    'contrast'           : 1,
    'sf'       : .2,   # cycles/deg
    'duration'           : 1000,
    'trial_duration'     : 1000,
    'intertrial_duration': 0,
    'init_duration'      : 0,
    'delay_duration'     : 0,
}

repeat_n = 1
conditions = []

ports = {1: 0,
         2: 90}

Grating_Stimuli = PsychoGrating()
Grating_Stimuli.fill_colors.ready = []
Grating_Stimuli.fill_colors.background = []

Grating_Stimuli.fill_colors.set({'background': (0.5, 0.5, 0.5)})


for port in ports:
    conditions += exp.make_conditions(stim_class=Grating_Stimuli, conditions={**block.dict(), **key,
                                                                              'ori'        : ports[port],
                                                                              'pos_x': [[-5, 5]],
                                                                              'size': 10})

conditions += exp.make_conditions(stim_class=Grating_Stimuli, conditions={**block.dict(), **key,
                                                                              'ori'        : 0,
                                                                              'pos_x': 0,
                                                                              'size': 100})

# run experiments
exp.push_conditions(conditions)
exp.start()