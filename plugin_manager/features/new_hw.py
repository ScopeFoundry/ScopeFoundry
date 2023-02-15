import datetime
from enum import Enum
from functools import partial
from pathlib import Path
from re import sub
from string import Template


class ComTypes(Enum):
    OTHER = 'OTHER'
    DLL = 'DLL'
    SERIAL = 'SERIAL'
    # VISA = 'VISA'


def to_class_name(s):
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join([s[0].upper(), s[1:]])


def do_template_file(template_file, target_file_name, substitutions, path_to_module):
    with open(template_file, 'r') as f:
        template = Template(f.read())

    with open(path_to_module / Path(target_file_name), 'w') as f:
        f.write(template.substitute(**substitutions))


def new_hw(company='thorlabs',
           model='XX6000_glavo_mirror',
           authors='Benedikt Ursprung, Mark E.Ziffer',
           pretty_name='galvo_mirror',
           overwrite_existing_module=True,
           com_type=ComTypes.DLL):

    module_name = f"{company.lower()}_{model.lower()}"
    path_to_module = Path('../../ScopeFoundryHW') / Path(module_name)

    if path_to_module.exists() and not overwrite_existing_module:
        raise FileExistsError(
            f'{module_name} already exists! You can use overwrite flag at your own risk')

    today = datetime.datetime.today()
    pretty_date = today.strftime("%b %d, %Y")
    year = today.strftime("%Y")

    if pretty_name is None or pretty_name == "":
        pretty_name = (model.lower())
    pretty_name = pretty_name.lower()

    dev_file_name = pretty_name + '_dev.py'
    dev_class_name = to_class_name(model.upper() + '_DEV')
    import_dev = f"from .{dev_file_name.rstrip('.py')} import {dev_class_name}"

    hw_file_name = pretty_name.lower() + '_hw.py'
    hw_class_name = to_class_name(model.upper() + '_HW')

    readout_file_name = pretty_name.lower() + '_readout.py'
    readout_class_name = to_class_name(model.upper() + '_Readout')

    test_app_file_name = pretty_name.lower() + '_test_app.py'

    print(hw_file_name, hw_file_name.rstrip('.py'))

    init_imports = f"from .{hw_file_name.rstrip('.py')} import {hw_class_name} \nfrom .{readout_file_name.rstrip('.py')} import {readout_class_name}"
    test_app_imports = f"from ScopeFoundryHW.{module_name.rstrip('.py')} import {hw_class_name}, {readout_class_name}"

    print(init_imports)

    substitutions = {
        'DATE_PRETTY': pretty_date,
        'YEAR': year,
        'AUTHORS': authors,
        'AUTHORS_SPLIT_NEWLINE': '\n'.join(authors.split(', ')),
        'DEV_CLASS_NAME': dev_class_name,
        'IMPORT_DEV': import_dev,
        'HW_CLASS_NAME': hw_class_name,
        'READOUT_CLASS_NAME': readout_class_name,
        'READOUT_NAME': pretty_name.lower() + '_readout',
        'TEST_APP_NAME': pretty_name.lower() + '_test_app',
        'HW_NAME': pretty_name.lower(),
        'INIT_IMPORTS': init_imports,
        'IMPORTS_IN_TEST_APP': test_app_imports,
        'MODULE_NAME': module_name,
        'COMPANY': " ".join(company.split('_')),
        'MODEL': " ".join(model.split('_'))
    }

    path_to_module.mkdir(exist_ok=True)
    do = partial(do_template_file,
                 substitutions=substitutions,
                 path_to_module=path_to_module
                 )

    do('templates/_readout.py', readout_file_name)
    do('templates/_test_app.py', test_app_file_name)
    do('templates/___init__.py', '__init__.py')
    do('templates/_LICENSE', 'LICENSE')
    do('templates/_README.md', 'README.md')

    if com_type == ComTypes.DLL:
        do('templates/_dll_dev.py', dev_file_name)
        do('templates/_dll_hw.py', hw_file_name)
    if com_type == ComTypes.SERIAL:
        do('templates/_serial_dev.py', dev_file_name)
        do('templates/_serial_hw.py', hw_file_name)
    if com_type == ComTypes.OTHER:
        do('templates/_serial_dev.py', dev_file_name)
        do('templates/_serial_hw.py', hw_file_name)

    return module_name


if __name__ == '__main__':
    new_hw(com_type=ComTypes.SERIAL)
