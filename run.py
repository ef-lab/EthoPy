from Logger import *
import sys
from utils.Start import *

global logger
protocol = int(sys.argv[1]) if len(sys.argv) > 1 else False
logger = Logger(protocol=protocol)   # setup logger

# # # # Waiting for instructions loop # # # # #
while not logger.setup_status == 'exit':
    if logger.is_pi and logger.setup_status != 'running': PyWelcome(logger)
    if logger.setup_status == 'running':   # run experiment unless stopped
        exec(open(logger.get_protocol()).read())
        if protocol: break
        elif logger.setup_status not in ['exit', 'running']:  # restart if session ended
            logger.update_setup_info({'status': 'ready'})  # restart
    time.sleep(.1)

# # # # # Exit # # # # #
logger.cleanup()
sys.exit(0)
