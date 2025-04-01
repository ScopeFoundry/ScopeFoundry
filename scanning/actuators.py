from typing import Callable, Dict, Iterable, List, Tuple, Union

from ScopeFoundry.base_app import BaseMicroscopeApp

# Each actuator can be defined with a tuple of settings paths. The following formats are supported:
# 1. (name, position_path, target_position_path)
# 2. (name, target_position_path) -> position_path=target_position_path
# 3. (position_path, target_position_path) -> name=position_path
# 4. (target_position_path) -> name=target_position_path=position_path
ACTUATOR_DEFINITION = Union[
    Tuple[str],
    Tuple[str, str],
    Tuple[str, str, str],
]


def parse_definitions(
    actuator_definitions: Iterable[ACTUATOR_DEFINITION],
    app: BaseMicroscopeApp,
) -> Dict[str, Tuple[str, str]]:
    """returns a list of tuples with the actuator name, read path and write path"""
    l = {}
    existing_paths = app.get_setting_paths()
    for d in actuator_definitions:
        if len(d) == 1:
            label = d[0]
            paths = (d[0], d[0])
        if len(d) == 2:
            # can either be defined as (label, write_lq) or (write_lq, read_path)
            if d[0] in existing_paths:
                label = d[0]
                paths = (d[0], d[1])
            else:
                label = d[0]
                paths = (d[1], d[1])
        elif len(d) == 3:
            label = d[0]
            paths = (d[1], d[2])
        l[label] = paths
    return l


def parse_actuator_definitions(
    actuator_definitions: Iterable[ACTUATOR_DEFINITION],
    app: BaseMicroscopeApp,
    include_all_connected_actuators: bool = False,
) -> List[Tuple[str, str, str]]:
    ds = list(actuator_definitions)
    if app is not None and include_all_connected_actuators:
        ds.extend(app.get_setting_paths(filter_has_hardware_write=True))
    return parse_definitions(ds, app)


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
) -> Union[None, Tuple[Callable, Callable]]:

    # allow direct defintion of a reader or writer function
    if callable(write_info) and read_info is None:
        return (write_info, write_info)
    elif callable(write_info) and callable(read_info):
        return (read_info, write_info)

    read_lq = app.get_lq(read_info)
    write_lq = app.get_lq(write_info)

    return read_lq.read_from_hardware, write_lq.update_value
    # write_info = write_lq.update_value

    # read_lqs = app.get_setting_paths(filter_has_hardware_read=True)

    # if read_info in read_lqs:
    #     read = app.get_lq(read_info).read_from_hardware
    #     return (read, write_info)

    # if write_lq.has_hardware_read:
    #     read = write_lq.read_from_hardware
    #     return (read, write_info)

    # if write_info.strip("target_") in read_lqs:
    #     read_info = app.get_lq(write_info.strip("target_")).read_from_hardware
    #     return (read_info, write_info)

    # read_info = write_lq.value
    # return (read_info, write_info)
