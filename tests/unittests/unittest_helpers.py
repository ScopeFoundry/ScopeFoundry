import logging

from qtpy import QtCore

from ScopeFoundry.base_app.logging_handlers import HtmlHandler, StatusBarHandler


def close_app_widgets(app):
    root_logger = logging.getLogger()
    logging_widget = getattr(app, "logging_widget", None)
    if logging_widget is not None:
        for handler in list(root_logger.handlers):
            if not isinstance(handler, HtmlHandler):
                continue
            try:
                handler.new_log_signal.disconnect(logging_widget.on_new_log)
            except TypeError:
                continue
            root_logger.removeHandler(handler)
            handler.close()

    log_file_handler = getattr(app, "log_file_handler", None)
    if log_file_handler is not None:
        root_logger.removeHandler(log_file_handler)
        log_file_handler.close()

    logger = getattr(app, "log", None)
    if logger is not None:
        for handler in list(logger.handlers):
            if (
                isinstance(handler, StatusBarHandler)
                and handler.setter == app.show_status_bar_msg
            ):
                logger.removeHandler(handler)
                handler.close()

    widgets = [
        widget
        for attribute in ("console_widget", "logging_widget", "ui")
        if (widget := getattr(app, attribute, None)) is not None
    ]
    for widget in widgets:
        widget.deleteLater()
    app.qtapp.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.qtapp.processEvents()