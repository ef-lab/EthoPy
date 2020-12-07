# Object experiment

from Experiments.Passive import *
from Behavior import *
from Stimuli.Panda3D import *
from utils.Generator import *
from scipy import interpolate

interp = lambda x: interpolate.splev(np.linspace(0,len(x),100), interpolate.splrep(np.linspace(0, len(x),len(x)), x))\
    if len(x)>3 else x
conditions = []

# define session parameters
session_params = {
    'trial_selection'    : 'fixed',
    'intensity'          : 255,
}

# define environment conditions
env_key = {
    'ambient_color'         : (0.1, 0.1, 0.1, 1),
    'direct1_color'         : (0.8, 0.8, 0.8, 1),
    'direct1_dir'           : (0, -20, 0),
    'direct2_color'         : (0.2, 0.2, 0.2, 1),
    'direct2_dir'           : (180, -20, 0),
    'intertrial_duration'   : 0,
    'stim_duration'         : 4,
    'delay_duration'        : 0,
    'reward_amount'         : 8,
    'timeout_duration'      : 1000,
}

obj_combs = [[1, 1, 2],[1, 2, 1],[2, 1, 2],[2, 2, 1]]
rew_prob = [1,2,2,1]
for idx, obj_comb in enumerate(obj_combs):
    rot_f = lambda : interp(np.random.rand(env_key['stim_duration']) *200)
    conditions += factorize({**env_key,
                            'obj_id'    : [obj_comb],
                            'probe'     : rew_prob[idx],
                            'obj_pos_x' : [[0,-.5,.5]],
                            'obj_pos_y' : 0,
                            'obj_mag'   : .5,
                            'obj_rot'   : [[rot_f(),rot_f(), rot_f()]],
                            'obj_tilt'  : 0,
                            'obj_yaw'   : 0,
                            'obj_delay' : 0,
                            'obj_dur'   : 3000,
                            'obj_period': [['cue','trial','trial']]})

# run experiments
exp = State()
exp.setup(logger, DummyProbe, Panda3D, session_params, conditions)
exp.run()
