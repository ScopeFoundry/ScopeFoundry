import logging
import time
from logging import Handler

from qtpy import QtCore

LEVEL_STYLES = {
    "CRITICAL": "color: red;",
    "ERROR": "color: red;",
    "WARNING": "color: orange;",
    "INFO": "color: green;",
    "DEBUG": "color: green;",
    "NOTSET": "",
}


class LoggingQObject(QtCore.QObject):
    # somehow makes handling errors more robust

    new_log_signal = QtCore.Signal((str,))


class HtmlHandler(Handler):
    """sends a signal with the log in html format"""

    def __init__(self, level=logging.NOTSET, buffer_len=500):

        Handler.__init__(self, level=level)
        self.q_object = LoggingQObject()
        self.new_log_signal = self.q_object.new_log_signal

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        self.new_log_signal.emit(log_entry)

    def format(self, record: logging.LogRecord):
        # timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
        style = LEVEL_STYLES.get(record.levelname, "")
        return f"""{timestamp} - <span style="{style}">{record.levelname}</span>: <i>{record.name}</i> :<pre>{record.msg}</pre><br>"""


class StatusBarHandler(Handler):

    def __init__(self, level=logging.NOTSET, setter=print):

        Handler.__init__(self, level=level)
        self.setter = setter

    def emit(self, record: logging.LogRecord):
        self.setter(self.format(record))

    def format(self, record: logging.LogRecord):
        return f"🛈 {record.name}: {record.msg}"


def new_log_file_handler(fname):
    handler = logging.FileHandler(str(fname))
    fmt = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)
    handler.setFormatter(formatter)
    return handler
