from Experiments.ProbeTest import *

# define calibration parameters
session_params = {
    'duration'        : [20, 100, 500,1000],
    'probes'          : [1, 2],
    'pulsenum'        : [20, 20, 10, 1],
    'pulse_interval'  : [30, 200, 200, 500],
}

# run experiment
exp = ProbeTest(logger, session_params)
exp.run()

