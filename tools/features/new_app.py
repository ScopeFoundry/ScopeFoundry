# intended to make a new setup by running:
# python -m ScopeFoundry.tools.new_setup

import os
import re
import shutil
import tempfile
from pathlib import Path


def convert_import_statement(original_import: str) -> str:
    """
    Convert a ScopeFoundry examples import statement to a local module import statement.

    Parameters:
    original_import (str): The original import statement.

    Returns:
    str: The converted import statement.
    """
    pattern = r"from ScopeFoundry\.examples\.((?:\w+\.)*\w+) imp(\w+)"
    replacement = r"from \1 imp\2"
    new_import = re.sub(pattern, replacement, original_import)
    return new_import


def apply_import_statement_conversion(input_file_path: str) -> None:
    """
    Parameters:
    input_file_path (str): The path to the input Python file.
    """
    with tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
        temp_file_path = temp_file.name
        with open(input_file_path, "r") as infile:
            for line in infile:
                temp_file.write(convert_import_statement(line))

    os.replace(temp_file_path, input_file_path)


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
            apply_import_statement_conversion(dest_file_path)
            print(f"Copied {file_path} to {dest_file_path} and adjusted imports")


def new_app() -> str:
    copy_scopefoundry_examples()
    print(
        """
test installation by calling
    
    python -m example_slowscan_app

rename/modify *app.py file to your liking.
"""
    )
    return "python -m example_slowscan_app"


if __name__ == "__main__":
    new_app()
