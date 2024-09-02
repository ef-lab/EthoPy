from Stimuli.OptoPanda import *
from Experiments.MatchToSample import *
from Behaviors.MultiPort import *
from scipy import interpolate
import numpy as np

interp = lambda x: interpolate.splev(np.linspace(0, len(x), 100),
                                     interpolate.splrep(np.linspace(0, len(x), len(x)), x)) if len(x) > 3 else x

# define session parameters
session_params = {
    'start_time'            : '00:00:00',
    'stop_time'             : '23:59:00',
    'setup_conf_idx'        : 1,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)
conditions = []

# two static objects (1 target + 1 distractor) multiple delays & rotation
cue_obj = [2, 2, 3, 3]
resp_obj = [(3, 2), (2, 3), (3, 2), (2, 3)]
rew_prob = [2, 1, 1, 2]
reps = 1
panda_obj = Opto()
panda_obj.fill_colors.set({'background': (0, 0, 0),
                      'start': (32, 32, 32),
                      'punish': (0, 0, 0)})

block = exp.Block(difficulty=0, next_up=1, next_down=0, trial_selection='staircase', metric='dprime', stair_up=1, stair_down=0.5)
for irep in range(0, reps):
    for idx, obj_comb in enumerate(resp_obj):

        # environement & light
        dir1_f = lambda: np.array([0, -20, 0]) + np.random.randn(3) * 30
        dir2_f = lambda: np.array([180, -20, 0]) + np.random.randn(3) * 30

        # object parameters
        rot_f = lambda: interp((np.random.rand(5)-.5) * 250)
        tilt_f = lambda: interp(np.random.rand(5)*30)
        yaw_f = lambda: interp(np.random.rand(5)*10)

        conditions += exp.make_conditions(stim_class=panda_obj, stim_periods=['Cue', 'Response'], conditions={**block.dict(),
            'Cue': {
                'obj_id'        : cue_obj[idx],
                'obj_dur'       : 2000,
                'obj_pos_x'     : 0,
                'obj_mag'       : .5,
                'obj_rot'       : (rot_f()),
                'obj_tilt'      : 0,
                'obj_yaw'       : 0,
                'opt_dutycycle'     : [0, 50],
                'opt_duration'      : 2000},
            'Response': {
                'obj_id'        : obj_comb,
                'obj_dur'       : 5000,
                'obj_pos_x'     : (-.25, .25),
                'obj_mag'       : .5,
                'obj_rot'       : (rot_f(), rot_f()),
                'obj_tilt'      : 0,
                'obj_yaw'       : 0,
                'opt_dutycycle'     : 0,
                'opt_duration'      : 0},
            'reward_port'       : rew_prob[idx],
            'response_port'     : rew_prob[idx],
            'cue_ready'         : 100,
            'cue_duration'      : 2000,
            'delay_duration'    : 100,
            'response_duration' : 5000,
            'reward_duration'   : 2000,
            'punish_duration'   : 500,
            'reward_amount'     : 6})


# run experiments
exp.push_conditions(conditions)
exp.start()
