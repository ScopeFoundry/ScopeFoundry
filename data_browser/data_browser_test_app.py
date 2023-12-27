import sys

from ScopeFoundry.data_browser import DataBrowser
from ScopeFoundry.helper_funcs import sibling_path

DEFAULT_PATH = r"C:\Users\bened\OneDrive"
LOGO_PATH = sibling_path(__file__, "scopefoundry_logo2C_1024.png")

if __name__ == "__main__":
    app = DataBrowser(sys.argv)

    from ScopeFoundry.data_browser.plug_ins.h5_search import H5SearchPlugIn
    from ScopeFoundry.data_browser.plug_ins.time_note import TimeNote

    app.add_plugin(H5SearchPlugIn(app))
    app.add_plugin(TimeNote(app))

    from ScopeFoundry.data_browser.viewers import H5TreeView, RangedOptimizationH5View
    app.add_view(H5TreeView(app))
    app.add_view(RangedOptimizationH5View(app))

    app.settings.browse_dir.update_value(DEFAULT_PATH)
    app.set_logo(LOGO_PATH)

    sys.exit(app.exec_())

