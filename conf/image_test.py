# Imagenet experiment

from Experiments.Passive import *
from Stimuli.Images import *
from core.Behavior import *

# define session parameters
session_params = {
    'trial_selection'       : 'fixed',
    'setup_conf_idx'        : 0,
    'max_res'               : 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

conditions = []
#print('empty conditions')

# define stimulus conditions
images = [[0, 1, 2], [3, 4, 5]]

key = {
    'image_class'          : 'imagenet',
    'pre_blank_period'     : 500,                        # (ms) off duration
    'presentation_time'    : 1000,                        # (ms) image duration
    'intertrial_duration'   : 0,
}  
    
repeat_n = 2

for irep in range(0, repeat_n):
    for img in images[irep]:
        print('inside for loop')
        print(img)
        conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_id': img})

print(conditions)
# run experiment
exp.push_conditions(conditions)
exp.start()