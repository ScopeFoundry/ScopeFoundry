import datetime
from pathlib import Path
from re import sub
from string import Template
from typing import Dict


def mk_dates() -> Dict[str, str]:
    today = datetime.datetime.today()
    pretty_date = today.strftime("%b %d, %Y")
    year = today.strftime("%Y")
    return {"DATE_PRETTY": pretty_date, "YEAR": year}


def mk_authors(authors: str) -> Dict[str, str]:
    return {
        "AUTHORS": authors,
        "AUTHORS_SPLIT_NEWLINE": "\n".join(authors.split(", ")),
    }


def to_class_name(s: str) -> str:
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return "".join([s[0].upper(), s[1:]])


def write_templated_file(
    template_path: Path,
    target_fname: str,
    substitutions: Dict[str, str],
    path_to_target: Path,
) -> None:
    with open(template_path, "r") as f:
        template = Template(f.read())

    with open(path_to_target / Path(target_fname), "w") as f:
        f.write(template.substitute(**substitutions))
