# visual-olfactory task with 2 objects (1 and 2) without background and 2 clips/object and 2 odors (odor_idx 1 and 2)
# reward amount = 8 microL

from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.SmellyMovies import *
from utils.factorize import *

# define stimulus conditions
analysis_group = 1
odor_ratios = [[100, 0], [85, 15], [65, 35], [50, 50]]
v_dur = 4000
o_dur = 500
cond_tables = ['OdorCond', 'MovieCond', 'RewardCond', 'AnalysisCond']
vo_conds = []
v_conds = []
o_conds = []
for ratio in odor_ratios:
    vo_conds += factorize({'probe': [1], 'movie_name': ['obj1v6'], 'movie_duration': [v_dur], 'clip_number': [1],
                           'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'odor_duration': [o_dur],
                           'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    vo_conds += factorize({'probe': [2], 'movie_name': ['obj2v6'], 'movie_duration': [v_dur], 'clip_number': [1],
                           'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'odor_duration': [o_dur],
                           'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    analysis_group += 1

for ratio in odor_ratios:
    o_conds += factorize({'probe': [1], 'movie_name': ['obj1v6'], 'movie_duration': [0], 'clip_number': [1],
                          'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'odor_duration': [o_dur],
                          'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    o_conds += factorize({'probe': [2], 'movie_name': ['obj2v6'], 'movie_duration': [0], 'clip_number': [1],
                          'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'odor_duration': [o_dur],
                          'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    analysis_group += 1

v_conds += factorize({'probe': [1], 'movie_name': ['obj1v6'], 'movie_duration': [v_dur], 'clip_number': [1],
                      'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'odor_duration': [0],
                      'dutycycle': [[0, 0]], 'analysis_group': [analysis_group]})
v_conds += factorize({'probe': [2], 'movie_name': ['obj2v6'], 'movie_duration': [v_dur], 'clip_number': [1],
                      'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'odor_duration': [0],
                      'dutycycle': [[0, 0]], 'analysis_group': [analysis_group]})

# define session parameters
session_params = {
    'trial_duration'     : 5000,
    'intertrial_duration': 0,
    'timeout_duration'   : 4000,
    'delay_duration'     : 0,
    'response_interval'  : 1000,
    'init_duration'      : 0,
    'reward_amount'      : 8,
    'randomization'      : 'bias',
    'start_time'         : '10:00:00',
    'stop_time'          : '22:00:00',
    'reward'             : 'water',
    'max_reward'         : 3000,
}

logger.log_session(session_params, vo_conds + v_conds + o_conds, '2AFC')
logger.log_conditions(['OdorCond', 'MovieCond', 'RewardCond', 'AnalysisCond'], vo_conds + v_conds + o_conds)
conditions = vo_conds + vo_conds + v_conds + v_conds + o_conds

# run experiment
exp = State()
exp.setup(logger, RPBehavior, SmellyMovies, session_params, conditions)
exp.run()

