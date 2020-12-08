# Object experiment

from Experiments.Passive import *
from Behavior import *
from Stimuli.Panda3D import *
from utils.Generator import *

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
    'stim_duration'         : 5,
}

timepoints = 1
rand = lambda x: np.random.rand(x)
repeat_n = 2
conditions = []
for rep in range(0, repeat_n):
    rot_f = rand(timepoints) * 200
    pos_x_f = rand(timepoints) - 0.5
    pos_y_f = (rand(timepoints) - 0.5)*0.5
    mag_f = rand(timepoints)*0.5 + 0.25
    tilt_f = rand(timepoints)*10
    yaw_f = rand(timepoints)*10
    for obj in [1, 2]:
        conditions += factorize({**env_key,
                                'object_id' : [[obj]],
                                'obj_pos_x' : [[pos_x_f]],
                                'obj_pos_y' : [[pos_y_f]],
                                'obj_mag'   : [[mag_f]],
                                'obj_rot'   : [[rot_f]],
                                'obj_tilt'  : [[tilt_f]],
                                'obj_yaw'   : [[yaw_f]]})

# run experiments
exp = State()
exp.setup(logger, DummyProbe, Panda3D, session_params, conditions)
exp.run()
