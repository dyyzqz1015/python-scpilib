# -*- coding: utf-8 -*-
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


from __future__ import print_function
try:
    import __builtin__
except Exception:
    # Python 3
    import builtins as __builtin__
from datetime import datetime as _datetime
import logging as _logging
from logging import handlers as _handlers
from multiprocessing import current_process as _current_process
from numpy import array, append
import os
from time import time
from threading import currentThread as _current_thread
from threading import Lock as _Lock
from weakref import ref as _weakref


__author__ = "Sergi Blanch-Torné"
__email__ = "sblanch@cells.es"
__copyright__ = "Copyright 2015, CELLS / ALBA Synchrotron"
__license__ = "GPLv3+"


global lock
lock = _Lock()
_debug_ = False
_log2file_ = True
_timeit_collect_ = False
_deprecate_collect_ = True


def scpi_debug(value):
    global _debug_
    _debug_ = value


def scpi_log2file(value):
    global _log2file_
    _log2file_ = value


def scpi_timeit_collection(value):
    global _timeit_collect_
    _timeit_collect_ = value


logger_NOTSET = _logging.NOTSET  # 0
logger_CRITICAL = _logging.CRITICAL  # 50
logger_ERROR = _logging.ERROR  # 40
logger_WARNING = _logging.WARNING  # 30
logger_INFO = _logging.INFO  # 20
logger_DEBUG = _logging.DEBUG  # 10


__all__ = ["scpi_debug", "scpi_log2file", "scpi_timeit_collection",
           "trace", "timeit", "deprecated",
           "timeit_collection", "deprecation_collection",
           "Logger", "logger_DEBUG", "logger_INFO", "logger_WARNING",
           "logger_ERROR", "logger_CRITICAL", "logger_NOTSET"]


timeit_collection = {}
deprecation_collection = {}
deprecation_arguments = {}


def debug_stream(msg):
    __builtin__.print("{0:f} -- {1}".format(time(), msg))


def _get_printer(obj):
    if hasattr(obj, "debug_stream"):
        return obj.debug_stream
    return debug_stream


def trace(method):
    def _compact_args(lst_args, dct_args):
        lst_str = "*args: {0}".format(lst_args) if len(lst_args) > 0 else ""
        dct_str = "**kwargs: {0}".format(dct_args) if len(dct_args) > 0 else ""
        if len(lst_str) > 0 and len(dct_args) > 0:
            return "{0}, {1}".format(lst_str, dct_str)
        elif len(lst_str) > 0:
            return "{0}".format(lst_str)
        elif len(dct_str) > 0:
            return "{0}".format(dct_str)
        return ""

    def _compact_answer(answer):
        if isinstance(answer, str) and len(answer) > 100:
            return "{0}...{1}".format(answer[:25], answer[-25:])
        return "{0}".format(answer)

    def logging(*args, **kwargs):
        if _debug_:
            self = args[0]
            klass = self.__class__.__name__
            method_name = method.__name__
            args_str = _compact_args(args[1:], kwargs)
            printer = _get_printer(self)
            printer("> {0}.{1}({2})"
                    "".format(klass, method_name, args_str))
        answer = method(*args, **kwargs)
        if _debug_:
            answer_str = _compact_answer(answer)
            printer("< {0}.{1}: {2}"
                    "".format(klass, method_name, answer_str))
        return answer
    return logging


def timeit(method):
    def measure(*args, **kwargs):
        if _timeit_collect_:
            self = args[0]
            klass = self.__class__.__name__
            if klass not in timeit_collection:
                timeit_collection[klass] = {}
            method_name = method.__name__
            if method_name not in timeit_collection[klass]:
                timeit_collection[klass][method_name] = array([])
            t_0 = time()
        answer = method(*args, **kwargs)
        if _timeit_collect_:
            t_diff = time()-t_0
            timeit_collection[klass][method_name] = append(
                timeit_collection[klass][method_name], t_diff)
        return answer

    return measure


def deprecated(method):
    def collect(*args, **kwargs):
        if _deprecate_collect_:
            self = args[0]
            klass = self.__class__.__name__
            if klass not in deprecation_collection:
                deprecation_collection[klass] = {}
            method_name = method.__name__
            if method_name not in deprecation_collection[klass]:
                deprecation_collection[klass][method_name] = 0
        answer = method(*args, **kwargs)
        if _deprecate_collect_:
            deprecation_collection[klass][method_name] += 1
        return answer

    return collect


def deprecated_argument(class_name, method_name, argument):
    if _deprecate_collect_:
        dct = deprecation_arguments
        if class_name not in dct:
            dct[class_name] = {}
        class_dct = dct[class_name]
        if method_name not in class_dct:
            class_dct[method_name] = {}
        method_dct = class_dct[method_name]
        if argument not in method_dct:
            method_dct[argument] = 0
        method_dct[argument] += 1


class Logger(object):
    '''This class is a very basic debugging flag mode used as a super class
       for the other classes in this library.
    '''

    _name = None
    _level_str = {logger_NOTSET:   '',
                  logger_CRITICAL: 'CRITICAL',
                  logger_ERROR:    'ERROR',
                  logger_WARNING:  'WARNING',
                  logger_INFO:     'INFO',
                  logger_DEBUG:    'DEBUG'}

    def __init__(self, name="Logger", logger_name=None, log2file=False,
                 debug=False,
                 loggerName=None,
                 *args, **kwargs):
        super(Logger, self).__init__()
        if loggerName is not None:
            deprecated_argument("Logger", "__init__", "loggerName")
            if logger_name is None:
                logger_name = loggerName
        self._name = name
        self.__debug_flag = None
        self.__log2file = log2file
        self.__logger_name = logger_name or "SCPI"
        self.__logging_folder = None
        self.__logging_file = None
        self.__logger_obj = _logging.getLogger(self.__logger_name)
        self._handler = None
        # setup ---
        self.enable_log(True)
        if debug or _debug_:
            self.log_level = logger_DEBUG
        else:
            self.log_level = logger_INFO
        if _log2file_:
            self.log2file(True)
        self.logging_file()
        if not len(self.__logger_obj.handlers):
            self.__logger_obj.setLevel(logger_DEBUG)
            self._handler = \
                _handlers.RotatingFileHandler(self.__logging_file,
                                              maxBytes=10000000,
                                              backupCount=5)
            self._handler.setLevel(logger_NOTSET)
            formatter = _logging.Formatter('%(asctime)s - %(levelname)-7s - '
                                           '%(name)s - %(message)s')
            self._handler.setFormatter(formatter)
            self.__logger_obj.addHandler(self._handler)
        else:
            self._handler = self.__logger_obj.handlers[0]

    @property
    def name(self):
        return self._name

    @property
    def depth(self):
        depth = 0
        if hasattr(self, '_parent'):
            parent = self.parent
            while parent is not None:
                parent = parent.parent
                depth += 1
        return depth

    @property
    def logger_obj(self):
        return self.__logger_obj

    @property
    @deprecated
    def devlogger(self):
        return self.logger_obj

    @logger_obj.setter
    def logger_obj(self, obj):
        self.__logger_obj = obj

    @devlogger.setter
    @deprecated
    def devlogger(self, obj):
        self.logger_obj = obj

    @property
    def handler(self):
        return self._handler

    def add_handler(self, handler):
        self.__logger_obj.addHandler(handler)

    @deprecated
    def addHandler(self, *args, **kwargs):
        return self.add_handler(*args, **kwargs)

    def remove_handler(self, handler=None):
        if handler:
            self.__logger_obj.removeHandler(handler)
        else:
            self.__logger_obj.removeHandler(self._handler)

    @deprecated
    def removeHandler(self, *args, **kwargs):
        return self.remove_handler(*args, **kwargs)

    def replace_handler(self, handler):
        self.__logger_obj.removeHandler(self._handler)
        self.__logger_obj.addHandler(handler)
        self._handler = handler

    @deprecated
    def replaceHandler(self, *args, **kwargs):
        return self.replace_handler(*args, **kwargs)

    def logging_folder(self):
        if self.__logging_folder is None:
            logging_folder = "/var/log/{0}".format(self.__logger_name)
            if not self.__build_logging_folder(logging_folder):
                logging_folder = "/tmp/log/{0}".format(self.__logger_name)
                if not self.__build_logging_folder(logging_folder):
                    raise SystemError("No folder for logging available")
            self.__logging_folder = logging_folder
        else:
            if not self.__build_logging_folder(self.__logging_folder):
                raise SystemError("No folder for logging available")
        return self.__logging_folder

    @deprecated
    def loggingFolder(self):
        return self.logging_folder()

    def __build_logging_folder(self, folder):
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            return True
        except Exception:
            return False

    @deprecated
    def __buildLoggingFolder(self, *args, **kwargs):
        return self.__build_logging_folder(*args, **kwargs)

    def logging_file(self):
        if self.__logging_file is None:
            self.__logging_file = "{0}/{1}.log".format(
                self.logging_folder(), self.__logger_name)
        return self.__logging_file

    @deprecated
    def loggingFile(self):
        return self.logging_file()

    def log2file(self, boolean):
        if type(boolean) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__log2file = boolean

    @deprecated
    def log2File(self, *args, **kwargs):
        return self.log2file(*args, **kwargs)

    def enable_log(self, dbg=False):
        if type(dbg) is not bool:
            raise AssertionError("The parameter must be a boolean")
        self.__debug_flag = dbg

    @deprecated
    def logEnable(self, *args, **kwargs):
        self.enable_log(*args, **kwargs)

    def log_state(self):
        return self.__debug_flag

    @deprecated
    def logState(self):
        return self.log_state()

    @property
    def log_level(self):
        return self.__logger_obj.level

    @log_level.setter
    def log_level(self, level):
        try:
            self.__logger_obj.setLevel(int(level))
        except Exception:
            raise AssertionError("The loglevel must be an integer")
        if self._handler is not None:
            self._handler.setLevel(self.__logger_obj.level)

    @deprecated
    def logLevel(self, level):
        if level is None:
            return self.log_level
        self.log_level = level

    @deprecated
    def logGetLevel(self):
        return self.log_level

    @property
    def _processId(self):
        return _current_process().name

    @property
    def _threadId(self):
        return _current_thread().getName()

    def log_message(self, msg, level):
        _tag = self._level_str[level]
        if self.__log2file:
            method = {logger_CRITICAL: self.__logger_obj.critical,
                      logger_ERROR: self.__logger_obj.error,
                      logger_WARNING: self.__logger_obj.warn,
                      logger_INFO: self.__logger_obj.info,
                      logger_DEBUG: self.__logger_obj.debug}
            method[level]("{0}: {1}".format(self.name, msg))

    @deprecated
    def logMessage(self, *args, **kwargs):
        self.log_message(*args, **kwargs)

    def _critical(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.log_message(msg, logger_CRITICAL)
        except Exception as exc:
            self.log_message("Cannot log {0!r} because {1}".format(msg, exc),
                             logger_CRITICAL)

    def _error(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.log_message(msg, logger_ERROR)
        except Exception as exc:
            self.log_message("Cannot log {0!r} because {1}".format(msg, exc),
                             logger_CRITICAL)

    def _warning(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.log_message(msg, logger_WARNING)
        except Exception as exc:
            self.log_message("Cannot log {0!r} because {1}".format(msg, exc),
                             logger_CRITICAL)

    def _info(self, msg, *args):
        try:
            if len(args) > 0:
                msg = msg.format(*args)
            self.log_message(msg, logger_INFO)
        except Exception as exc:
            self.log_message("Cannot log {0!r} because {1}".format(msg, exc),
                             logger_CRITICAL)

    def _debug(self, msg, *args):
        try:
            if self.__debug_flag:
                if len(args) > 0:
                    msg = msg.format(*args)
                self.log_message(msg, logger_DEBUG)
        except Exception as exc:
            self.log_message("Cannot log {0!r} because {1}".format(msg, exc),
                             logger_CRITICAL)
