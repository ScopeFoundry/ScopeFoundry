SCAN_MODES = ("NA", "Position List")
SCAN_MODES_DESCRIPTION = """
<p><i>NA:</i> single actuator sweep
<p><i>Position List:</i> positions are defined by this Measurement's Position List.</p>
"""


def mk_positions_gen(ar_1, mode="NA"):
    if mode == "NA" or mode == "Position List":
        for k, kv in enumerate(ar_1):
            yield (kv,)


def mk_data_shape(ar_1, mode="NA"):
    if mode == "NA" or mode == "Position List":
        return (len(ar_1),)


def mk_indices_gen(ar_1, mode="NA"):
    if mode == "NA" or mode == "Position List":
        for k, v in enumerate(ar_1):
            yield k,


def mk_ranges_consistent(settings, actuator_names=("1", "2", "3")):
    return
