from Stimuli.SmellyObjects import *
from Experiments.MatchToSample import *
from Behaviors.MultiPort import *

# define session parameters
session_params = {
    'start_time'           : '08:00:00',
    'stop_time'            : '22:00:00',
    'min_reward'           : 100,
    'max_reward'           : 3000,
    'setup_conf_idx'       : 1,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)
vo, vis = [], []

block = exp.Block(difficulty=0, next_up=1, next_down=0, trial_selection='staircase')

trial_params = {**block.dict(),
    'timeout_duration'      : 6000,
    'cue_duration'          : 5000,
    'intertrial_duration'   : 500,
    'init_duration'         : 100,
    'delay_duration'        : 0,
    'reward_amount'         : 5,
}

v_params = {
    'obj_mag'               : .5,
    'obj_rot'               : 0,
    'obj_tilt'              : 0,
    'obj_yaw'               : 0
}

o_params = {
    'odorant_id'            : (1, 3),
    'delivery_port'         : (1, 2),
    'dutycycle'             : (0, 0),
}

cue_obj = [2, 2, 3, 3]
resp_obj = [(3, 2), (2, 3), (3, 2), (2, 3)]
rew_port = [2, 1, 1, 2]
odor_ratios = [(100, 0), (100, 0), (0, 100), (0, 100)]

for idx, port in enumerate(rew_port):
    vo += exp.make_conditions(stim_class=SmellyObjects(), stim_periods=['Cue', 'Response'], conditions={**trial_params,
        'Cue': {**v_params, **o_params,
            'obj_id'        : cue_obj[idx],
            'obj_pos_x'     : 0,
            'obj_dur'       : 2000,
            'odor_duration' : 500,
            'dutycycle'     : odor_ratios[idx]},
        'Response': {**v_params, **o_params,
            'obj_id'        : resp_obj[idx],
            'obj_pos_x'     : (-.25, .25),
            'obj_dur'       : 2000},
        'reward_port'       : port,
        'response_port'     : port})
    vis += exp.make_conditions(stim_class=SmellyObjects(), stim_periods=['Cue', 'Response'], conditions={**trial_params,
        'Cue': {**v_params, **o_params,
            'obj_id'        : cue_obj[idx],
            'obj_pos_x'     : 0,
            'obj_dur'       : 2000},
        'Response': {**v_params, **o_params,
            'obj_id'        : resp_obj[idx],
            'obj_pos_x'     : (-.25, .25),
            'obj_dur'       : 2000},
        'reward_port'       : port,
        'response_port'     : port})

conditions = vo + vis

# run experiments
exp.push_conditions(conditions)
exp.start()

