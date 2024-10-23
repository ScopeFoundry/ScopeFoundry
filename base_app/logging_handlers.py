import logging
import time
from logging import Handler

from qtpy import QtCore, QtGui

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


class LoggingQTextEditHandler(Handler):

    def __init__(self, textEdit, level=logging.NOTSET, buffer_len=500):
        self.textEdit = textEdit
        self.buffer_len = buffer_len
        self.messages = []
        Handler.__init__(self, level=level)
        self.q_object = LoggingQObject()
        self.new_log_signal = self.q_object.new_log_signal
        self.new_log_signal.connect(self.on_new_log)

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        self.new_log_signal.emit(log_entry)

    def on_new_log(self, log_entry: str):
        self.messages.append(log_entry)
        if len(self.messages) > self.buffer_len:
            self.messages = ["...<br>"] + self.messages[-self.buffer_len :]
        self.textEdit.setHtml("\n".join(self.messages))
        self.textEdit.moveCursor(QtGui.QTextCursor.End)

    def format(self, record: logging.LogRecord):
        # timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created))
        style = LEVEL_STYLES.get(record.levelname, "")
        return (
            """{} - <span style="{}">{}</span>: <i>{}</i> :<pre>{}</pre><br>""".format(
                timestamp, style, record.levelname, record.name, record.msg
            )
        )


def new_log_file_handler(fname):
    handler = logging.FileHandler(str(fname))
    fmt = "%(asctime)s|%(levelname)s|%(name)s|%(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)
    handler.setFormatter(formatter)
    return handler
