import numpy as np
from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

from ScopeFoundry.helper_funcs import str2bool


# https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg17575.html
# plus more
class NumpyQTableModel(QtCore.QAbstractTableModel):
    def __init__(self, narray, col_names=None, row_names=None, fmt="%g", copy=True, transpose=False, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.copy = copy
        self.transpose = transpose
        self.col_names = col_names
        self.row_names = row_names
        self.fmt=fmt

        self.set_array(narray)

    def rowCount(self, parent=None):
        if len(self._array.shape) < 1:
            return 0
        return self._array.shape[0]

    def columnCount(self, parent=None):
        if len(self._array.shape) < 2:
            return 0
        return self._array.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole or role==Qt.EditRole:
                row = index.row()
                col = index.column()
                return self.fmt % self._array[row, col]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        print(index,value, role)
        jj,ii = index.row(), index.column()

        print('setData', ii,jj)
        # return QtCore.QAbstractTableModel.setData(self, *args, **kwargs)

        try:
            if self._array.dtype == bool:
                value = str2bool(value)
            self._array[jj,ii] = value
            self.dataChanged.emit(index, index) # topLeft, bottomRight indexes of change
            return True
        except Exception as err:
            print("setData err:", err)
            return False

    def set_array(self, narray):
        # print "set_array"
        self.original_shape = narray.shape
        if self.copy:
            self._array = narray.copy()
        else:
            self._array = narray.view()
        if len(self._array.shape) == 1:
            self._array.shape=self._array.shape +(1,) # view as 2D
        if self.transpose:
            self._array = self._array.T
        self.layoutChanged.emit()
        # self.dataChanged.emit(self.index(0,0),
        #                      self.index(self.rowCount(), self.columnCount()))

    @property    
    def array(self):
        if self.original_shape != self._array.shape:
            return self._array.reshape(self.original_shape)
        if self.transpose:
            return self._array.T
        return self._array

    def flags(self, *args, **kwargs):
        # return QtCore.QAbstractTableModel.flags(self, *args, **kwargs)
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and self.col_names:
            return self.col_names[section]
        if role == Qt.DisplayRole and orientation == Qt.Vertical and self.row_names:
            return self.row_names[section]
        return QtCore.QAbstractTableModel.headerData(self, section-1, orientation, role)    
        # return None

class ArrayLQ_QTableModel(NumpyQTableModel):
    def __init__(self, lq, col_names=None, row_names=None, parent=None, **kwargs):
        print(lq.val)
        default_kwargs = dict( col_names=col_names, row_names=row_names, fmt=lq.fmt)
        default_kwargs.update(kwargs)
        NumpyQTableModel.__init__(self, lq.val, parent=parent, **default_kwargs)
        self.lq = lq
        self.lq.updated_value[()].connect(self.on_lq_updated_value)
        self.dataChanged.connect(self.on_dataChanged)

    def on_lq_updated_value(self):
        # print "ArrayLQ_QTableModel", self.lq.name, 'on_lq_updated_value'
        self.set_array(self.lq.val)

    def on_dataChanged(self,topLeft=None, bottomRight=None):
        # print "ArrayLQ_QTableModel", self.lq.name, 'on_dataChanged'
        self.lq.update_value(np.array(self.array))
        # self.lq.send_display_updates(force=True)


if __name__ == '__main__':
    qtapp = QtWidgets.QApplication([])
    
    import numpy as np
    
    A = np.random.rand(10,5)
    B = np.random.rand(12,4)
    
    table_view = QtWidgets.QTableView()
    table_view_model = NumpyQTableModel(narray=A, col_names=['Peak', 'FWHM','center', 'asdf', '!__!'])
    table_view.setModel(table_view_model)
    table_view.show()
    table_view.raise_()
    
    table_view_model.set_array(B)
    
    qtapp.exec_()
