SCAN_MODES = ("co-move", "nested", "2,3_co-move", "1,2_co-move")
SCAN_MODES_DESCRIPTION = """
<p><i>co-move:</i> all actuators co-move
<p><i>nested:</i> actuators move all combinations where 1st is slowest ...
<p><i>2,3_co-move:</i> 2st and 3nd move simultaneously, 1rd moves individually
<p><i>1,2_co-move:</i> 1st and 2nd move simultaneously, 3rd moves individually
"""


def mk_positions_gen(ar_1, ar_2, ar_3, mode="nested"):
    if mode == "nested":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                for m, mv in enumerate(ar_3):
                    yield (kv, lv, mv)

    elif mode == "co-move":
        for k, v in enumerate(ar_1):
            yield (ar_1[k], ar_2[k], ar_3[k])

    elif mode == "2,3_co-move":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                yield (kv, ar_2[l], ar_3[l])

    elif mode == "1,2_co-move":
        for k, kv in enumerate(ar_1):
            for m, mv in enumerate(ar_3):
                yield (ar_1[k], ar_2[k], mv)


def mk_data_shape(ar_1, ar_2, ar_3, mode="nested"):
    if mode == "nested":
        return len(ar_1), len(ar_2), len(ar_3)
    elif mode == "co-move":
        return 1, 1, len(ar_3)
    elif mode == "2,3_co-move":
        return len(ar_1), 1, len(ar_3)
    elif mode == "1,2_co-move":
        return 1, len(ar_2), len(ar_3)


def mk_indices_gen(ar_1, ar_2, ar_3, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            for l, v in enumerate(ar_2):
                for m, v in enumerate(ar_3):
                    yield k, l, m,

    elif mode == "co-move":
        for n, v in enumerate(ar_3):
            yield 0, 0, n

    elif mode == "2,3_co-move":
        for k, v in enumerate(ar_1):
            for m, v in enumerate(ar_3):
                yield k, 0, m

    elif mode == "1,2_co-move":
        for l, v in enumerate(ar_2):
            for m, v in enumerate(ar_3):
                yield 0, l, m


def mk_ranges_consistent(settings, actuator_names=("1", "2", "3")):
    if settings["scan_mode"] == "co-move":
        print(settings["scan_mode"])
        for i in actuator_names[:2]:
            settings[f"range_{i}_num"] = settings[f"range_{actuator_names[-1]}_num"]
    elif settings["scan_mode"] == "2,3_co-move":
        print(settings["scan_mode"])
        settings[f"range_{actuator_names[1]}_num"] = settings[
            f"range_{actuator_names[2]}_num"
        ]
    elif settings["scan_mode"] == "1,2_co-move":
        print(settings["scan_mode"])
        settings[f"range_{actuator_names[0]}_num"] = settings[
            f"range_{actuator_names[1]}_num"
        ]
