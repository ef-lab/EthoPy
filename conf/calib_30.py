
from Experiments.Calibrate import *

# define calibration parameters
session_params = {
    'duration'        : 30,
    'probes'          : [1,2],
    'pulsenum'        : 300,
    'pulse_interval'  : 50,
    'save'            : True,
}

# run experiment
exp = Calibrate(logger, session_params)
exp.run()

