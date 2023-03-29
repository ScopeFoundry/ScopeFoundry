from .new_hw import ComTypes, new_hw
from .new_hw_qt_view import NewHWView as View
from .utils import InfoTypes, decorate_info_text


class NewHWController:
    def __init__(self, view: View):
        self.view = view
        view.set_com_types_options([t.value for t in ComTypes])
        view.model_text_changed(self.non_overwrite_guess)
        view.pretty_name_text_changed(self.on_pretty_name_set)
        view.guess_button_clicked(self.guess_pretty_name)
        view.com_texted_changed(self.on_change_com_type)
        view.create_clicked(self.on_create)
        view.set_overwrite(False)
        self.is_pretty_name_set = False
        self.set_msg(WELCOME_TEXT)

    def set_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.set_info_text(text)

    def append_msg(self, text, info_type=InfoTypes.INFO):
        text = decorate_info_text(text, info_type)
        self.view.append_info(text)

    def new_task_msg(self, text):
        self.set_msg(text, InfoTypes.TASK)

    def on_change_com_type(self, t):
        dev_type = ComTypes(t)
        if dev_type == ComTypes.SERIAL:
            self.set_msg(
                f'choose {t} if you have found a Baudrate in device documentation!')
        elif dev_type == ComTypes.DLL:
            self.set_msg(
                f'choose {t} if you have file and either a documentation or a .h header file with it')
        elif dev_type == ComTypes.OTHER:
            self.set_msg(
                f"""choose {t} if you your strategy to handle low level communication 
                with a python library from the manufacturer, or from a trusted internet source or have another idea.""")

    def on_pretty_name_set(self):
        self.is_pretty_name_set = True

    def on_create(self):
        self.new_task_msg('creating a new hardware')

        company = self.view.get_company()
        model = self.view.get_model()
        for name, required_field in (('company', company), ('model', model)):
            if required_field == "":
                self.set_msg(f"{name} is required", InfoTypes.FAILED)
                return

        overwrite_existing_module = self.view.get_overwrite()
        dev_type = ComTypes(self.view.get_com_option())
        authors = self.view.get_authors()
        if authors == "":
            authors = 'Mysterion'
            self.view.set_authors(authors)
        pretty_name = self.view.get_pretty_name()
        if pretty_name == "":
            pretty_name = make_pretty_name(model)
            self.view.set_pretty_name(pretty_name)

        for verboten in (" ", "-"):
            if verboten in model:
                self.view.set_model(self._clean_verboten(model, verboten))
                return
            if verboten in company:
                self.view.set_company(self._clean_verboten(company, verboten))
                return
            if verboten in pretty_name:
                self.view.set_pretty_name(
                    self._clean_verboten(pretty_name, verboten))
                return

        try:
            module_name = new_hw(company, model, authors, pretty_name,
                                 overwrite_existing_module, dev_type)
        except FileExistsError as e:
            self.set_msg("Failed: " + str(e), InfoTypes.FAILED)
            return

        self.set_msg(
            f"""created ScopeFoundryHW/{module_name}""",
            InfoTypes.SUCCESS)
        self.append_msg(next_steps(module_name))

    def _clean_verboten(self, text, verboten):
        self.append_msg(
            f'{repr(verboten)} in {text} not allowed: replaced with _', InfoTypes.FAILED)
        return "_".join(text.split(verboten))

    def non_overwrite_guess(self, text=None):
        if not self.is_pretty_name_set:
            self.guess_pretty_name()

    def guess_pretty_name(self):
        model = self.view.get_model()
        self.view.set_pretty_name(make_pretty_name(model))


def make_pretty_name(model: str):
    s = model.split('_')
    if len(s) >= 2:
        name = '_'.join(s[-2:])
    else:
        name = model
    return name.lower()


def next_steps(module_name):
    return f"""<p>typical Next Steps:</p>
            1. run ScopeFoundryHW/{module_name}/*_test_app.py as initial test.<br>
            2. get ScopeFoundryHW/{module_name}/*_dev file to work with your costum read and write functions<br>
            3. in ScopeFoundryHW/{module_name}/*_hw add settings to *_hw file, connect to your read and write functions<br>
            4. test extensivly. <br>
            5. update README.md and publish on GitHub because sharing is caring. <br>
            <br><br>
            Good Luck! <br>
            - UBene.
            """


WELCOME_TEXT = """Although doing some thinking is here is recommended, 
    everything can be changed latter! Defintely have a strategy 
    for your low level communication before you start.
    <br>
    <br>
    a quick google search to see if there already exist a pluggin that you can adapt might 
    save you a lot of time. Use import from github in that case
    """
