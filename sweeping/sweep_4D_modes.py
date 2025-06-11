SCAN_MODES = ("co-move", "nested", "1,2_nested_3,4_co-move")
SCAN_MODES_DESCRIPTION = """
<p><i>co-move:</i> all actuators co-move
<p><i>nested:</i> actuators move all combinations where 1st is slowest ...
<p><i>1,2_nested_3,4_co-move:</i> 1st and 2nd move all combinations, 3rd and 4th move simultaneously
"""


def mk_positions_gen(ar_1, ar_2, ar_3, ar_4, mode="nested"):
    if mode == "nested":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                for m, mv in enumerate(ar_3):
                    for n, nv in enumerate(ar_4):
                        yield (kv, lv, mv, nv)

    elif mode == "co-move":
        for k, v in enumerate(ar_1):
            yield (ar_1[k], ar_2[k], ar_3[k], ar_4[k])

    elif mode == "1,2_nested_3,4_co-move":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                for m, mv in enumerate(ar_3):
                    yield (kv, lv, ar_3[m], ar_4[m])


def mk_data_shape(ar_1, ar_2, ar_3, ar_4, mode="nested"):
    if mode == "nested":
        return len(ar_1), len(ar_2), len(ar_3), len(ar_4)
    elif mode == "co-move":
        return 1, 1, 1, len(ar_4)
    elif mode == "1,2_nested_3,4_co-move":
        return len(ar_1), len(ar_2), 1, len(ar_4)


def mk_indices_gen(ar_1, ar_2, ar_3, ar_4, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            for l, v in enumerate(ar_2):
                for m, v in enumerate(ar_3):
                    for n, v in enumerate(ar_4):
                        yield k, l, m, n

    elif mode == "co-move":
        for n, v in enumerate(ar_4):
            yield 0, 0, 0, n

    elif mode == "1,2_nested_3,4_co-move":
        for k, v in enumerate(ar_1):
            for l, v in enumerate(ar_2):
                for n, v in enumerate(ar_4):
                    yield k, l, 0, n


def mk_ranges_consistent(settings, actuator_names=("1", "2", "3", "4")):
    if settings["scan_mode"] == "co-move":
        print(settings["scan_mode"])
        print(
            "all actuator take num steps from actuator 4:",
            settings[f"range_{actuator_names[-1]}_num"],
        )
        for i in actuator_names[:3]:
            settings[f"range_{i}_num"] = settings[f"range_{actuator_names[-1]}_num"]

    elif settings["scan_mode"] == "1,2_nested_3,4_co-move":
        print(settings["scan_mode"])
        print(
            f"actuator {actuator_names[2]} takes num steps from {actuator_names[3]}:",
            settings[f"range_{actuator_names[3]}_num"],
        )
        settings[f"range_{actuator_names[2]}_num"] = settings[
            f"range_{actuator_names[3]}_num"
        ]
