import sys
import os
import configparser


class Config(object):
    def __init__(self, config_file='config.ini'):
        self._path = "%s/%s" % (sys.path[0], config_file)
        if not os.path.exists(self._path):
            raise FileNotFoundError("No such file: %s" % config_file)
        self._config = configparser.ConfigParser()
        self._config.read(self._path, encoding='utf-8-sig')

    def get(self, section, name):
        return self._config.get(section, name)

    def getint(self, section, name):
        return self._config.getint(section, name)

    def getfloat(self, section, name):
        return self._config.getfloat(section, name)

    def getfloat(self, section, name):
        return self._config.getboolean(section, name)

    def get_logger(self):
        return {
            'name': self._config.get('logger', 'name'),
            'path': self._config.get('logger', 'path'),
        }


config = Config()
