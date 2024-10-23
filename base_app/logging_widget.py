from qtpy import QtCore, QtGui, QtWidgets


class LoggingWidget(QtWidgets.QWidget):

    def __init__(
        self,
        parent: QtWidgets.QWidget = None,
        buffer_len=500,
    ) -> None:
        super().__init__(parent)
        self.buffer_len = buffer_len
        self.messages = []

        self.setWindowTitle("Log")
        self.setLayout(QtWidgets.QVBoxLayout())
        self.search_lineEdit = QtWidgets.QLineEdit()
        self.text_edit = QtWidgets.QTextEdit("")

        self.layout().addWidget(self.search_lineEdit)
        self.layout().addWidget(self.text_edit)

        self.text_edit.document().setDefaultStyleSheet("body{font-family: Courier;}")
        self.search_lineEdit.editingFinished.connect(self.on_search)

    @QtCore.Slot(str)
    def on_new_log(self, log_entry: str):
        self.messages.append(log_entry)
        if len(self.messages) > self.buffer_len:
            self.messages = ["...<br>"] + self.messages[-self.buffer_len :]
        self.text_edit.setHtml("\n".join(self.messages))
        self.text_edit.moveCursor(QtGui.QTextCursor.End)

    @QtCore.Slot()
    def on_search(self):
        search_text = self.search_lineEdit.text().lower()
        messages = [message for message in self.messages if search_text in message.lower()]
        self.text_edit.setHtml("\n".join(messages))
        self.text_edit.moveCursor(QtGui.QTextCursor.End)
