from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

from ScopeFoundry.base_app import BaseMicroscopeApp

# Each actuator can be defined with a tuple of settings paths. The following formats are supported:
# 1. (name, position_path | position_read_func, target_position_path | target_position_write_func)
# 2. (name, target_position_path | target_position_write_func) -> target_position_path=position_path
# 3. (target_position_path) -> name=target_position_path=position_path

WriteFunc = Callable[[Any], None]
ReadFunc = Callable[[], Any]
WriteInfo = Union[str, WriteFunc]
ReadInfo = Union[str, ReadFunc, None]
ActuatorFuncs = Tuple[ReadFunc, WriteFunc]
ActuatorInfos = Tuple[ReadInfo, WriteInfo]


ActuatorDefinitions = Union[
    str,
    Tuple[str],
    Tuple[str, WriteInfo],
    Tuple[str, WriteInfo, ReadInfo],
]


def add_all_possible_actuators_and_parse_definitions(
    actuator_definitions: Iterable[ActuatorDefinitions],
    app: BaseMicroscopeApp,
) -> Dict[str, ActuatorInfos]:
    ds = list(actuator_definitions)
    ds.extend(app.get_setting_paths(filter_has_hardware_write=True))
    return parse_definitions(ds)


def parse_definitions(
    actuator_definitions: Iterable[ActuatorDefinitions],
) -> Dict[str, ActuatorInfos]:
    """returns a list of tuples with the actuator name, read path and write path"""
    d = {}
    for defs in actuator_definitions:
        label = defs[0]
        if isinstance(defs, str):
            d[label] = (None, defs)
        elif len(defs) == 1:
            d[label] = (None, defs[0])
        if len(defs) == 2:
            d[label] = (None, defs[1])
        elif len(defs) == 3:
            d[label] = (defs[1], defs[2])
    return d


def get_actuator_funcs(
    app: BaseMicroscopeApp,
    actuator_definitions: Dict[str, ActuatorInfos],
) -> Dict[str, ActuatorFuncs]:
    return {
        k: mk_actuator_func(app, read_info=v[0], write_info=v[1])
        for k, v in actuator_definitions.items()
    }


def mk_actuator_func(
    app: BaseMicroscopeApp,
    read_info: ReadInfo,
    write_info: WriteInfo,
) -> ActuatorFuncs:

    if callable(write_info):
        write_func = write_info
    else:
        write_func = app.get_lq(write_info).update_value

    if read_info is None:
        read_func = lambda: 0
    elif callable(read_info):
        read_func = read_info
    else:
        read_func = app.get_lq(read_info).read_from_hardware

    return read_func, write_func
