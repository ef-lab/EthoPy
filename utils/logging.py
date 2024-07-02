"""Module for configuring and handling logging across the application.

This module provides functionalities to set up logging with various handlers,
including file and console handlers, with customizable formatting and levels.
It allows for easy integration and consistent logging practices throughout
the application.
"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler


class CustomFormatter(logging.Formatter):
    """A custom log formatter that provides colored output and additional information.

    This formatter extends the base `logging.Formatter` class and adds custom formatting options
    for different log levels. It provides colored output for different log levels and includes
    additional information such as the timestamp, log level, message, filename, and line number.

    Attributes:
        grey (str): ANSI escape sequence for grey color.
        yellow (str): ANSI escape sequence for yellow color.
        red (str): ANSI escape sequence for red color.
        bold_red (str): ANSI escape sequence for bold red color.
        reset (str): ANSI escape sequence to reset color.
        custom_format (str): Format string for log records with timestamp, log level, message,
            filename, and line number.
        info_format (str): Format string for log records with timestamp, log level, and message.
        FORMATS (dict): Dictionary mapping log levels to their respective format strings.

    Methods:
        format(record): Formats the log record using the appropriate format string based on the
            log level.
    """
    def __init__(self):
        super().__init__()
        self.grey = "\x1b[38;21m"
        self.yellow = "\x1b[33;21m"
        self.red = "\x1b[31;21m"
        self.bold_red = "\x1b[31;1m"
        self.reset = "\x1b[0m"
        self.custom_format = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
        self.info_format = "%(asctime)s - %(levelname)s - %(message)s"
        self.FORMATS = {
            logging.DEBUG: self.grey + self.custom_format + self.reset,
            logging.INFO: self.grey + self.info_format + self.reset,
            logging.WARNING: self.yellow + self.custom_format + self.reset,
            logging.ERROR: self.red + self.custom_format + self.reset,
            logging.CRITICAL: self.bold_red + self.custom_format + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(console_log):
    """
    Set up logging configuration.

    Args:
        console_log (bool): Flag indicating whether to enable console logging.

    Returns:
        None
    """
    log_file_path = os.path.join("log.txt")

    # Load logging configuration from a JSON file
    with open('local_conf.json', 'r', encoding='utf-8') as config_file:
        config = json.load(config_file)

    # Extract the logging level from the configuration
    log_level_str = config.get('log_level', 'INFO')  # Default to INFO if not specified
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Create and configure a rotating file handler
    rotating_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=30*1024*1024,  # 30 MB
        backupCount=5
    )
    rotating_handler.setLevel(log_level)
    frmt = "%(asctime)-15s - (%(filename)s:%(lineno)d) - %(levelname)s - %(message)s"
    rotating_handler.setFormatter(logging.Formatter(frmt))
    # rotating_handler.setFormatter(CustomFormatter())  # Use CustomFormatter here
    # Configure the root logger
    logging.basicConfig(
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
        format="%(asctime)-15s %(message)s",
        handlers=[rotating_handler]
    )

    # Add a console handler with colored output
    if console_log:
        console = logging.StreamHandler()
        console.setLevel(log_level)
        console.setFormatter(CustomFormatter())
        logging.getLogger("").addHandler(console)
