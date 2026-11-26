import time
import unittest

from ScopeFoundry import BaseMicroscopeApp, Measurement, Sweep1D
from ScopeFoundry.tests.unittests.unittest_helpers import close_app_widgets


class QuickNestedMeasurement(Measurement):
    name = "quick_nested_measurement"

    def __init__(self, app):
        self.completed_runs = 0
        super().__init__(app)

    def run(self):
        time.sleep(0.1)
        self.completed_runs += 1


class NestedWaitSweep1D(Sweep1D):
    name = "nested_wait_sweep_1d"

    def __init__(self, app, nested_measurement, repetitions):
        self.nested_measurement = nested_measurement
        self.repetitions = repetitions
        self.nested_results = []
        super().__init__(
            app,
            actuator_names=(),
            range_n_intervals=(),
            n_any_measurements=0,
            n_read_any_settings=0,
        )

    def run(self):
        for _ in range(self.repetitions):
            if self.interrupt_measurement_called:
                break
            self.nested_results.append(
                self.start_nested_measure_and_wait(self.nested_measurement)
            )


class TestSweep1DNestedMeasurement(unittest.TestCase):
    def test_repeated_nested_start_and_wait(self):
        app = BaseMicroscopeApp([])
        self.addCleanup(close_app_widgets, app)
        nested = QuickNestedMeasurement(app)
        sweep = NestedWaitSweep1D(app, nested, repetitions=30)

        sweep.start()
        deadline = time.monotonic() + 10
        while sweep.is_measuring() and time.monotonic() < deadline:
            app.qtapp.processEvents()
            time.sleep(0.005)
        app.qtapp.processEvents()

        if sweep.is_thread_alive():
            sweep._interrupt()
            sweep.acq_thread.wait(1000)

        self.assertFalse(sweep.is_measuring(), "Sweep1D did not finish in time")
        self.assertEqual(sweep.settings["run_state"], "stop_success")
        self.assertEqual(nested.completed_runs, 30)
        self.assertEqual(sweep.nested_results, [True] * 30)
        self.assertEqual(nested.settings["run_state"], "stop_success")


if __name__ == "__main__":
    unittest.main()
