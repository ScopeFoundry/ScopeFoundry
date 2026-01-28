SCAN_MODES = ("nested",)
SCAN_MODES_DESCRIPTION = """
<p><i>nested:</i> Single actuator sweep. Somewhat a trivial case - I know :-)</p>
"""


def mk_positions_gen(ar_1, mode="nested"):
    if mode == "nested" or mode == "position_list":
        for k, kv in enumerate(ar_1):
            yield (kv,)


def mk_data_shape(ar_1, mode="nested"):
    if mode == "nested" or mode == "position_list":
        return (len(ar_1),)


def mk_indices_gen(ar_1, mode="nested"):
    if mode == "nested" or mode == "position_list":
        for k, v in enumerate(ar_1):
            yield k,


def mk_ranges_consistent(settings, actuator_names=("1",)):
    return
