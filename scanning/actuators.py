from typing import Callable, Dict, Iterable, List, Tuple, Union

from ScopeFoundry.base_app import BaseMicroscopeApp

# Each actuator can be defined with a tuple of settings paths. The following formats are supported:
# 1. (name, position_path | position_read_func, target_position_path | target_position_write_func)
# 2. (name, target_position_path | target_position_write_func) -> target_position_path=position_path
# 3. (target_position_path) -> name=target_position_path=position_path
ACTUATOR_DEFINITION = Union[
    Tuple[str],
    Tuple[str, Union[str, Callable]],
    Tuple[str, Union[str, Callable], Union[str, Callable]],
]


def parse_definitions(
    actuator_definitions: Iterable[ACTUATOR_DEFINITION],
) -> Dict[str, Tuple[Union[str, Callable], Union[str, Callable]]]:
    """returns a list of tuples with the actuator name, read path and write path"""
    l = {}
    for d in actuator_definitions:
        if len(d) == 1:
            label = d[0]
            paths = (d[0], d[0])
        if len(d) == 2:
            label = d[0]
            if callable(d[1]):
                paths = (lambda: 0, d[1])
            else:
                paths = (d[1], d[1])
        elif len(d) == 3:
            label = d[0]
            paths = (d[1], d[2])
        l[label] = paths
    return l


def add_all_possible_actuators_and_parse_definitions(
    actuator_definitions: Iterable[ACTUATOR_DEFINITION],
    app: BaseMicroscopeApp,
) -> List[Tuple[str, Union[str, Callable], Union[str, Callable]]]:
    ds = list(actuator_definitions)
    ds.extend(app.get_setting_paths(filter_has_hardware_write=True))
    return parse_definitions(ds)


def get_actuator_funcs(
    app: BaseMicroscopeApp,
    actuator_definitions: Dict[str, Tuple[str, str]] = {},
) -> Dict[str, Tuple[Callable, Callable]]:
    return {
        k: mk_actuator_func(app, read_info=v[0], write_info=v[1])
        for k, v in actuator_definitions.items()
    }


def mk_actuator_func(
    app: BaseMicroscopeApp,
    write_info: Union[str, Callable],
    read_info: Union[str, Callable, None] = None,
) -> Union[Tuple[None, None], Tuple[Callable, Callable]]:

    if callable(write_info):
        write_func = write_info
    else:
        write_func = app.get_lq(write_info).update_value

    if read_info is None:
        return write_func, write_func

    elif callable(read_info):
        read_func = read_info
    else:
        read_func = app.get_lq(read_info).read_from_hardware

    return read_func, write_func
