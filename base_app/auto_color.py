import hashlib
from typing import Optional, Union

from qtpy import QtGui

ColorLike = Union[QtGui.QColor, str, tuple, list]


def auto_color(obj) -> QtGui.QColor:
    """Return obj.color if usable, else assign and return a deterministic color."""
    obj_color = obj.color
    if obj_color is None:
        return

    if obj_color == "AUTO":
        return color_from_name(getattr(obj, "name", ""))

    color = to_qcolor(obj_color)
    if not color.isValid():
        color = color_from_name(getattr(obj, "name", ""))
        print(
            f"ensure_obj_color: {getattr(obj, 'name', '')} color: {obj_color} is not valid, assigning a new color"
        )
    return color


def color_from_name(name: str) -> QtGui.QColor:
    """Return a deterministic header background color for a given name."""
    base_name = name.split("_")[0]
    digest = hashlib.md5(base_name.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return QtGui.QColor.fromHsv(hue, 58, 122, 95)


def to_qcolor(value: Optional[ColorLike]) -> Optional[QtGui.QColor]:
    if value is None:
        return None
    if isinstance(value, QtGui.QColor):
        return value
    if isinstance(value, str):
        color = QtGui.QColor(value)
        return color if color.isValid() else None
    if isinstance(value, (tuple, list)) and len(value) in (3, 4):
        try:
            color = QtGui.QColor(*value)
        except TypeError:
            return None
        return color if color.isValid() else None
    return None
