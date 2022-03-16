# Blank experiment

from Experiments.Passive import *
from core.Stimulus import *
from core.Behavior import *

# define session parameters
session_params = {
    'setup_conf_idx'        : 2,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

conditions = []
conditions += exp.make_conditions(stim_class=Stimulus(), conditions=dict())

# run experiment
exp.push_conditions(conditions)
exp.start()