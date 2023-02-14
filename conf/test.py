# Object experiment
from Experiments.MatchToSample import *
from Behaviors.MultiPort import *
from Stimuli.Panda import *
from scipy import interpolate

interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x

# define session parameters
session_params = {
    'max_reward'            : 1500,
    'min_reward'            : 50,
    'stair_up'              : 0.65,
    'setup_conf_idx'        : 1,
    'staircase_window'      : 15,
    'sliding':True,
    'transition_method': 'staircase',
    'criterion_method': 'performance',
    'selection_type':'random',
    'window_size':3,
    'block_upgrade':0.7,
    'block_downgrade':0.4,
    'noresponse_intertrial' : True,
    'incremental_punishment' : False
}


exp = Experiment()
exp.setup(logger, MultiPort, session_params)
conditions = []

# define environment conditions
env_key = {
    'cue_ready'             : 150,
    'abort_duration'        : 500,
    'punish_duration'       : 1000,
    'cue_duration'          : 240000,
    'delay_duration'        : 350,
}


#distractor 
cue_obj = [7, 7]
resp_obj = [7, 7]
x_pos = [-.3, .3]
rew_prob = [1, 2]
rot_f = lambda: interp((np.random.rand(20)-.5) *2500)
rots = rot_f()
for idx, obj_comb in enumerate(resp_obj):
    conditions += exp.make_conditions(stim_class=Panda(), stim_periods=['Cue', 'Response'], conditions={**env_key,
            'Cue': {
                'obj_id'        : cue_obj[idx],
                'obj_dur'       : 240000,
                'obj_pos_x'     : 0,
                'obj_pos_y'     : 0.02,
                'obj_mag'       : 0.5,
                'obj_rot'       : (rots, rots),
                'obj_tilt'      : (rots, rots)},                                                                       
            'Response': {
                'obj_id'        : resp_obj[idx],
                'obj_dur'       : 240000,
                'obj_pos_x'     : x_pos[idx],
                'obj_pos_y'     : 0.02,
                'obj_mag'       : 0.5,
                'obj_rot'       : (rots, rots),
                'obj_tilt'      : (rots, rots)},
            'difficulty'        : 0,
            'reward_port'       : rew_prob[idx],
            'response_port'     : rew_prob[idx],
            'reward_amount'     : 6})

for idx, obj_comb in enumerate(resp_obj):
    conditions += exp.make_conditions(stim_class=Panda(), stim_periods=['Cue', 'Response'], conditions={**env_key,
            'Cue': {
                'obj_id'        : cue_obj[idx],
                'obj_dur'       : 240000,
                'obj_pos_x'     : 0,
                'obj_pos_y'     : 0.02,
                'obj_mag'       : 0.5,
                'obj_rot'       : (rots, rots),
                'obj_tilt'      : (rots, rots)},                                                                       
            'Response': {
                'obj_id'        : resp_obj[idx],
                'obj_dur'       : 240000,
                'obj_pos_x'     : x_pos[idx],
                'obj_pos_y'     : 0.02,
                'obj_mag'       : 0.5,
                'obj_rot'       : (rots, rots),
                'obj_tilt'      : (rots, rots)},
            'difficulty'        : 1 ,
            'reward_port'       : rew_prob[idx],
            'response_port'     : rew_prob[idx],
            'reward_amount'     : 6})
    
# run experiments
exp.push_conditions(conditions)
exp.start()

    