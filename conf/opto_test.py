from Stimuli.Opto import *
from Experiments.MatchPort import *
from Behaviors.HeadFixed import *


# define session parameters
session_params = {
    'setup_conf_idx'     : 0,
    'trial_selection'    : 'fixed',
}

exp = Experiment()
exp.setup(logger, HeadFixed, session_params)
conditions = []

# define stimulus conditions
dutycycles = (20, 50, 100)
o_dur = 500

key = {
    'intertrial_duration': 500,
}

for ratio in dutycycles:
    conditions += exp.make_conditions(stim_class=Opto(), conditions={**key,
                          'dutycycle'      : ratio,
                          'duration'  : o_dur})


# run experiments
exp.push_conditions(conditions)
exp.start()
