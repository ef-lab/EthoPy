from Logger import *
import sys
from utils.Start import *

global logger
protocol = int(sys.argv[1]) if len(sys.argv) > 1 else False
logger = Logger(log_setup=True, protocol=protocol)   # setup logger

# # # # Waiting for instructions loop # # # # #
while not logger.setup_status == 'exit':
    if logger.is_pi: PyWelcome(logger)
    if logger.setup_status == 'running':   # run experiment unless stopped
        exec(open(logger.get_protocol()).read())
        status = 'ready' if logger.setup_status == 'stop' and not protocol else 'exit'
        logger.update_setup_info('status', status, nowait=True)  # update setup status
    time.sleep(2)

# # # # # Exit # # # # #
logger.cleanup()
sys.exit(0)
