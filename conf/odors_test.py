from Experiments.Center2AFC import *
from Behavior import *
from Stimuli.Odors import *
from utils.Generator import *


# define stimulus conditions
odor_ratios = [[100, 0], [90, 10], [80, 20], [70, 30], [60, 40], [50, 50]]
v_dur = 4000
o_dur = 500
o_conds = []
analysis_group = 1
for ratio in odor_ratios:
    o_conds += factorize({'probe': [1], 'movie_name': ['obj1v6'], 'movie_duration': [0], 'clip_number': [1],
                          'delivery_idx': [[1, 2]], 'odor_idx': [[1, 2]], 'odor_duration': [o_dur],
                          'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    o_conds += factorize({'probe': [2], 'movie_name': ['obj2v6'], 'movie_duration': [0], 'clip_number': [1],
                          'delivery_idx': [[2, 1]], 'odor_idx': [[2, 1]], 'odor_duration': [o_dur],
                          'dutycycle': [ratio], 'analysis_group': [analysis_group]})
    analysis_group += 1


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

logger.log_session(session_params, o_conds, '2AFC')
logger.log_conditions(['OdorCond', 'MovieCond', 'RewardCond', 'AnalysisCond'], o_conds)
exp = State()
exp.setup(logger, RPBehavior, RPMovies, session_params, o_conds)
exp.run()