from collections import OrderedDict

import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from ScopeFoundry.helper_funcs import get_logger_from_class

from .array_lq import ArrayLQ
from .file_lq import FileLQ
from .logged_quantity import LoggedQuantity
from .lq_3_vector import LQ3Vector
from .lq_range import LQRange


class LQCollection:
    """
    LQCollection is a smart dictionary of LoggedQuantity objects.

    attribute access such as lqcoll.x1 will return full LoggedQuantity object

    dictionary-style access lqcoll['x1'] allows direct reading and writing of
    the LQ's value, handling the signals automatically

    New LQ's can be created with :meth:`New`

    LQRange objects can be created with :meth:`New_Range` and will be stored
    in :attr:ranges

    """

    def __init__(self) -> None:
        self._logged_quantities = OrderedDict()
        self.ranges = OrderedDict()
        self.vectors = OrderedDict()

        self.log = get_logger_from_class(self)

    def New(self, name, dtype=float, **kwargs) -> LoggedQuantity:
        """
        Create a new LoggedQuantity with name and dtype
        """

        is_array = kwargs.pop("array", False)
        # self.log.debug("{} is_array? {}".format(name, is_array))
        if is_array:
            lq = ArrayLQ(name=name, dtype=dtype, **kwargs)
        else:
            if dtype == "file":
                lq = FileLQ(name=name, **kwargs)
            else:
                lq = LoggedQuantity(name=name, dtype=dtype, **kwargs)

        return self.Add(lq)

    def Add(self, lq: LoggedQuantity) -> LoggedQuantity:
        """Add an existing LoggedQuantity to the Collection
        Examples of usefulness: add hardware lq to measurement settings
        """
        name = lq.name
        assert not (name in self._logged_quantities)
        assert not (name in self.__dict__)
        self._logged_quantities[name] = lq
        self.__dict__[name] = lq  # allow attribute access
        return lq

    def get_lq(self, key) -> LoggedQuantity:
        return self._logged_quantities[key]

    def get_val(self, key):
        return self._logged_quantities[key].val

    def as_list(self):
        return self._logged_quantities.values()

    def as_dict(self):
        return self._logged_quantities

    def as_value_dict(self):
        val_dict = dict()
        for k, lq in self.as_dict().items():
            val_dict[k] = lq.value
        return val_dict

    #    def items(self):
    #        return self._logged_quantities.items()

    def keys(self):
        return self._logged_quantities.keys()

    def remove(self, name):
        lq = self._logged_quantities.pop(name)
        del self.__dict__[name]
        del lq

    def __delitem__(self, key):
        self.remove(key)

    def __getitem__(self, key):
        "Dictionary-like access reads and sets value of LQ's"
        return self._logged_quantities[key].val

    def __setitem__(self, key, item):
        "Dictionary-like access reads and sets value of LQ's"
        self._logged_quantities[key].update_value(item)

    def __contains__(self, key):
        return self._logged_quantities.__contains__(key)

    """
    def __getattribute__(self,name):
        if name in self.logged_quantities.keys():
            return self.logged_quantities[name]
        else:
            return object.__getattribute__(self, name)
    """

    def New_Range(
        self,
        name,
        include_center_span=False,
        include_sweep_type=False,
        initials=[0, 1.0, 0.1],
        **kwargs,
    ):

        mn, mx, d = initials
        min_lq = self.New(name + "_min", initial=mn, **kwargs)
        max_lq = self.New(name + "_max", initial=mx, **kwargs)
        step_lq = self.New(name + "_step", initial=d, **kwargs)
        num_lq = self.New(name + "_num", dtype=int, vmin=1, initial=11)

        LQRange_kwargs = {
            "min_lq": min_lq,
            "max_lq": max_lq,
            "step_lq": step_lq,
            "num_lq": num_lq,
        }
        if include_center_span:
            center_lq = self.New(name + "_center", **kwargs, initial=0.5)
            span_lq = self.New(name + "_span", **kwargs, initial=1.0)
            LQRange_kwargs.update({"center_lq": center_lq, "span_lq": span_lq})
        if include_sweep_type:
            sweep_type_lq = self.New(
                name + "_sweep_type", dtype=str, choices=("up", "down"), initial="up"
            )
            LQRange_kwargs.update({"sweep_type_lq": sweep_type_lq})

        lqrange = LQRange(**LQRange_kwargs)

        self.ranges[name] = lqrange
        return lqrange

    def New_Vector(self, name, components="xyz", initial=[1, 0, 0], **kwargs):

        assert len(components) == len(initial)

        if len(components) == 3:

            lq_x = self.New(name + "_" + components[0], initial=initial[0], **kwargs)
            lq_y = self.New(name + "_" + components[1], initial=initial[1], **kwargs)
            lq_z = self.New(name + "_" + components[2], initial=initial[2], **kwargs)

            lq_vector = LQ3Vector(lq_x, lq_y, lq_z)
            self.vectors[name] = lq_vector
            return lq_vector

    def New_UI(self, include=None, exclude=[], style="form"):
        """create a default Qt Widget that contains
        widgets for all settings in the LQCollection
        """

        if include is None:
            lqnames = self.as_dict().keys()
        else:
            lqnames = include

        ui_widget = QtWidgets.QWidget()

        if style == "form":
            formLayout = QtWidgets.QFormLayout()
            ui_widget.setLayout(formLayout)

            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)
                #: :type lq: LoggedQuantity
                widget = lq.new_default_widget()
                # Add to formlayout
                formLayout.addRow(lqname, widget)
                # lq_tree_item = QtWidgets.QTreeWidgetItem(self.tree_item, [lqname, ""])
                # self.tree_item.addChild(lq_tree_item)
                # lq.hardware_tree_widget = widget
                # tree.setItemWidget(lq_tree_item, 1, lq.hardware_tree_widget)
                # self.control_widgets[lqname] = widget

        elif style == "hbox":
            hboxLayout = QtWidgets.QHBoxLayout()
            ui_widget.setLayout(hboxLayout)

            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)
                widget = lq.new_default_widget()

                hboxLayout.addWidget(QtWidgets.QLabel(lqname))
                hboxLayout.addWidget(widget)

        elif style == "scroll_form":
            scroll_area = QtWidgets.QScrollArea()
            formLayout = QtWidgets.QFormLayout()
            ui_widget.setLayout(formLayout)
            scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(ui_widget)

            for lqname in lqnames:
                if lqname in exclude:
                    continue
                lq = self.get_lq(lqname)
                #: :type lq: LoggedQuantity
                widget = lq.new_default_widget()
                # Add to formlayout
                formLayout.addRow(lqname, widget)

            return scroll_area

        return ui_widget

    def add_widgets_to_subtree(self, tree_item):
        lq_tree_items = []
        for lqname, lq in self.as_dict().items():
            #: :type lq: LoggedQuantity
            if isinstance(lq, ArrayLQ):
                lineedit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton("...")
                widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout()
                widget.setLayout(layout)
                layout.addWidget(lineedit)
                layout.addWidget(button)
                layout.setSpacing(0)
                layout.setContentsMargins(0, 0, 0, 0)

                lq.connect_to_widget(lineedit)
                button.clicked.connect(lq.array_tableView.show)
                button.clicked.connect(lq.array_tableView.raise_)
            elif isinstance(lq, FileLQ):
                lineedit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton("...")
                widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout()
                widget.setLayout(layout)
                layout.addWidget(lineedit)
                layout.addWidget(button)
                layout.setSpacing(0)
                layout.setContentsMargins(0, 0, 0, 0)

                lq.connect_to_browse_widgets(lineedit, button)
            else:
                if lq.choices is not None:
                    widget = QtWidgets.QComboBox()
                elif lq.dtype in [int, float]:
                    if lq.si:
                        widget = pg.SpinBox()
                    else:
                        widget = QtWidgets.QDoubleSpinBox()
                elif lq.dtype in [bool]:
                    widget = QtWidgets.QCheckBox()
                elif lq.dtype in [str]:
                    widget = QtWidgets.QLineEdit()
                lq.connect_to_widget(widget)

            lq_tree_item = QtWidgets.QTreeWidgetItem(tree_item, [lqname, ""])
            lq_tree_items.append(lq_tree_item)
            tree_item.addChild(lq_tree_item)
            lq.tree_widget = widget
            tree_item.treeWidget().setItemWidget(lq_tree_item, 1, lq.tree_widget)
            # self.control_widgets[lqname] = widget
        return lq_tree_items

    def disconnect_all_from_hardware(self):
        for lq in self.as_list():
            lq.disconnect_from_hardware()
