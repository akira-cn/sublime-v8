# coding=utf-8

import logging
import logging.handlers
import datetime
import os

logging.basicConfig()

class logger():
    _loggers = {}

    def __init__(self, name = 'default'):
        self.name = name
        self.logger = logger._loggers.get(name)

        if(not self.logger):
            self.logger = logging.getLogger(self.name)
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(thread)d %(asctime)s %(levelname)s %(message)s')
            filehandler = logging.handlers.TimedRotatingFileHandler(
                os.path.join(os.path.dirname(__file__), "logs","log"), 'D', 1, 7)
            filehandler.suffix = "%Y-%m-%d"
            filehandler.setFormatter(formatter)
            self.logger.addHandler(filehandler)
            logger._loggers[name] = self.logger

    def instance(self):
        return self.logger