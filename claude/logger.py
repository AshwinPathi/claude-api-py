import logging

logger = logging

OLD_FORMAT = '%(asctime)s:%(name)s:%(levelname)s - %(message)s'
FORMAT = '[%(asctime)s:%(name)s:%(levelname)s][%(filename)s:%(lineno)s - %(funcName)s() ] %(message)s'

logger.basicConfig(
    level=logging.DEBUG,
    format=FORMAT,
    datefmt='%d-%b-%y %H:%M:%S'
)
