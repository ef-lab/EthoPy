from Logger import *
from utils.Start import Welcome
import sys, utils

global logger
logger = RPLogger()                                                   # setup logger & timer
logger.log_setup()                                                    # publish IP and make setup available

# # # # Waiting for instructions loop # # # # #
while not logger.get_setup_state() == 'stopped':
    interface = Welcome(logger)
    while logger.get_setup_state() == 'ready':                        # wait for remote start
        interface.eval_input()
        time.sleep(0.2)
        logger.ping()
    if not logger.get_setup_state() == 'stopped':                     # run experiment unless stopped
        protocol = logger.get_protocol()
        exec(open(protocol).read())
        logger.update_setup_state('ready')                            # update setup state

# # # # # Exit # # # # #
logger.cleanup()
sys.exit(0)
