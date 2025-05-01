N_DIMS = 2
DIM_NUMS = "12"
SCAN_MODES = ("co-move", "nested")
SCAN_MODES_DESCRIPTION = """
<p><i>co-move:</i> all actuators co-move
<p><i>nested:</i> actuators move all combinations where 1st is slowest ...
"""


def mk_positions_gen(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                yield (kv, lv)

    elif mode == "co-move":
        for l, lv in enumerate(ar_2):
            yield (ar_1[l], ar_2[l])


def mk_data_shape(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        return len(ar_1), len(ar_2)
    elif mode == "co-move":
        return 1, len(ar_2)


def mk_indices_gen(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            for l, v in enumerate(ar_2):
                yield k, l

    elif mode == "co-move":
        for l, v in enumerate(ar_2):
            yield 0, l


def mk_ranges_consistent(settings):
    if settings["scan_mode"] == "co-move":
        print(settings["scan_mode"])
        print("actuator 1 takes num steps from actuator 2:", settings[f"range_2_num"])
        settings[f"range_1_num"] = settings["range_2_num"]
