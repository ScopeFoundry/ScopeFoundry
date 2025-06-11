from qtpy import QtCore


class LQCircularNetwork(QtCore.QObject):
    """
    LQCircularNetwork is collection of logged quantities
    Helper class if a network of lqs with circular structures are present
    Use update_values_synchronously method if the specified lqs should
    be updated at once. The internal lock-flag prevents infinite loops.
    """

    updated_values = QtCore.Signal(
        (),
    )

    def __init__(self, lq_dict=None, lq_list=None):
        if lq_dict is None:
            lq_dict = dict()
        if lq_list is not None:
            for lq in lq_list:
                lq_dict[lq.name] = lq
        self.lq_dict = lq_dict  # {lq_key:lq}
        self.locked = False  # some lock that does NOT allow blocked routines to be executed after release()
        QtCore.QObject.__init__(self)

        # a flag (as it is now) works well.

    def update_values_synchronously(self, **kwargs):
        """
        kwargs is dict containing lq_key and new_vals
        Note: lq_key is not necessarily the name of the lq but key of lq_dict
              as specified at initialization
        """
        if self.locked == False:
            self.locked = True
            for kev, val in kwargs.items():
                self.lq_dict[kev].update_value(val)
                self.updated_values.emit()
                self.locked = False

    def add_lq(self, lq, name=None):
        if name is None:
            name = lq.name
        self.lq_dict[name] = lq
