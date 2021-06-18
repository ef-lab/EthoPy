from core.Logger import *
import sys
global logger
from Experiments.Match2Sample import *
from Behaviors.MultiPort import *
from Stimuli.Panda import *
from utils.helper_functions import *
from scipy import interpolate
import numpy as np
interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x

# define session parameters
session_params = {
    'start_time'            : '00:00:00',
    'stop_time'             : '23:45:00',
}

exp = Experiment()
exp.setup(logger, DummyPorts, session_params)

# define environment conditions
base_key = {'cue_ready'             : 100,
            'cue_duration'          : 240000,
            'delay_duration'        : 300,
            'response_duration'     : 5000,
            'reward_duration'       : 2000,
            'punish_duration'       : 5000,
            'obj_dur'               : 240000,
            'obj_delay'             : 0,
            'reward_amount'         : 6}

np.random.seed(0)
conditions = []

# two static objects (1 target + 1 distractor) multiple delays & rotation
obj_combs = [[2, 3, 2], [2, 2, 3], [3, 3, 2], [3, 2, 3]]
rew_prob = [2, 1, 1, 2]
reps = 2
for idx, obj_comb in enumerate(obj_combs):
    for irep in range(0, reps):
        rot_f = lambda: interp((np.random.rand(30)-.5) * 150)
        tilt_f = lambda: interp(np.random.rand(3)*30)
        yaw_f = lambda: interp(np.random.rand(2)*10)
        dir1_f = lambda: np.array([0, -20, 0]) + np.random.randn(3)*30
        dir2_f = lambda: np.array([180, -20, 0]) + np.random.randn(3)*30
        key =  {**base_key,
                'difficulty'    : 0,
                'obj_id'        : [obj_comb],
                'reward_port'   : rew_prob[idx],
                'response_port' : rew_prob[idx],
                'obj_pos_x'     : [[0, -.25, .25]],
                'obj_pos_y'     : 0,
                'obj_mag'       : .5,
                'obj_rot'       : [[rot_f(), rot_f(), rot_f()]],
                'obj_tilt'      : 0,
                'obj_yaw'       : 0,
                'obj_period'    : [['Cue', 'Response', 'Response']],
                'direct1_dir'   : [dir1_f()],
                'direct2_dir'   : [dir2_f()]}
        conditions += exp.make_conditions(Panda, key)

# run experiments
exp.push_conditions(conditions)
exp.start()
