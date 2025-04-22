"""Configure logging for the app"""

from logging import getLogger, DEBUG, INFO, StreamHandler, Logger
from sys import stdout


def get_logger(module_name: str) -> Logger:
    logger = getLogger(module_name)
    logger.addHandler(StreamHandler(stream=stdout))
    logger.setLevel(DEBUG if __debug__ else INFO)
    return logger
