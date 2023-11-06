from Experiments.Passive import *
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

np.random.seed(0)
obj_combs = [[3, 2]]
times = 10
reps = 1

panda_obj = Panda()
panda_obj.record()

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
        conditions += exp.make_conditions(stim_class=panda_obj, conditions={
            'background_color': (0.5, 0.5, 0.5),
            'obj_dur': 3000,
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