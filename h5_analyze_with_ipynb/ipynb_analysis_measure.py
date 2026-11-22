from ScopeFoundry.h5_analyze_with_ipynb.generate_loaders_py import generate_loaders_py
from ScopeFoundry.h5_analyze_with_ipynb.ipynb_analysis import update_ipynb
from ScopeFoundry.helper_funcs import open_file
from ScopeFoundry.measurement import Measurement


from pathlib import Path
from shutil import copyfile
from typing import Dict


class IpynbAnalysisMeasurement(Measurement):
    """Generate notebook analysis for the microscope's saved data."""

    name = "ipynb_analysis"

    def setup(self):
        self.settings.New(
            "ipynb_option",
            str,
            initial="last",
            choices=["all", "last", "remaining"],
            description="Reserved for a future workflow; microscope analysis currently uses last.",
        )
        self.add_operation(
            "analyze with ipynb",
            self.analyze,
            description="Generates h5_data_loaders.py and overview.ipynb and opens the notebook.",
            icon_path=self.app.icons_path / "jupyter_logo.png",
            keyboard_shortcut="Ctrl+I",
        )
        self.app_scripts_path = self.app.implementation_path / "py_analysis_scripts"
        if not self.app_scripts_path.exists():
            self.app_scripts_path.mkdir()
            (self.app_scripts_path / "__place_py_files_here.md").write_text(
                "Place .py files here that get copied to your data folder "
                "(never overrides, delete at data folder to update).\n"
                "In particular useful to reference with snippets that gets returned "
                "with .get_py_snippets() method of the Measurement properly implemented."
            )

        self.button_layout = self.app._app_widget_buttons_layout
        operation = self.operations.get("analyze with ipynb")
        self.button = operation.new_button()
        self.button.setText(" analyze")
        self.button_layout.insertWidget(1, self.button)

    def _init_py_analysis_directory(self):
        self.py_analysis_scripts_path = self.app_scripts_path
        return self.py_analysis_scripts_path

    def get_snippets(self) -> Dict[str, str]:
        snippets = {}
        for name, measure in self.app.measurements.items():
            if measure is self:
                continue
            try:
                snippet = measure.get_py_snippet()
                if isinstance(snippet, str):
                    snippets[name] = snippet
                else:
                    snippets[name] = f"{name}.get_py_snippet returned: {repr(snippet)}"
            except Exception as err:
                self.log.error(f"Error getting snippet for {name}: {err}")
        return snippets

    def _analysis_inputs(self, folder=None):
        folder = Path(self.app.settings["save_dir"] if folder is None else folder)
        scripts = [
            source
            for measure in self.app.measurements.values()
            if measure is not self
            for source in measure.get_py_analysis_scripts()
        ]
        scripts.extend(self.app_scripts_path.glob("*.py"))
        return folder, self.get_snippets(), scripts

    @staticmethod
    def _generate(folder, snippets, scripts, open_notebook):
        loaders_fname, dset_names = generate_loaders_py(folder)
        ipynb_path = update_ipynb(folder, snippets=snippets, descriptive_snippets=())
        print("")
        print("generated", loaders_fname, f"with {len(dset_names)} loader(s)")
        print("")
        print("check", ipynb_path)
        print("")
        if open_notebook and ipynb_path.exists():
            open_file(ipynb_path)
        for source in scripts:
            target_path = folder / source.name
            if not target_path.exists():
                copyfile(source, target_path)
        return ipynb_path

    def analyze(self, folder=None) -> Path:
        if self.is_measuring():
            raise RuntimeError("Cannot analyze while notebook analysis is running")
        return self._generate(*self._analysis_inputs(folder), open_notebook=True)

    def pre_run(self):
        self._run_inputs = self._analysis_inputs()
        self._run_ipynb_path = None

    def run(self):
        self._run_ipynb_path = self._generate(*self._run_inputs, open_notebook=False)

    def post_run(self):
        if self._run_ipynb_path is not None and self._run_ipynb_path.exists():
            open_file(self._run_ipynb_path)

    def teardown(self):
        self.button_layout.removeWidget(self.button)
        self.button.deleteLater()
