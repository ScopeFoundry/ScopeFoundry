import unittest

from ScopeFoundry import BaseMicroscopeApp, HardwareComponent, Measurement


class Measure1(Measurement):
    name = "measure1"

    def setup(self):
        self.settings.New("string", str, ro=True, initial="0")


class Hardware1(HardwareComponent):
    name = "hardware1"

    def setup(self):
        self.settings.New("string", str, ro=True, initial="0")
        self.settings.New("float", float, ro=True, initial=0.0)
        self.settings.New("int", float, ro=True, initial=0.0)

    def connect(self):
        self.settings.get_lq("string").connect_to_hardware(print, None)
        self.settings.get_lq("float").connect_to_hardware(print, print)
        self.settings.get_lq("int").connect_to_hardware(None, print)

    def disconnect(self):
        self.settings.disconnect_all_from_hardware()


class App(BaseMicroscopeApp):

    mdi = False

    def setup(self):
        self.add_measurement(Measure1(self))
        self.hw = self.add_hardware(Hardware1(self))

class GetSettingsTest(unittest.TestCase):

    def setUp(self):
        self.app = App([])
        self.hw = self.app.hw

    def test_settings_persistance(self):
        all_settings_0 = list(self.app.get_setting_paths())
        self.hw.connect()
        self.assertListEqual(all_settings_0, list(self.app.get_setting_paths()))
        self.hw.disconnect()
        self.assertListEqual(all_settings_0, list(self.app.get_setting_paths()))

    def test_filter_has_hardware_read(self):
        self.hw.connect()
        self.assertListEqual(
            ["hw/hardware1/string", "hw/hardware1/float"],
            list(self.app.get_setting_paths(filter_has_hardware_read=True)),
        )
        self.hw.disconnect()
        self.assertListEqual(
            [], list(self.app.get_setting_paths(filter_has_hardware_read=True))
        )

    def test_filter_has_hardware_write(self):
        self.hw.connect()
        self.assertListEqual(
            ["hw/hardware1/float", "hw/hardware1/int"],
            list(self.app.get_setting_paths(filter_has_hardware_write=True)),
        )
        self.hw.disconnect()
        self.assertListEqual(
            [], list(self.app.get_setting_paths(filter_has_hardware_write=True))
        )

    def test_filter_has_hardware_read_and_write(self):
        self.hw.connect()
        self.assertListEqual(
            ["hw/hardware1/float", "hw/hardware1/int"],
            list(self.app.get_setting_paths(filter_has_hardware_write=True)),
        )
        self.hw.disconnect()
        self.assertListEqual(
            [], list(self.app.get_setting_paths(filter_has_hardware_write=True))
        )

    def test_ro(self):
        self.assertSetEqual(
            {
                "mm/measure1/activation",
                "mm/measure1/profile",
                "hw/hardware1/debug_mode",
                "hw/hardware1/connected",
            },
            set(
                self.app.get_setting_paths(exclude_ro=True, exclude_patterns=("app/*",))
            ),
        )

    def test_pattern(self):
        self.assertSetEqual(
            {
                "hw/hardware1/debug_mode",
                "hw/hardware1/int",
                "hw/hardware1/float",
                "hw/hardware1/string",
            },
            set(
                self.app.get_setting_paths(
                    exclude_patterns=("mm/*", "app/*", "*connected")
                )
            ),
        )


if __name__ == "__main__":
    unittest.main()
