
from Experiments.Calibrate import *

# define calibration parameters
session_params = {
    'duration'        : 500,
    'probes'          : [1, 2],
    'pulsenum'        : 20,
    'pulse_interval'  : 100,
    'save'            : True,
}

# run experiment
exp = Calibrate(logger, session_params)
exp.run()

