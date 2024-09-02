from core.Logger import *
import sys
from utils.Start import *
error = False

global logger
protocol = sys.argv[1] if len(sys.argv) > 1 else False
logger = Logger(protocol=protocol)   # setup logger

# # # # Waiting for instructions loop # # # # #
while not logger.setup_status == 'exit':
    if logger.setup_status != 'running': PyWelcome(logger)
    if logger.setup_status == 'running':   # run experiment unless stopped
        try:
            if logger.get_protocol(): exec(open(logger.get_protocol()).read())
        except Exception as e:
            error = e
            logger.update_setup_info({'state': 'ERROR!', 'notes': str(e), 'status': 'exit'})
        if logger.manual_run:  logger.update_setup_info({'status': 'exit'}); break
        elif logger.setup_status not in ['exit', 'running']:  # restart if session ended
            logger.update_setup_info({'status': 'ready'})  # restart
    time.sleep(.1)

# # # # # Exit # # # # #
logger.cleanup()
if error: print(error)
sys.exit(0)

