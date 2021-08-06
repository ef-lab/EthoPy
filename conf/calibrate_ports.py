global logger
from Experiments.Calibrate import *


# define calibration parameters
session_params = {
    'duration'        : [20, 40, 100, 250],
    'ports'           : [1, 2],
    'pulsenum'        : [600, 400, 100, 30],
    'pulse_interval'  : [30, 10, 0, 0],
    'save'            : True,
}

# run experiment
exp = Experiment()
exp.setup(logger, session_params)
exp.run()

