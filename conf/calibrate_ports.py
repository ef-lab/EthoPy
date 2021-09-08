global logger
from Experiments.Calibrate import *


# define calibration parameters
session_params = {
    'duration'        : [20, 30, 40, 150],
    'ports'           : [1, 2],
    'pulsenum'        : [600, 300, 200, 100],
    'pulse_interval'  : [40, 40, 40, 40],
    'save'            : True,
    'setup_conf_idx'  : 1,
}

# run experiment
exp = Experiment()
exp.setup(logger, session_params)
exp.run()

