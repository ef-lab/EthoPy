
from Experiments.Calibrate import *

# define calibration parameters
session_params = {
    'duration'        : [30, 100, 500],
    'probes'          : [1, 2],
    'pulsenum'        : [300, 150, 20],
    'pulse_interval'  : [50, 100, 100],
    'save'            : True,
}

# run experiment
exp = Calibrate(logger, session_params)
exp.run()

