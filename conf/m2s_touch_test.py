# Object experiment

from Experiments.Match2Sample import *
from Behavior import *
from Stimuli.Panda3D import *
from utils.Generator import *
from scipy import interpolate

interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x
conditions = []

# define session parameters
session_params = {
    'trial_selection'    : 'staircase',
    'start_time'         : '00:00:00',
    'stop_time'          : '23:57:00',
    'reward'             : 'water',
    'intensity'          : 64,
    'max_reward'         : 3000,
    'bias_window'        : 5,
    'staircase_window'   : 10,
    'stair_up'           : 0.7,
    'stair_down'         : 0.6,
    'noresponse_intertrial'  : True,
    'resp_cond'          : 'correct_loc'
}

# define environment conditions
env_key = {
    'background_color'      : (.01, .01, .01),
    'ambient_color'         : (0.1, 0.1, 0.1, 1),
    'direct1_color'         : (0.7, 0.7, 0.7, 1),
    'direct1_dir'           : (0, -20, 0),
    'direct2_color'         : (0.2, 0.2, 0.2, 1),
    'direct2_dir'           : (180, -20, 0),
    'init_ready'            : 0,
    'cue_ready'             : 100,
    'delay_ready'           : 0,
    'resp_ready'            : 0,
    'intertrial_duration'   : 0,
    'cue_duration'          : 20000,
    'delay_duration'        : 5000,
    'response_duration'     : 4000,
    'reward_amount'         : 8,
    'reward_duration'       : 2000,
    'punish_duration'       : 1000,
    'obj_dur'               : 20000,
    'obj_delay'             : 0,
    'ready_loc'             : [[0,0]],
    'probe'                 : 1
}

np.random.seed(0)
conditions += factorize({**env_key,
                        'difficulty': 1,
                        'obj_id'    : 1,
                        'correct_loc': [[0, 0]],
                        'obj_pos_x' : 0,
                        'obj_pos_y' : 0,
                        'obj_mag'   : 0,
                        'obj_rot'   : 0,
                        'obj_tilt'  : 0,
                        'obj_yaw'   : 0,
                        'obj_period': 'Response',
                        'cue_ready' : 0,
                        'response_duration': 240000,
                        'obj_dur'   : 0,
                        'touch_area': [[(500,300)]]})

obj_timepoints = 5
obj_combs = [[1, 1], [1, 1], [2, 2], [2, 2]]
correct_loc = [(-0.25,0),(0.25,0),(0.25,0),(-0.25,0)]
obj_posX = [[0, -.25], [0, .25], [0, .25], [0, -.25]]
for idx, obj_comb in enumerate(obj_combs):
    rot_f = lambda: interp(np.random.rand(obj_timepoints) *200)
    conditions += factorize({**env_key,
                            'difficulty': 2,
                            'obj_id'    : [obj_comb],
                            'correct_loc': [correct_loc[idx]],
                            'obj_pos_x' : [obj_posX[idx]],
                            'obj_pos_y' : [[-0.13,-0.13,-0.13]],
                            'obj_mag'   : .5,
                            'obj_rot'   : [[rot_f(), rot_f()]],
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_period': [['Cue', 'Response']]})

obj_combs = [[1, 1, 2], [1, 2, 1], [2, 1, 2], [2, 2, 1]]
correct_loc = [[-0.25,0],[0.25,0],[0.25,0],[-0.25,0]]
for idx, obj_comb in enumerate(obj_combs):
    rot_f = lambda: interp(np.random.rand(obj_timepoints) *200)
    conditions += factorize({**env_key,
                            'difficulty':3,
                            'obj_id'    : [obj_comb],
                            'correct_loc': [correct_loc[idx]],
                            'obj_pos_x' : [[0, -.25, .25]],
                            'obj_pos_y' : [[-0.13,-0.13,-0.13]],
                            'obj_mag'   : .5,
                            'obj_rot'   : [[rot_f(), rot_f(), rot_f()]],
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_period': [['Cue', 'Response', 'Response']]})

# run experiments
exp = State()
exp.setup(logger, TouchBehavior, Panda3D, session_params, conditions)
exp.run()


