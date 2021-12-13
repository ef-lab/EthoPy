from Experiments.Passive import *
from Stimuli.Movies import *
from core.Behavior import *

# define session parameters
session_params = {
    'setup_conf_idx'     : 1,
    'trial_selection'    : 'fixed',
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)


conditions = []

# define stimulus conditions
objects = ('obj1v6','MadMax')

key = {
    'clip_number'        : [20,30],
    'skip_time'          : [0],
    'movie_duration'     : 2000,
    'static_frame'       : False,
    'intertrial_duration': 0,
}

for obj in objects:
    conditions += exp.make_conditions(stim_class=Movies(), conditions={**key, 'movie_name': obj})

# run experiment
exp.push_conditions(conditions)
exp.start()
