# Imagenet experiment

from Experiments.Passive import *
from Stimuli.Images import *
from core.Behavior import *

# define session parameters
session_params = {
    'trial_selection'       : 'random',
    'setup_conf_idx'        : 1,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

conditions = []
print('empty conditions')

# define stimulus conditions
images = [[1, 2, 3], [4, 5, 6]]

key = {
    'image_class'          : 'imagenet',
    'pre_blank_period'     : .2,                        # (s) off duration
    'presentation_time'    : .5,                        # (s) image duration
}  
    
repeat_n = 2

for irep in range(0, repeat_n):
    for img in images[irep]:
        conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img})
        print(conditions)


# run experiment
exp.push_conditions(conditions)
exp.start()