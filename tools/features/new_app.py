# intended to make a new setup by running:
# python -m ScopeFoundry.tools.new_setup

import re
import shutil
from pathlib import Path


def convert_import_statement(import_line: str) -> str:
    pattern = r"from ScopeFoundry\.examples\.((?:\w+\.)*\w+) imp(\w+)"
    replacement = r"from \1 imp\2"
    new_import = re.sub(pattern, replacement, import_line)
    return new_import


def convert_import_statements(input_file_path: str) -> None:
    with open(input_file_path, "r") as infile:
        lines = infile.readlines()

    with open(input_file_path, "w") as outfile:
        for line in lines:
            outfile.write(convert_import_statement(line))


def copy_scopefoundry_examples() -> None:

    source_dir = Path(__file__).resolve().parent.parent.parent / "examples"
    dest_dir = Path.cwd()

    if not source_dir.exists():
        print(f"Source directory {source_dir} does not exist.")
        return

    for file_path in source_dir.rglob("*"):
        if file_path.is_file():
            if file_path.suffix not in (".py", ".ini", ".json"):
                continue
            relative_path = file_path.relative_to(source_dir)
            dest_file_path = dest_dir / relative_path

            if dest_file_path.exists():
                print(f"Skipped {dest_file_path}, already exists.")
                continue

            dest_file_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(file_path, dest_file_path)
            convert_import_statements(dest_file_path)
            print(f"Copied {file_path} to {dest_file_path} and adjusted imports")


def new_app() -> str:
    copy_scopefoundry_examples()
    print(
        """
test installation by calling
    
    python -m fancy_app

rename/modify *app.py file to your liking.
"""
    )
    return "python -m fancy_app"


if __name__ == "__main__":
    new_app()
