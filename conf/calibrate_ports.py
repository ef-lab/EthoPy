global logger
from Experiments.Calibrate import *


# define calibration parameters
session_params = {
    'duration'        : [20, 40, 100, 250],
    'ports'           : [1, 2],
    'pulsenum'        : [60, 40, 10, 3],
    'pulse_interval'  : [30, 10, 0, 0],
    'save'            : True,
    'setup_conf_idx'  : 1,
}

# run experiment
exp = Experiment()
exp.setup(logger, session_params)
exp.run()

