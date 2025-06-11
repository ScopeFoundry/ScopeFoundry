SCAN_MODES = ("NA",)
SCAN_MODES_DESCRIPTION = """
-
"""


def mk_positions_gen(ar_1, mode="NA"):
    if mode == "NA":
        for k, kv in enumerate(ar_1):
            yield (kv,)


def mk_data_shape(ar_1, mode="NA"):
    if mode == "NA":
        return (len(ar_1),)


def mk_indices_gen(ar_1, mode="NA"):
    if mode == "NA":
        for k, v in enumerate(ar_1):
            yield k,


def mk_ranges_consistent(settings, actuator_names=("1", "2", "3")):
    return
