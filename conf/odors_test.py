from Stimuli.Olfactory import *
from Experiments.MatchPort import *
from Behaviors.MultiPort import *


# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '10:00:00',
    'stop_time'          : '22:00:00',
    'max_reward'         : 3000,
    'setup_conf_idx'     : 1,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)
conditions = []

# define stimulus conditions
odor_ratios = {1: [(100, 0)],
               2: [(0, 100)]}
v_dur = 4000
o_dur = 500
key = {
    'odorant_id'         : (1, 2),
    'delivery_port'      : (1, 2),
    'timeout_duration'   : 4000,
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 8,
}

block = exp.Block(difficulty=1, next_up=2, next_down=1, trial_selection='staircase', stair_up=0.7, stair_down=0.6)
for port in [1, 2]:
    for ratio in odor_ratios[port]:
        conditions += exp.make_conditions(stim_class=Olfactory(), conditions={**key, **block.dict(),
                              'reward_port'    : port,
                              'response_port'  : port,
                              'dutycycle'      : ratio,
                              'odor_duration'  : o_dur})

# define stimulus conditions
odor_ratios = {1: [(100, 0), (85, 15), (65, 35), (50, 50)],
               2: [(0, 100), (15, 85), (35, 65), (50, 50)]}
o_dur = 500
key = {
    'odorant_id'         : (1, 2),
    'delivery_port'      : (1, 2),
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'init_duration'      : 100,
    'delay_duration'     : 0,
    'reward_amount'      : 5,
}

block = exp.Block(difficulty=2, next_up=2, next_down=1, trial_selection='staircase', stair_up=0.7, stair_down=0.6)
for port in [1, 2]:
    for ratio in odor_ratios[port]:
        conditions += exp.make_conditions(stim_class=Olfactory(), conditions={**key, **block.dict(),
                              'reward_port'    : port,
                              'response_port'  : port,
                              'dutycycle'      : ratio,
                              'odor_duration'  : o_dur})

# run experiments
exp.push_conditions(conditions)
exp.start()
