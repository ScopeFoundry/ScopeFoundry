from collections import OrderedDict
from warnings import warn

from qtpy import QtCore, QtWidgets

from ScopeFoundry.helper_funcs import get_logger_from_class

from .array_lq import ArrayLQ
from .file_lq import FileLQ
from .logged_quantity import LoggedQuantity
from .lq_3_vector import LQ3Vector
from .lq_range import LQRange


class LQCollectionQObject(QtCore.QObject):

    new_lq_added = QtCore.Signal((LoggedQuantity,))
    lq_removed = QtCore.Signal((LoggedQuantity,))

    def __init__(self, settings, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.settings = settings


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

    def __init__(self, path="") -> None:
        self._logged_quantities = OrderedDict()
        self.ranges = OrderedDict()
        self.vectors = OrderedDict()
        self.log = get_logger_from_class(self)
        self.q_object = LQCollectionQObject(self)
        self.path = path

    def New(
        self,
        name: str,
        dtype: type = float,
        initial=0.0,
        unit: str = None,
        ro: bool = False,  # read only flag
        si: bool = False,
        choices=None,
        spinbox_decimals: int = 2,
        spinbox_step: float = 0.1,
        vmin: float = -1e12,
        vmax: float = +1e12,
        description: str = None,
        colors=None,
        protected: bool = False,  # a guard that prevents from being updated, i.e. file loading
        is_dir: bool = False,
        default_dir: str = None,
        reread_from_hardware_after_write: bool = False,
        is_array: bool = False,
        fmt="%g",
        **kwargs,
    ) -> LoggedQuantity:
        """
        Create a new LoggedQuantity with name and dtype
        """
        if "array" in kwargs:
            warn(
                f"New(array=...) is deprecated, use New(is_array=...) instead. Seen in creation of setting {name}",
                DeprecationWarning,
            )
            is_array = is_array or kwargs.pop("array", False)

        kwargs.update(
            {
                "initial": initial,
                "unit": unit,
                "si": si,
                "ro": ro,
                "choices": choices,
                "vmin": vmin,
                "vmax": vmax,
                "fmt": fmt,
                "description": description,
                "protected": protected,
            }
        )

        if is_array:
            lq = ArrayLQ(name=name, dtype=dtype, **kwargs)
        elif dtype == "file":
            lq = FileLQ(
                name=name,
                default_dir=default_dir,
                is_dir=is_dir,
                **kwargs,
            )
        else:
            lq = LoggedQuantity(
                name=name,
                dtype=dtype,
                spinbox_decimals=spinbox_decimals,
                spinbox_step=spinbox_step,
                reread_from_hardware_after_write=reread_from_hardware_after_write,
                colors=colors,
                **kwargs,
            )

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

        lq.set_path(f"{self.path}/{name}")
        self.q_object.new_lq_added[LoggedQuantity].emit(lq)
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
        self.q_object.lq_removed.emit(lq)
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

    def iter(self, include=None, exclude=None):
        if include is None:
            include = self.as_dict().keys()
        if exclude is None:
            exclude = []
        return ((x, self.get_lq(x)) for x in include if x not in exclude)

    def New_UI(
        self,
        include=None,
        exclude=None,
        style="form",
        additional_widgets=None,
        title=None,
    ) -> QtWidgets.QWidget:
        """
        create a default Qt Widget that contains
        widgets for all settings in the LQCollection
        """

        if additional_widgets is None:
            additional_widgets = {}

        if title is not None:
            ui_widget = QtWidgets.QGroupBox()
            ui_widget.setTitle(title)
        else:
            ui_widget = QtWidgets.QWidget()

        if style == "form":
            formLayout = QtWidgets.QFormLayout(ui_widget)
            for text, lq in self.iter(include, exclude):
                formLayout.addRow(text, lq.new_default_widget())
            for text, widget in additional_widgets.items():
                formLayout.addRow(text, widget)
            return ui_widget

        elif style == "hbox":
            hboxLayout = QtWidgets.QHBoxLayout(ui_widget)
            for text, lq in self.iter(include, exclude):
                hboxLayout.addWidget(QtWidgets.QLabel(text))
                hboxLayout.addWidget(lq.new_default_widget())
            for text, widget in additional_widgets.items():
                hboxLayout.addWidget(QtWidgets.QLabel(text))
                hboxLayout.addWidget(widget)
            return ui_widget

        elif style == "scroll_form":
            formLayout = QtWidgets.QFormLayout(ui_widget)
            scroll_area = QtWidgets.QScrollArea()
            scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(ui_widget)
            for text, lq in self.iter(include, exclude):
                formLayout.addRow(text, lq.new_default_widget())
            for text, widget in additional_widgets.items():
                formLayout.addRow(text, widget)
            return scroll_area

        assert style in ("form", "hbox", "scroll_form")

    def disconnect_all_from_hardware(self):
        for lq in self.as_list():
            lq.disconnect_from_hardware()
