# Object experiment
from Experiments.Match2Sample import *
from Behavior import*
from Stimuli.Panda import *
from utils.generator import *
from scipy import interpolate

interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x
conditions = []

exp = Experiment()

# define session parameters
session_params = {
    'trial_selection'       : 'staircase',
    'start_time'            : '13:00:00',
    'stop_time'             : '21:50:00',
    'reward'                : 'water',
    'intensity'             : 64,
    'max_reward'            : 3000,
    'min_reward'            : 500,
    'bias_window'           : 5,
    'staircase_window'      : 20,
    'stair_up'              : 0.7,
    'stair_down'            : 0.55,
    'noresponse_intertrial' : True,
    'incremental_punishment': True,
}

# define environment conditions
env_key = {
    'background_color'      : (0.1,0.1,0.1),
    'ambient_color'         : (0.1, 0.1, 0.1, 1),
    'direct1_color'         : (0.7, 0.7, 0.7, 1),
    'direct1_dir'           : (0, -20, 0),
    'direct2_color'         : (0.2, 0.2, 0.2, 1),
    'direct2_dir'           : (180, -20, 0),
    'init_ready'            : 0,
    'cue_ready'             : 100,
    'delay_ready'           : 0,
    'resp_ready'            : 0,
    'intertrial_duration'   : 1000,
    'cue_duration'          : 240000,
    'delay_duration'        : 0,
    'response_duration'     : 5000,
    'reward_duration'       : 2000,
    'punish_duration'       : 1000,
    'obj_dur'               : 240000,
    'obj_delay'             : 0,
}

np.random.seed(0)
# one static object
obj_combs = [[3, 3], [3, 3]]#, [2, 2], [2, 2]]
rew_prob = [1, 2]
obj_posX = [[0, -.25], [0, .25]]

for idx, obj_comb in enumerate(obj_combs):
    conditions += factorize({**env_key,
                            'difficulty': 0,
                            'reward_amount': 5,
                            'obj_id'    : [obj_comb],
                            'probe'     : rew_prob[idx],
                            'obj_pos_x' : obj_posX[idx],
                            'obj_pos_y' : 0,
                            'obj_mag'   : .5,
                            'obj_rot'   : 0,
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_period': [['Cue', 'Response', 'Response']]})


# two static objects (1 target + 1 distractor)
obj_combs = [[3, 4, 3], [3, 3, 4]]
rew_prob = [2, 1]
for idx, obj_comb in enumerate(obj_combs):
    conditions += factorize({**env_key,
                            'difficulty': 1,
                            'reward_amount': 5,
                            'obj_id'    : [obj_comb],
                            'probe'     : rew_prob[idx],
                            'obj_pos_x' : [[0, -.25, .25]],
                            'obj_pos_y' : 0,
                            'obj_mag'   : .5,
                            'obj_rot'   : 0,
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_period': [['Cue', 'Response', 'Response']]})


# two static objects (1 target + 2 distractors)
obj_combs = [[3, 4, 3], [3, 3, 4],[3, 1, 3], [3, 3, 1]]
rew_prob = [2, 1, 2, 1]
for idx, obj_comb in enumerate(obj_combs):
    conditions += factorize({**env_key,
                            'difficulty': 2,
                            'reward_amount': 5,
                            'obj_id'    : [obj_comb],
                            'probe'     : rew_prob[idx],
                            'obj_pos_x' : [[0, -.25, .25]],
                            'obj_pos_y' : 0,
                            'obj_mag'   : .5,
                            'obj_rot'   : 0,
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_period': [['Cue', 'Response', 'Response']]})


# two rotating objects (1 target + 2 distractors) + tilt + yaw
obj_combs = [[3, 4, 3], [3, 3, 4],[3, 1, 3], [3, 3, 1]]
rew_prob = [2, 1, 2, 1]
reps = 4
for idx, obj_comb in enumerate(obj_combs):
    for irep in range(0,reps):
        rot_f = lambda: interp((np.random.rand(3)-.5) *100)
        tilt_f = lambda: interp(np.random.rand(3)*20)
        yaw_f = lambda: interp(np.random.rand(2)*10)
        conditions += factorize({**env_key,
                                'difficulty': 3,
                                'reward_amount': 5,
                                'obj_id'    : [obj_comb],
                                'probe'     : rew_prob[idx],
                                'obj_pos_x' : [[0, -.25, .25]],
                                'obj_pos_y' : 0,
                                'obj_mag'   : .5,
                                'obj_rot'   : [[rot_f(), rot_f(), rot_f()]],
                                'obj_tilt'  : [[tilt_f(), tilt_f(), tilt_f()]],
                                'obj_yaw'   : [[yaw_f(), yaw_f(), yaw_f()]],
                                'obj_period': [['Cue', 'Response', 'Response']]})


# two rotating objects + changing light
obj_timepoints = 5
obj_combs = [[3, 4, 3], [3, 3, 4],[3, 1, 3], [3, 3, 1]]
rew_prob = [2, 1, 2, 1]
reps = 4
for idx, obj_comb in enumerate(obj_combs):
    for irep in range(0,reps):
        rot_f = lambda: interp((np.random.rand(3)-.5) *100)
        tilt_f = lambda: interp(np.random.rand(3)*20)
        yaw_f = lambda: interp(np.random.rand(2)*10)
        dir1_f = lambda: np.array([0, -20, 0]) + np.random.randn(3)*30
        dir2_f = lambda: np.array([180, -20, 0]) + np.random.randn(3)*30
        conditions += factorize({**env_key,
                                'difficulty'    : 4,
                                'reward_amount' : 5,
                                'obj_id'        : [obj_comb],
                                'probe'         : rew_prob[idx],
                                'obj_pos_x'     : [[0, -.25, .25]],
                                'obj_pos_y'     : 0,
                                'obj_mag'       : .5,
                                'obj_rot'       : [[rot_f(), rot_f(), rot_f()]],
                                'obj_tilt'      : [[tilt_f(), tilt_f(), tilt_f()]],
                                'obj_yaw'       : [[yaw_f(), yaw_f(), yaw_f()]],
                                'obj_period'    : [['Cue', 'Response', 'Response']],
                                'direct1_dir'   : [dir1_f()],
                                'direct2_dir'   : [dir2_f()]})

# run experiments

exp.setup(logger, DummyProbe, session_params, conditions)
exp.run()


