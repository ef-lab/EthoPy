# Retinotopic mapping experiment

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

# define stimulus conditions
train_images = ('img1','img2')

key = {
    'image_id'             : [1,2],                         # image index
    'test_image'           : False,
    'image_duration'       : 5000,
}

for img in images:
    conditions += exp.make_conditions(stim_class=Images(), conditions={**key, 'image_name': img})
    
repeat_n = 20

conditions = []
for axis in ['horizontal', 'vertical']:
    for rep in range(0, repeat_n):
        conditions += exp.make_conditions(stim_class=Bar(), conditions={**key, 'axis': axis})

# run experiment
exp.push_conditions(conditions)
exp.start()