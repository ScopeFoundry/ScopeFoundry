from collections import OrderedDict
from typing import Dict, List
from warnings import warn

from qtpy import QtCore, QtWidgets

from ScopeFoundry.dynamical_widgets.tools import Tools
from ScopeFoundry.helper_funcs import get_logger_from_class, filter_with_patterns
from ScopeFoundry.logged_quantity import (
    ArrayLQ,
    FileLQ,
    LoggedQuantity,
    LQ3Vector,
    LQRange,
    IntervaledLQRange,
)


class LQCollectionQObject(QtCore.QObject):

    lq_added = QtCore.Signal((LoggedQuantity,))
    lq_removed = QtCore.Signal((LoggedQuantity,))

    def __init__(self, settings, parent: QtCore.QObject = None) -> None:
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

    def __init__(self, path="", event_filter=None) -> None:
        self._logged_quantities = OrderedDict()
        self.ranges: Dict[str, LQRange] = OrderedDict()
        self.vectors: Dict[str, LQ3Vector] = OrderedDict()
        self.log = get_logger_from_class(self)
        self.q_object = LQCollectionQObject(self)
        self.path = path
        self._widgets_managers_ = []
        self.event_filter = event_filter

    def new_file(
        self,
        name: str,
        initial: float = 0.0,
        is_dir: bool = False,
        default_dir: str = None,
        file_filters=(),
        description: str = None,
        ro: bool = False,  # read only flag
        choices=None,
        colors=None,
        protected: bool = False,  # a guard that prevents from being updated, i.e. file loading
        is_clipboardable=False,
        **kwargs,
    ) -> FileLQ:
        return self.New(
            name=name,
            dtype="file",
            initial=initial,
            is_dir=is_dir,
            default_dir=default_dir,
            file_filters=file_filters,
            description=description,
            ro=ro,
            choices=choices,
            colors=colors,
            protected=protected,
            is_clipboardable=is_clipboardable,
            **kwargs,
        )

    def New(
        self,
        name: str,
        dtype: type = float,
        initial: float = 0.0,
        unit: str = None,
        si: bool = False,
        vmin: float = -1_000_000_000_000,
        vmax: float = 1_000_000_000_000,
        description: str = None,
        ro: bool = False,  # read only flag
        choices=None,
        spinbox_decimals: int = 2,
        spinbox_step: float = 0.1,
        colors=None,
        protected: bool = False,  # a guard that prevents from being updated, i.e. file loading
        is_dir: bool = False,
        default_dir: str = None,
        file_filters=(),
        reread_from_hardware_after_write: bool = False,
        is_array: bool = False,
        fmt="%g",
        is_cmd=False,
        is_clipboardable=False,
        default_widget_factory=None,
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
                file_filters=file_filters,
                is_clipboardable=is_clipboardable,
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
                is_cmd=is_cmd,
                is_clipboardable=is_clipboardable,
                default_widget_factory=default_widget_factory,
                **kwargs,
            )
        lq.event_filter = self.event_filter

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
        self.q_object.lq_added[LoggedQuantity].emit(lq)
        return lq

    def get_lq(self, key) -> LoggedQuantity:
        return self._logged_quantities[key]

    def get_val(self, key):
        return self._logged_quantities[key].val

    def as_list(self) -> List[LoggedQuantity]:
        return self._logged_quantities.values()

    def as_dict(self) -> Dict[str, LoggedQuantity]:
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

    def __str__(self) -> str:
        lines = [f"Settings path: {self.path}"] + [
            f"{k}: {v}" for k, v in self.as_value_dict().items()
        ]
        return "\n".join(lines)

    """
    def __getattribute__(self,name):
        if name in self.logged_quantities.keys():
            return self.logged_quantities[name]
        else:
            return object.__getattribute__(self, name)
    """

    def New_Range(
        self,
        name: str,
        include_center_span: bool = False,
        include_sweep_type: bool = False,
        initials=[0, 1.0, 0.1],
        unit: str = "",
        si: bool = False,
        ro: bool = False,
        vmin: float = -1_000_000_000_000,
        vmax: float = 1_000_000_000_000,
        spinbox_decimals: int = 2,
        description: str = "",
        **kwargs,
    ):
        kwargs["ro"] = ro
        kwargs["description"] = description

        kwargs.pop("dtype", None)

        mn, mx, d = initials
        min_lq = self.New(
            f"{name}_min",
            initial=mn,
            vmin=vmin,
            vmax=vmax,
            spinbox_decimals=spinbox_decimals,
            unit=unit,
            si=si,
            **kwargs,
        )
        max_lq = self.New(
            name=f"{name}_max",
            initial=mx,
            vmin=vmin,
            vmax=vmax,
            spinbox_decimals=spinbox_decimals,
            unit=unit,
            si=si,
            **kwargs,
        )

        step_lq = self.New(
            f"{name}_step",
            initial=d,
            unit=unit,
            si=si,
            spinbox_decimals=spinbox_decimals + 1,
            **kwargs,
        )
        step0 = int((initials[1] - initials[0]) / d) + 1
        num_lq = self.New(f"{name}_num", dtype=int, vmin=1, initial=step0, **kwargs)

        LQRange_kwargs = {
            "min_lq": min_lq,
            "max_lq": max_lq,
            "step_lq": step_lq,
            "num_lq": num_lq,
        }
        if include_center_span:
            c0 = (initials[1] + initials[0]) / 2
            s0 = initials[1] - initials[0]
            center_lq = self.New(
                name=f"{name}_center",
                initial=c0,
                spinbox_decimals=spinbox_decimals,
                unit=unit,
                si=si,
                **kwargs,
            )
            span_lq = self.New(
                name=f"{name}_span",
                initial=s0,
                spinbox_decimals=spinbox_decimals,
                unit=unit,
                si=si,
                **kwargs,
            )
            LQRange_kwargs.update({"center_lq": center_lq, "span_lq": span_lq})
        if include_sweep_type:
            sweep_type_lq = self.New(f"{name}_sweep_type", str, choices=("up", "down"))
            LQRange_kwargs.update({"sweep_type_lq": sweep_type_lq})

        lqrange = LQRange(**LQRange_kwargs)

        self.ranges[name] = lqrange
        return lqrange

    def new_intervaled_range(
        self,
        name: str,
        n_intervals=5,
        include_center_span: bool = False,
        include_sweep_type: bool = False,
        initials=None,
        unit=None,
        si=False,
        ro=False,
        vmin=-1_000_000_000_000,
        vmax=1_000_000_000_000,
        spinbox_decimals=4,
        description="",
        **kwargs,
    ):
        """
        Create a new TripleLQRange with n ranges.
        Each range is an ActiveLQRange with min, max, step, num, center, span, sweep_type, and is_active.
        """

        if initials is None:
            initials = [(ii < 1, ii, ii + 1, 0.1) for ii in range(n_intervals)]
        elif len(initials) != n_intervals:
            raise ValueError("invalid initials length, must match n")

        lq_ranges = [
            self.New_Range(
                name=f"{name}_{i}",
                include_center_span=include_center_span,
                include_sweep_type=False,
                unit=unit,
                si=si,
                ro=ro,
                vmin=vmin,
                vmax=vmax,
                spinbox_decimals=spinbox_decimals,
                description=description,
                initials=initials[i][1:],
                **kwargs,
            )
            for i in range(n_intervals)
        ]
        is_active_lqs = [
            self.New(f"{name}_{i}_is_active", bool, initial=initials[i][0])
            for i in range(n_intervals)
        ]
        if include_sweep_type:
            sweep_type = self.New(
                f"{name}_sweep_type",
                str,
                choices=("up", "down", "up_down", "down_up", "zig_zag", "zag_zig"),
            )
        else:
            sweep_type = None

        no_duplicates = self.New(
            f"{name}_no_duplicates",
            bool,
            initial=True,
            description="Remove adjacent duplicates from *up* and *down* sweep ranges",
        )

        i_range = IntervaledLQRange(lq_ranges, is_active_lqs, no_duplicates, sweep_type)
        self.ranges[name] = i_range
        return i_range

    def New_Vector(self, name, components="xyz", initial=[1, 0, 0], **kwargs):

        assert len(components) == len(initial)

        if len(components) == 3:

            lq_x = self.New(f"{name}_{components[0]}", initial=initial[0], **kwargs)
            lq_y = self.New(f"{name}_{components[1]}", initial=initial[1], **kwargs)
            lq_z = self.New(f"{name}_{components[2]}", initial=initial[2], **kwargs)

            lq_vector = LQ3Vector(lq_x, lq_y, lq_z)
            self.vectors[name] = lq_vector
            return lq_vector

    def iter(self, include=None, exclude=None):
        """
        returns a list logged quantity specified by include and exclude

        include and exclude support wildcards:
            *       matches everything
            ?       matches any single character
            [seq]   matches any character in seq
            [!seq]  matches any char not in seq
        """
        return (
            (x, self.get_lq(x))
            for x in filter_with_patterns(self.keys(), include, exclude)
        )

    def New_UI(
        self,
        include=None,
        exclude=None,
        style="form",
        title=None,
    ) -> QtWidgets.QWidget:
        """
        create a default Qt Widget that contains
        widgets for all settings in the LQCollection
        """
        if title is not None:
            widget = QtWidgets.QGroupBox()
            widget.setTitle(title)
        else:
            widget = QtWidgets.QWidget()

        if style in ("form", "scroll_form"):
            layout = QtWidgets.QFormLayout(widget)

        elif style == "hbox":
            layout = QtWidgets.QHBoxLayout(widget)

        tools = Tools(layout, include, exclude)
        self._widgets_managers_.append(LQCollectionWidgetsManager(self, tools))

        if style == "scroll_form":
            scroll_area = QtWidgets.QScrollArea()
            scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(widget)
            return scroll_area

        return widget

    def disconnect_all_from_hardware(self):
        for lq in self.as_list():
            lq.disconnect_from_hardware()


class LQCollectionWidgetsManager:

    def __init__(
        self,
        settings: LQCollection,
        tools: Tools,
    ) -> None:
        self.settings = settings
        self.tools = tools

        settings.q_object.lq_added.connect(self.add)
        settings.q_object.lq_removed.connect(self.remove)

        self.widgets = {}

        self.update()

    def add(self, lq: LoggedQuantity):
        self.update()

    def remove(self, lq: LoggedQuantity):
        widget = self.widgets.pop(lq.name, None)
        if widget is None:
            return
        self.tools.remove_from_layout(lq.name, widget)

    def update(self):
        for lqname, lq in tuple(
            self.settings.iter(self.tools.include, self.tools.exclude)
        ):
            if lqname in self.widgets.keys():
                continue
            if isinstance(lq, ArrayLQ):
                lineedit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton("...")
                new_widget = QtWidgets.QWidget()
                layout = QtWidgets.QHBoxLayout()
                new_widget.setLayout(layout)
                layout.addWidget(lineedit)
                layout.addWidget(button)
                layout.setSpacing(0)
                layout.setContentsMargins(0, 0, 0, 0)
                lq.connect_to_widget(lineedit)
                button.clicked.connect(lq.array_tableView.show)
                button.clicked.connect(lq.array_tableView.raise_)
            elif isinstance(lq, FileLQ):
                new_widget = lq.new_default_widget()
                new_widget.layout().setSpacing(0)
                new_widget.layout().setContentsMargins(0, 0, 0, 0)
            elif isinstance(lq, LoggedQuantity):
                new_widget = lq.new_default_widget()
            else:
                continue

            self.widgets[lqname] = new_widget
            self.tools.add_to_layout(lqname, new_widget)
