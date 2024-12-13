from typing import Callable

from qtpy import QtCore

from ScopeFoundry import LQCollection
from ScopeFoundry.operations import Operations


class ViewQObject(QtCore.QObject):
    pass


class DataBrowserView:
    """Abstract class for DataBrowser Views"""

    name = "base_view"  # override me! (recommended to use the ScopeFoundry.Measurement.name)

    def __init__(self, databrowser):
        self.databrowser = databrowser
        self.settings = LQCollection(path=f"view/{self.name}")
        self.operations = Operations()
        self.q_object = ViewQObject()
        self._subtree_managers_ = []
        self._widgets_managers_ = []
        self.view_loaded = False
        self.ui = None

    def setup(self):
        pass
        # create view with no data file

    def on_change_data_filename(self, fname=None):
        pass
        # load data file

        # update display

    def is_file_supported(self, fname):
        """
        returns whether view can handle file, should return False early to avoid
        too much computation when selecting a file.

        Override me if this fallback does not behave as expected. In particular
            if self.name is not the supported measurement name
            or if supported file is not an h5 file
        """
        return self.check_h5_file_support(fname, (self.name,))

    def check_h5_file_support(self, fname, supported_measurement_names):
        """
        helper function to check if h5 file *fname* has group 'measurement/X'
        where X is any element of *supported_measurement_names*
        """
        if not fname.endswith(".h5"):
            return False

        if isinstance(supported_measurement_names, str):
            supported_measurement_names = (supported_measurement_names,)

        import h5py

        with h5py.File(fname) as file:
            return any(
                name in file["measurement"] for name in supported_measurement_names
            )

    def add_operation(
        self, name: str, op_func: Callable[[], None], description="", icon_path=""
    ):
        self.operations.new(name, op_func, description, icon_path)

    def remove_operation(self, name: str):
        self.operations.remove(name)
