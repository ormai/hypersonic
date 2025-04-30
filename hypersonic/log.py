"""Configure logging for the app"""

import logging
from sys import stdout
from typing import override


class ColoredFormatter(logging.Formatter):
    RESET = '\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    MAGENTA = '\033[35m'
    BOLD = '\033[1m'
    FORMAT = '%(asctime)s %(filename)s:%(lineno)d %(levelname)s: %(message)s '
    FORMATTERS = {
        logging.DEBUG: logging.Formatter(MAGENTA + FORMAT + RESET),
        logging.INFO: logging.Formatter(GREEN + FORMAT + RESET),
        logging.WARNING: logging.Formatter(YELLOW + FORMAT + RESET),
        logging.ERROR: logging.Formatter(RED + FORMAT + RESET),
        logging.CRITICAL: logging.Formatter(BOLD + RED + FORMAT + RESET)
    }

    @override
    def format(self, record):
        return ColoredFormatter.FORMATTERS[record.levelno].format(record)


def get_logger(module_name: str) -> logging.Logger:
    logger = logging.getLogger(module_name)
    stream_handler = logging.StreamHandler(stream=stdout)
    stream_handler.setFormatter(ColoredFormatter())
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG if __debug__ else logging.INFO)
    return logger
