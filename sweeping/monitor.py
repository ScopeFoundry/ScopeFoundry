import threading
import time

from ScopeFoundry import LQCollection

DESCRIPTION = "Periodically reads a setting value during the sweep measurement (free running in parallel). Records start/stop indices for events, enabling correlation between recorded values and measurement data at specific time points."


class MonitorBase:
    """Monitor that runs periodic functions and tracks events."""

    def __init__(self, name="monitor"):
        self.name = name
        self.description = DESCRIPTION
        self._monitor_thread = None
        self._running = False
        self._stop_event = None
        # Dict of event_name -> list of (start_index, stop_index) pairs
        self._event_pairs = {}
        self._pending_starts = {}
        self._current_index = 0
        self.values = []  # Initialize data storage
        self.settings = LQCollection()
        self.settings.New(
            name="enabled",
            dtype=bool,
            initial=True,
            description="Enable/disable this monitor",
        )
        self.settings.New(
            name="update_period",
            dtype=float,
            initial=1.0,
            unit="s",
            description="Time period between monitor function calls",
        )
        self.setup()

    def setup(self):
        pass

    def start(self):
        """Start monitoring thread that calls function periodically with running index."""
        if self._running or not self.settings["enabled"]:
            return

        self._running = True
        self._stop_event = threading.Event()
        self._current_index = 0
        self.values = []

        def _monitor_loop():
            while not self._stop_event.is_set():
                try:
                    self.values.append(self.monitor_function())
                    self._current_index += 1

                    # Wait for update period or until stop event
                    if self._stop_event.wait(self.settings["update_period"]):
                        break

                except Exception as e:
                    print(f"Monitor error: {e}")
                    break

            self._running = False

        # Always create a new thread (threads cannot be restarted)
        self._monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        """Stop the monitoring thread."""
        if self._running:
            self._stop_event.set()
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2.0)
            self._running = False

    def inform(self, event_message=""):
        """Store current index when called for start/stop event pairs.

        Args:
            event_message: Message in format "start_X" or "stop_X"
        """
        if not self.settings["enabled"]:
            return

        if event_message.startswith("start_"):
            event_name = event_message[6:]  # Remove "start_" prefix
            self._pending_starts[event_name] = self._current_index
            # print(f"Monitor start event '{event_name}' at index {self._current_index}")

        elif event_message.startswith("stop_"):
            event_name = event_message[5:]  # Remove "stop_" prefix
            if event_name in self._pending_starts:
                start_index = self._pending_starts.pop(event_name)
                if event_name not in self._event_pairs:
                    self._event_pairs[event_name] = []
                self._event_pairs[event_name].append((start_index, self._current_index))
                # print(
                #     f"Monitor stop event '{event_name}' at index {self._current_index} (paired with start at {start_index})"
                # )
            else:
                print(
                    f"Warning: stop event '{event_name}' at index {self._current_index} has no matching start event"
                )
        else:
            print(
                f"Warning: event message '{event_message}' should start with 'start_' or 'stop_'"
            )

    def is_enabled(self):
        """Return whether this monitor is enabled."""
        return self.settings["enabled"]

    def get_events(self):
        """Return dict of event names mapped to lists of (start_index, stop_index) pairs."""
        return self._event_pairs.copy()

    def get_pending_starts(self):
        """Return dict of event names with unpaired start events."""
        return self._pending_starts.copy()

    def clear_events(self):
        """Clear all recorded events and pending starts."""
        self._event_pairs.clear()
        self._pending_starts.clear()

    def monitor_function(self) -> float:
        """Default monitor function that prints the index."""
        print(f"Monitor tick: {self._current_index}")
        return self._current_index

    @property
    def prefix(self) -> str:
        return self.name

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()


class SettingMonitor(MonitorBase):
    """Monitor that tracks changes to a specific setting."""

    def __init__(self, name="setting_monitor", app=None):
        super().__init__(name=name)
        self.app = app

    def setup(self):
        self.settings.New(
            name="setting",
            dtype=str,
            initial="default",
            choices=["default", "option1", "option2"],
            description="Setting to monitor for changes",
        )

    def monitor_function(self):
        """Check for changes in the monitored setting."""
        return self.app.get_lq(self.settings["setting"]).read_from_hardware()

    @property
    def prefix(self) -> str:
        return self.settings["setting"].replace("/", "__")


if __name__ == "__main__":

    # Create and add monitors
    monitor = MonitorBase("my_monitor")
    monitor.setup()
    monitor.settings["update_period"] = 0.5

    monitor.start()

    # Let it run for a few seconds
    time.sleep(1)
    monitor.inform("start_test")
    time.sleep(2)
    monitor.inform("stop_test")
    time.sleep(1)
    monitor.inform("start_test_2")
    monitor.inform("start_test")
    monitor.inform("stop_test_2")
    time.sleep(1)
    monitor.stop()

    print("Recorded events:", monitor.get_events())
