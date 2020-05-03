
from Experiments.Calibrate import *

# define calibration parameters
session_params = {
    'duration'        : 30,
    'probes'          : [1, 2],
    'pulsenum'        : 150,
    'pulse_interval'  : 100,
    'save'            : True,
}

# run experiment
exp = Calibrate(logger, session_params)
exp.run()

