import functools
import h5py
from qtpy import QtCore, QtWidgets

from ScopeFoundry.data_browser.data_browser_plug_in import DataBrowserPlugIn


class H5SearchPlugIn(DataBrowserPlugIn):
    name = "h5_search"
    button_text = "🔍h5"
    show_keyboard_key = QtCore.Qt.Key_F
    description = "used to inspect data sets and attributes of .h5 files (Ctrl+F)"

    def setup(self):
        self.search_line = QtWidgets.QLineEdit()
        self.search_line.setText("measurement")
        self.text_edit = QtWidgets.QTextEdit()

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.addWidget(QtWidgets.QLabel("🔍 text"))
        search_layout.addWidget(self.search_line)

        self.ui = QtWidgets.QWidget(objectName="SearchWidget")
        layout = QtWidgets.QVBoxLayout(self.ui)
        layout.addLayout(search_layout)
        layout.addWidget(self.text_edit)
        self.ui.setStyleSheet(
            "QWidget#SearchWidget{background-color:rgba(0, 166, 237, 0.1)}"
        )

        self.search_line.textChanged.connect(self.update)

    def update(self, fname: str = None) -> None:
        fname = self.new_fname
        if not fname.endswith(".h5"):
            self.text_edit.setText(f"{fname} is not supported")
            return
        search_text = self.search_line.text()
        self.new_search(search_text, fname)

    def new_search(self, search_text, fname):
        x = search_text.lower()
        if x == "":
            text = "<br>".join(make_tree(fname))
        else:
            text = "<br>".join(search_h5(fname, x))
            text = text.replace(
                search_text, f"<font color='green'>{search_text}</font>"
            )
        self.text_edit.setText(text)


def search_h5(fname, search_text):
    priority_results = []
    results = []
    visit_func = functools.partial(
        _search_visitfunc,
        results=results,
        priority_results=priority_results,
        search_text=search_text,
    )
    with h5py.File(fname) as file:
        file.visititems(visit_func)
    return priority_results + results


def _search_visitfunc(name, node, results, priority_results, search_text):
    if not (
        search_text in name or any(search_text in attr for attr in node.attrs.keys())
    ):
        return

    if isinstance(node, h5py.Dataset):
        try:
            stats = f"min={min(node[:].ravel()):1.1f} max={max(node[:].ravel()):1.1f}"
        except ValueError:
            stats = ""
        priority_results.append(f"<i>{name}, {node.shape}, {node.dtype}</i> {stats}")

    elif name.endswith("settings"):
        for key, val in node.attrs.items():
            units = node["units"].attrs[key] if key in node["units"].attrs else ""
            res = f"<b>{name.replace('settings', key)}</b>: {str(val)} {units}"
            if search_text in key or search_text in name:
                priority_results.append(res)
            else:
                results.append(res)


def make_tree(fname):
    texts = []
    visit_func = functools.partial(_tree_visitfunc, texts=texts)
    with h5py.File(fname) as file:
        file.visititems(visit_func)
    return texts


def _tree_visitfunc(name, node, texts):
    level = len(name.split("/"))
    indent = "&nbsp;" * 4 * (level - 1)
    localname = name.split("/")[-1]

    if isinstance(node, h5py.Group):
        t = f"|> <b>{localname}/</b>".format(localname)
    elif isinstance(node, h5py.Dataset):
        t = f"|D <b>{localname}</b>: {node.shape} {node.dtype}"
    texts.append(indent + t)

    for key, val in node.attrs.items():
        t = f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|- <i>{key}</i> = {val}"
        texts.append(indent + t)
