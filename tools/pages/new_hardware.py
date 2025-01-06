from qtpy import QtWidgets

from ScopeFoundry.tools.page import Page
from ScopeFoundry.tools.features.new_hw import ComTypes, new_hw


class NewHardware(Page):
    def setup(self) -> None:
        self.name = "new hardware"
        self.settings.New("company", dtype=str, initial="thorlabs")
        m = self.settings.New(
            "series or model", dtype=str, initial="XX312_Piezo_Controller"
        )
        self.settings.New("authors", dtype=str, initial="Benedikt Ursprung")
        p = self.settings.New("pretty name", dtype=str, initial="")

        p.connect_lq_math((m,), make_pretty_name)

        self.settings.New("communication type", str, choices=ComTypes)
        self.settings.New("overwrite existing", bool, initial=False)

        self.operations.new("create new hardware", self.new_hardware)

        self.settings.New(
            "import",
            dtype=str,
            default_widget_factory=QtWidgets.QTextEdit,
            is_clipboardable=True,
        )
        self.settings.New("run", str, is_cmd=True, is_clipboardable=True)

        self.operations.new("create", self.new_hardware)
        self.procedure = (
            "define name and press create",
            "company",
            "series or model",
            "authors",
            "communication type",
            "pretty name",
            "overwrite existing",
            "create new hardware",
            "run to test & copy paste to your apps setup function",
            "run",
            "import",
        )

    def new_hardware(self) -> None:
        company = self.settings["company"]
        model = self.settings["series or model"]
        overwrite_existing_module = self.settings["overwrite existing"]
        dev_type = self.settings["communication type"]
        authors = self.settings["authors"]
        if authors == "":
            authors = "Mysterion"
            self.settings["authors"] = authors
        pretty_name = self.settings["pretty name"]
        if pretty_name == "":
            pretty_name = make_pretty_name(model)
            self.settings["pretty name"] = pretty_name

        for verboten in (" ", "-"):
            if verboten in model:
                self.settings["series or model"] = self._clean_verboten(model, verboten)
                return
            if verboten in company:
                self.settings["company"] = self._clean_verboten(company, verboten)

                return
            if verboten in pretty_name:
                self.settings["pretty name"] = self._clean_verboten(
                    pretty_name, verboten
                )
                return

        try:
            info = new_hw(
                company,
                model,
                authors,
                pretty_name,
                overwrite_existing_module,
                dev_type,
            )
        except FileExistsError as e:
            print("Failed: " + str(e))
            return

        print(f"""created ScopeFoundryHW/{info['MODULE_NAME']}""")

        self.settings["import"] = info["ADD_TO_APP"]
        self.settings["run"] = (
            f"python -m ScopeFoundryHW.{info['MODULE_NAME']}.{info['TEST_APP_FILE_NAME'].replace('test_app.py', 'test_app')}"
        )

    def _clean_verboten(self, text: str, verboten: str) -> str:
        return "_".join(text.split(verboten))


def make_pretty_name(model: str) -> str:
    s = model.split("_")
    if len(s) >= 2:
        name = "_".join(s[-2:])
    else:
        name = model
    return name.lower()
