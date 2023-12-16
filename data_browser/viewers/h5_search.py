'''
Created on Dec 13, 2023

@author: Benedikt Ursprung
'''
import functools

from qtpy import QtWidgets
import h5py

from ScopeFoundry.data_browser import DataBrowserView


class H5SearchView(DataBrowserView):

    name = 'h5_search'

    def is_file_supported(self, fname):
        return ('.h5' in fname)

    def setup(self):
        self.ui = QtWidgets.QWidget()
        self.ui.setLayout(QtWidgets.QVBoxLayout())
        self.search_lineEdit = QtWidgets.QLineEdit()
        self.tree_textEdit = QtWidgets.QTextEdit()

        self.ui.layout().addWidget(self.search_lineEdit)
        self.ui.layout().addWidget(self.tree_textEdit)

        self.search_lineEdit.textChanged.connect(self.on_new_search_text)
        self.search_lineEdit.setText("measurement")

    def on_change_data_filename(self, fname=None):
        self.tree_textEdit.setText("loading {}".format(fname))
        try:
            self.fname = fname
            self.on_new_search_text()
            self.databrowser.ui.statusbar.showMessage("")

        except Exception as err:
            msg = "Failed to load %s:\n%s" % (fname, err)
            self.databrowser.ui.statusbar.showMessage(msg)
            self.tree_textEdit.setText(msg)
            raise(err)

    def on_new_search_text(self, x=None):
        fname = self.databrowser.settings["data_filename"]
        if x is None or x.lower() == "":
            text = "<br>".join(make_tree(fname))
        else:
            search_text = x.lower()
            text = "<br>".join(search_h5(fname, search_text))
            text = text.replace(
                search_text, f"<font color='green'>{search_text}</font>")
        self.tree_textEdit.setText(text)


def search_h5(fname, search_text):
    priority_results = []
    results = []
    visit_func = functools.partial(_search_visitfunc,
                                   results=results,
                                   priority_results=priority_results,
                                   search_text=search_text)
    with h5py.File(fname) as file:
        file.visititems(visit_func)
    return priority_results + results


def _search_visitfunc(name, node, results, priority_results, search_text):
    if not (search_text in name or any(search_text in attr for attr in node.attrs.keys())):
        return

    if isinstance(node, h5py.Dataset):
        priority_results.append(f"<i>{name}, {node.shape}, {node.dtype}</i>")

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

    level = len(name.split('/'))
    indent = '&nbsp;' * 4 * (level - 1)
    localname = name.split('/')[-1]

    if isinstance(node, h5py.Group):
        t = f"|> <b>{localname}/</b>".format(localname)
    elif isinstance(node, h5py.Dataset):
        t = f"|D <b>{localname}</b>: {node.shape} {node.dtype}"
    texts.append(indent + t)
    
    for key, val in node.attrs.items():
        t = f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|- <i>{key}</i> = {val}"
        texts.append(indent + t)
