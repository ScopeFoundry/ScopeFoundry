import sys

from ScopeFoundry.data_browser import DataBrowser

DEFAULT_PATH = r"C:\Users\bened\OneDrive\PHD\data_analysis\changwhan"

if __name__ == "__main__":
    app = DataBrowser(sys.argv)

    from ScopeFoundry.data_browser.plug_ins.h5_search import H5SearchPlugIn
    from ScopeFoundry.data_browser.plug_ins.time_note import TimeNote

    app.add_plugin(H5SearchPlugIn(app))
    app.add_plugin(TimeNote(app))

    app.settings.browse_dir.update_value(DEFAULT_PATH)
    sys.exit(app.exec_())
