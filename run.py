import logging
import sys
import time
import traceback

from core.Logger import Logger
from utils.logging import setup_logging
from utils.Start import PyWelcome

setup_logging(False)

ERROR = None
protocol = sys.argv[1] if len(sys.argv) > 1 else False
logger = Logger(protocol=protocol)   # setup logger

# # # # Waiting for instructions loop # # # # #
while logger.setup_status != 'exit':
    if logger.setup_status != 'running':
        PyWelcome(logger)
    if logger.setup_status == 'running':   # run experiment unless stopped
        try:
            if logger.update_protocol():
                exec(open(logger.protocol_path, encoding='utf-8').read())
        except Exception as e:
            ERROR = traceback.format_exc()
            logger.update_setup_info({'state': 'ERROR!', 'notes': str(e), 'status': 'exit'})
        if logger.manual_run:
            logger.update_setup_info({'status': 'exit'})
            break
        elif logger.setup_status not in ['exit', 'running']:  # restart if session ended
            logger.update_setup_info({'status': 'ready'})  # restart
    time.sleep(.1)

# # # # # Exit # # # # #
logger.cleanup()
if ERROR:
    logging.error("ERROR %s", ERROR)
sys.exit(0)
