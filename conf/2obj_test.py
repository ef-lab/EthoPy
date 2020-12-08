# Object experiment

from Experiments.Passive import *
from Behavior import *
from Stimuli.Panda3D import *
from utils.Generator import *
from scipy import interpolate

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
    'stim_duration'         : 10,
}

interp = lambda x: interpolate.splev(np.linspace(0,len(x),100), interpolate.splrep(np.linspace(0, len(x),len(x)), x))
times = env_key['stim_duration']
repeat_n = 10
conditions = []
for rep in range(0, repeat_n):
    rot_f = lambda x: interp(np.random.rand(x) * 200)
    pos_x_f = lambda x: interp(np.random.rand(x) - 0.5)
    pos_y_f = lambda x: interp((np.random.rand(x) - 0.5)*0.5)
    mag_f = lambda x: interp(np.random.rand(x)*0.5 + 0.25)
    tilt_f = lambda x: interp(np.random.rand(x)*10)
    yaw_f = lambda x: interp(np.random.rand(x)*10)

    conditions += factorize({**env_key,
                            'object_id' : [[1,2]],
                            'obj_pos_x' : [[pos_x_f(times), pos_x_f(times)]],
                            'obj_pos_y' : [[pos_y_f(times), pos_y_f(times)]],
                            'obj_mag'   : [[mag_f(times), mag_f(times)]],
                            'obj_rot'   : [[rot_f(times),rot_f(times)]],
                            'obj_tilt'  : [[tilt_f(times),tilt_f(times)]],
                            'obj_yaw'   : [[yaw_f(times),yaw_f(times)]]})

# run experiments
exp = State()
exp.setup(logger, DummyProbe, Panda3D, session_params, conditions)
exp.run()
