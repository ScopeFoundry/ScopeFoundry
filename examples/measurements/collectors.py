# required for Sweep4d example


from ScopeFoundry import Collector


class Noiser200Collector(Collector):
    name = "noiser200"
    repeated_dset_names = ("signals",)
    acquisition_duration_path = "mm/noiser200/capture_duration"

    def run(
        self,
        index,
        host_measurement,
        polling_func=None,
        polling_time=0.001,
        int_time=None,
        *args,
        **kwargs
    ):
        # needs to define self.data with reapated_dset_names
        self.data["signals"] = self.app.get_lq(
            "hw/noiser_200/signal"
        ).read_from_hardware()
