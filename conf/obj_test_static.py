from Experiments.Passive import *
from core.Behavior import *
from Stimuli.Panda import *
from utils.helper_functions import *


# define session parameters
session_params = {
    'setup_conf_idx'        : 2,
    'trial_selection': 'fixed',
    'max_res': 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

# two static objects (1 target + 1 distractor) multiple delays & rotation
np.random.seed(0)
reps = 1

conditions = exp.make_conditions(stim_class=Panda(), conditions={
    'background_color': [[1,1,1]],
    'obj_dur': 4000,
    'obj_id': 4,
    'obj_pos_x': 0,
    'obj_pos_y': 0,
    'obj_mag': .5,
    'obj_rot': -0,
    'obj_tilt': -0,
    'obj_yaw': 0,
    'light_idx': [[1, 2]],
    'light_dir': [[[0, -20, 0], [180, -20, 0]]]})

# run experiments
exp.push_conditions(conditions)
exp.start()
