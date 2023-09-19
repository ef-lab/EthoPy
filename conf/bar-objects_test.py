# Retinotopic mapping experiment

from Experiments.Passive import *
from Stimuli.Bar import *
from core.Behavior import *
from Stimuli.Panda import *
from utils.helper_functions import *
from scipy import interpolate
import random

interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x

# define session parameters
session_params = {
    'setup_conf_idx'        : 0,
    'trial_selection': 'fixed',
    'max_res': 1000,
}

exp = Experiment()
exp.setup(logger, Behavior, session_params)

repeat_n = 2
conditions = []
for axis in ['horizontal', 'vertical']:
    for rep in range(0, repeat_n):
        conditions += exp.make_conditions(stim_class=Bar(), conditions={
                      'center_x'            : 0,
                      'center_y'            : -0.17,
                      'bar_width'           : 4,  # degrees
                      'bar_speed'           : 10,  # degrees/sec
                      'flash_speed'         : 2,
                      'grat_width'          : 10,  # degrees
                      'grat_freq'           : 1,
                      'grid_width'          : 10,
                      'grit_freq'           : .1,
                      'style'               : 'checkerboard',  # checkerboard, grating
                      'direction'           : 1,  # 1 for UD LR, -1 for DU RL
                      'flatness_correction' : 1,
                      'intertrial_duration' : 0,
                      'axis'                : axis})

np.random.seed(0)
obj_combs = [[3, 2]]
times = 10
reps = 3
for idx, obj_comb in enumerate(obj_combs):
    for irep in range(0, reps):
        pos_x_f = lambda x: interp(np.random.rand(x) - 0.5)
        pos_y_f = lambda x: interp((np.random.rand(x) - 0.5) * 0.5)
        rot_f = lambda x: interp((np.random.rand(x)-.5) * 25)
        tilt_f = lambda x: interp(np.random.rand(x)*30)
        mag_f = lambda x: interp(np.random.rand(x) * 0.5 + 0.25)
        yaw_f = lambda x: interp(np.random.rand(x)*10)
        dir1_f = lambda: np.array([0, -20, 0]) + np.random.randn(3)*30
        dir2_f = lambda: np.array([180, -20, 0]) + np.random.randn(3)*30
        conditions += exp.make_conditions(stim_class=Panda(), conditions={
            'obj_dur': 1000,
            'obj_id': [obj_comb],
            'obj_pos_x': [[pos_x_f(times), pos_x_f(times)]],
            'obj_pos_y': [[pos_y_f(times), pos_y_f(times)]],
            'obj_mag': [[mag_f(times), mag_f(times)]],
            'obj_rot': [[rot_f(times), rot_f(times)]],
            'obj_tilt': 0,
            'obj_yaw': 0,
            'light_idx': [[1, 2]],
            'light_dir': [[dir1_f(), dir2_f()]]})

random.seed(0)
random.shuffle(conditions)

# run experiments
exp.push_conditions(conditions)
exp.start()