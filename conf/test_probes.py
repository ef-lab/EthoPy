from Experiments.ProbeTest import *

# define calibration parameters
session_params = {
    'duration'        : [30, 100, 500, 1000, 100],
    'probes'          : [1, 2],
    'pulsenum'        : [30, 20, 5, 1, 5],
    'pulse_interval'  : [30, 200, 200, 500, 200],
}

# run experiment
exp = ProbeTest(logger, session_params)
exp.run()

