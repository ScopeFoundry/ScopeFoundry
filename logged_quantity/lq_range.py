import numpy as np
from qtpy import QtWidgets

from ScopeFoundry.helper_funcs import get_logger_from_class

from .logged_quantity import LoggedQuantity
from .lq_circular_network import LQCircularNetwork


class LQRange(LQCircularNetwork):
    """
    LQRange is a collection of logged quantities that describe a
    numpy.linspace array inputs.
    Four (or six) LQ's are defined, min, max, num, step (center, span)
    and are connected by signals/slots that keep the quantities
    in sync.
    LQRange.array is the linspace array and is kept upto date
    with changes to the 4 (or 6) LQ's
    """

    def __init__(
        self,
        min_lq: LoggedQuantity,
        max_lq: LoggedQuantity,
        step_lq: LoggedQuantity,
        num_lq: LoggedQuantity,
        center_lq: LoggedQuantity = None,
        span_lq: LoggedQuantity = None,
        sweep_type_lq: LoggedQuantity = None,
    ):
        self.log = get_logger_from_class(self)
        self.min = min_lq
        self.max = max_lq
        self.num = num_lq
        self.step = step_lq
        self.center = center_lq
        self.span = span_lq

        lq_dict = {"min": self.min, "max": self.max, "num": self.num, "step": self.step}

        if self.center == None:
            assert self.span == None, "Invalid initialization of LQRange"
        else:
            lq_dict.update({"center": self.center})
        if self.span == None:
            assert self.center == None, "Invalid initialization of LQRange"
        else:
            lq_dict.update({"span": self.span})

        LQCircularNetwork.__init__(self, lq_dict)

        """
        Note: {step, num} and {min,max,span,center} form each 2 circular subnetworks
        The listener functions update the subnetworks, a connect_lq_math connects 
         {min,max,span,center} to {step, num} unidirectional
        """
        self.num.add_listener(self.on_change_num)
        self.step.add_listener(self.on_change_step)
        if self.center and self.span:
            self.center.add_listener(self.on_change_center_span)
            self.span.add_listener(self.on_change_center_span)
            self.min.add_listener(self.on_change_min_max)
            self.max.add_listener(self.on_change_min_max)

        self.step.connect_lq_math((self.min, self.max, self.num), self.calc_step)

        if sweep_type_lq is not None:
            self.sweep_type_map = {
                "up": self.up_sweep_array,
                "down": self.down_sweep_array,
                "up_down": self.up_down_sweep_array,
                "down_up": self.down_up_sweep_array,
                "zig_zag": self.zig_zag_sweep_array,
                "zag_zig": self.zag_zig_sweep_array,
            }
            self.sweep_type = sweep_type_lq
            self.sweep_type.change_choice_list(self.sweep_type_map.keys())
            lq_dict["sweep_type"] = sweep_type_lq

    def calc_num(self, min_, max_, step):
        """
        enforces num to be a positive integer and adjust step accordingly
        returns num,step
        """
        span = max_ - min_
        if step == 0:
            n = 10
        else:
            n = span / step  # num = n+1
            if n < 0:
                n = -n
            n = np.ceil(n)
        step = span / n
        num = n + 1
        return int(num), step

    def calc_step(self, min_, max_, num):
        """
        excludes num=1 to prevent division by zero,
        returns step
        """
        if num == 1:  # prevent division by zero
            num = 2
        step = (max_ - min_) / (num - 1)
        return step

    def calc_span(self, min_, max_):
        return max_ - min_

    def calc_center(self, min_, max_):
        return (max_ - min_) / 2 + min_

    def calc_min(self, center, span):
        return center - span / 2.0

    def calc_max(self, center, span):
        return center + span / 2.0

    def on_change_step(self):
        step = self.step.val
        num, step = self.calc_num(self.min.val, self.max.val, step)
        self.update_values_synchronously(num=num, step=step)

    def on_change_num(self):
        num = self.num.val
        if num == 1:
            num = 2
        step = self.calc_step(self.min.val, self.max.val, self.num.val)
        self.update_values_synchronously(num=num, step=step)

    def on_change_min_max(self):
        min_ = self.min.val
        max_ = self.max.val
        span = self.calc_span(min_, max_)
        center = self.calc_center(min_, max_)
        self.update_values_synchronously(span=span, center=center)

    def on_change_center_span(self):
        span = self.span.val
        center = self.center.val
        min_ = self.calc_min(center, span)
        max_ = self.calc_max(center, span)
        self.update_values_synchronously(min=min_, max=max_)

    @property
    def array(self):
        return np.linspace(self.min.val, self.max.val, self.num.val)

    def zig_zag_sweep_array(self):
        mid_arg = int(self.num.val / 2)
        ar = self.array
        return np.concatenate([ar[mid_arg:], ar[::-1], ar[0:mid_arg]])

    def zag_zig_sweep_array(self):
        return self.zig_zag_sweep_array()[::-1]

    def up_down_sweep_array(self):
        ar = self.array
        return np.concatenate([ar, ar[::-1]])

    def down_up_sweep_array(self):
        return self.up_down_sweep_array()[::-1]

    def down_sweep_array(self):
        return self.array[::-1]

    def up_sweep_array(self):
        return self.array

    @property
    def sweep_array(self):
        if hasattr(self, "sweep_type"):
            return self.sweep_type_map[self.sweep_type.val]()
        else:
            return self.array

    def add_listener(self, func, argtype=(), **kwargs):
        self.min.add_listener(func, argtype, **kwargs)
        self.max.add_listener(func, argtype, **kwargs)
        self.num.add_listener(func, argtype, **kwargs)

    def New_UI(self):
        ui_widget = QtWidgets.QWidget()
        formLayout = QtWidgets.QFormLayout()
        ui_widget.setLayout(formLayout)
        for lqname, lq in self.lq_dict.items():
            formLayout.addRow(lqname, lq.new_default_widget())
        return ui_widget


class TripleRange(LQRange):
    """
    LQRangeABC is a collection of logged quantities that describe a
    numpy.linspace array inputs.
    Four (or six) LQ's are defined, min, max, num, step (center, span)
    and are connected by signals/slots that keep the quantities
    in sync.
    LQRange.array is the linspace array and is kept upto date
    with changes to the 4 (or 6) LQ's
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log.warning("LQRangeABC is deprecated, use LQRange instead")
        