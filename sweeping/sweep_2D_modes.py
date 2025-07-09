SCAN_MODES = (
    "co-move",
    "nested",
    "nested_swap_order",
    "serpentine",
    "serpentine_swap_order",
)
SCAN_MODES_DESCRIPTION = """
<p><i>co-move:</i> all actuators co-move
<p><i>nested:</i> actuators move all combinations where 1st is slowest ...
<p><i>serpentine:</i> actuators move all combinations where 1st is slowest, 2nd is fastest and 2nd reverses direction every row.
<p><i>*_swap_order</i> modes are the same as above, but the order of the actuators is swapped.</p>
"""


def mk_positions_gen(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        for k, kv in enumerate(ar_1):
            for l, lv in enumerate(ar_2):
                yield (kv, lv)

    if mode == "nested_swap_order":
        for l, lv in enumerate(ar_2):
            for k, kv in enumerate(ar_1):
                yield (kv, lv)

    elif mode == "co-move":
        for l, lv in enumerate(ar_2):
            yield (ar_1[l], ar_2[l])

    elif mode == "serpentine":
        for k, kv in enumerate(ar_1):
            if k % 2 == 0:
                for l, lv in enumerate(ar_2):
                    yield (kv, lv)
            else:
                for l, lv in reversed(list(enumerate(ar_2))):
                    yield (kv, lv)

    elif mode == "serpentine_swap_order":
        for l, lv in enumerate(ar_2):
            if l % 2 == 0:
                for k, kv in enumerate(ar_1):
                    yield (kv, lv)
            else:
                for k, kv in reversed(list(enumerate(ar_1))):
                    yield (kv, lv)


def mk_data_shape(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        return len(ar_1), len(ar_2)
    elif mode == "nested_swap_order":
        return len(ar_2), len(ar_1)
    elif mode == "co-move":
        return 1, len(ar_2)
    elif mode == "serpentine":
        return len(ar_1), len(ar_2)


def mk_indices_gen(ar_1, ar_2, mode="nested"):
    if mode == "nested":
        for k, v in enumerate(ar_1):
            for l, v in enumerate(ar_2):
                yield k, l

    elif mode == "nested_swap_order":
        for l, lv in enumerate(ar_2):
            for k, kv in enumerate(ar_1):
                yield k, l

    elif mode == "co-move":
        for l, v in enumerate(ar_2):
            yield 0, l

    elif mode == "serpentine":
        for k, v in enumerate(ar_1):
            if k % 2 == 0:
                for l, v in enumerate(ar_2):
                    yield k, l
            else:
                for l, v in reversed(list(enumerate(ar_2))):
                    yield k, l

    elif mode == "serpentine_swap_order":
        for l, v in enumerate(ar_2):
            if l % 2 == 0:
                for k, v in enumerate(ar_1):
                    yield k, l
            else:
                for k, v in reversed(list(enumerate(ar_1))):
                    yield k, l


def mk_ranges_consistent(settings, actuator_names=("1", "2")):
    if settings["scan_mode"] == "co-move":
        print(settings["scan_mode"])
        print(
            f"actuator {actuator_names[0]} takes num steps from actuator {actuator_names[1]}:",
            settings[f"range_{actuator_names[0]}_num"],
        )
        settings[f"range_{actuator_names[0]}_num"] = settings[
            f"range_{actuator_names[1]}_num"
        ]
