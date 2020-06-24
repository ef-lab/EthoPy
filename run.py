from Logger import *
import sys, utils, os

if os.uname()[4][:3] == 'arm':
    from utils.Start import PyWelcome as Welcome
else:
    from utils.Start import Welcome

global logger
logger = Logger()                                                   # setup logger & timer
logger.log_setup()                                                  # publish IP and make setup available

# # # # Waiting for instructions loop # # # # #
while not logger.get_setup_info('status') == 'exit':
    if logger.get_setup_info('status') == 'ready':
        interface = Welcome(logger)
        while logger.get_setup_info('status') == 'ready':                        # wait for remote start
            interface.eval_input()
            time.sleep(0.2)
            logger.ping()
        interface.close()
    if logger.get_setup_info('status') == 'running':   # run experiment unless stopped
        protocol = logger.get_protocol()
        exec(open(protocol).read())
        if logger.get_setup_info('status') == 'stop':
            logger.update_setup_status('ready')                            # update setup status


# # # # # Exit # # # # #
logger.cleanup()
sys.exit(0)
