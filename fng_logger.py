import time
import logging
import logging.handlers

from fng_config import config


logger = logging.getLogger()


def setup_logger():
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(process)d-%(threadName)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = logging.handlers.RotatingFileHandler("{}/{}.{}.log".format(
        config.get_logger()['path'],
        config.get_logger()['name'],
        time.strftime("%Y-%m-%d")),
        maxBytes=10485760, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


setup_logger()
