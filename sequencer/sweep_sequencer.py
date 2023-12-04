from qtpy.QtWidgets import QHBoxLayout

from .sequencer import Sequencer


class SweepSequencer(Sequencer):
    name = "sweep_sequencer"

    def setup(self):
        Sequencer.setup(self)
        self.range = self.settings.New_Range(
            "range",
            include_sweep_type=True,
            initials=[67, 410, 10],
            description=RANGEDESCRIPTION,
            spinbox_decimals=5,
        )
        self.settings.New("current_range_value", ro=True)
        self.settings.New("ignore_sweep", bool, initial=False)

    def setup_figure(self):
        Sequencer.setup_figure(self)
        layout = QHBoxLayout()
        layout.addWidget(self.range.New_UI())
        layout.addWidget(self.settings.New_UI(["current_range_value", "ignore_sweep"]))
        self.layout.insertLayout(1, layout)
        try:
            self.editors["update-setting"].ui.value_le.setText(
                "measurement/sweep_sequencer/current_range_value"
            )
        except AttributeError:
            pass

    def run(self):
        if self.settings["ignore_sweep"]:
            Sequencer.run(self)
        else:
            values = self.range.sweep_array
            for i, x in enumerate(values):
                if self.interrupt_measurement_called:
                    break
                self.settings["current_range_value"] = x
                # print(self.name, 'current_range_value', x)
                self.set_progress(100.0 * i / len(values))
                Sequencer.run(self)


RANGEDESCRIPTION = """use <i>measurement/sweep_sequencer/current_range_value</i> 
to update the setting you want to sweep"""
