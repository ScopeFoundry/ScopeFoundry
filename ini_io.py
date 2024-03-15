"""helpers for handling .ini files"""
import configparser


TRANSLATIONS = {"True": True, "False": False}
REV_TRANSLATIONS = {v: k for k, v in TRANSLATIONS.items()}


def to_path_settings(config):
    settings = {}
    for section, values in config.items():
        for name, val in values.items():
            settings[f"{section}/{name}"] = TRANSLATIONS.get(val, val)
    return settings


def from_path_settings(settings):
    config = configparser.ConfigParser(interpolation=None)

    for path, value in settings.items():
        parts = path.split("/")
        section = "/".join(parts[:-1])
        name = parts[-1]
        if not section in config.sections():
            config.add_section(section)
        config.set(section, name, REV_TRANSLATIONS.get(value, value))

    return config


def laod_ini(fname):
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read(fname)
    return config


def save_ini(ini_fname, config):
    with open(ini_fname, "w") as file:
        config.write(file)


def load_settings(ini_fname):
    return to_path_settings(laod_ini(ini_fname))


def save_settings(ini_fname, settings):
    save_ini(ini_fname, from_path_settings(settings))
