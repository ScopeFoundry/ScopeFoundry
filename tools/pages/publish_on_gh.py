import os
import sys
import webbrowser

from qtpy.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ScopeFoundry.tools.features.publish_on_gh.publish_all_on_gh import publish_on_gh
from ScopeFoundry.tools.page import Page


class PublishOnGH(Page):

    name = "publish on gh"

    def setup(self) -> None:
        self.name = "publish on gh"
        self.settings.new_file(
            "ScopeFoundryHW_dir", str, initial="/ScopeFoundryHW", is_dir=True
        )
        self.settings.New("gh_username", str, initial="ubene")
        self.settings.New("message", str, initial="Initial commit")
        self.settings.New(
            "private_or_public",
            str,
            choices=[("private", "--private"), ("public", "--public")],
            initial="--public",
            description="Choose whether to publish the repository as private or public.",
        )

    def setup_figure(self):
        self.ui = FolderListWidget(self.settings)


from ScopeFoundry.logged_quantity.collection import LQCollection

INSTRUCTIONS_URL = "https://scopefoundry.org/docs/200_hardware-sharing/"


class FolderListWidget(QWidget):

    @property
    def parent_dir(self):
        return self.settings["ScopeFoundryHW_dir"]

    def __init__(self, settings: LQCollection):
        super().__init__()
        self.settings = settings

        # Buttons
        self.instructions_button = QPushButton("Instructions")  # Instructions button

        # Widgets
        root_layout = QHBoxLayout()
        self.current_dir_widget = self.settings.get_lq(
            "ScopeFoundryHW_dir"
        ).new_default_widget()
        # self.select_folder_button = QPushButton("Select ScopeFoundryHW Folder")
        root_layout.addWidget(self.current_dir_widget)
        # root_layout.addWidget(self.select_folder_button)

        # list layout
        self.available_label = QLabel("Available HWs")
        self.selected_label = QLabel("HWs to publish")
        self.available_list = QListWidget()
        self.selected_list = QListWidget()

        left_list_layout = QVBoxLayout()
        right_list_layout = QVBoxLayout()
        left_list_layout.addWidget(self.available_label)
        right_list_layout.addWidget(self.selected_label)
        left_list_layout.addWidget(self.available_list)
        right_list_layout.addWidget(self.selected_list)
        list_layout = QHBoxLayout()
        list_layout.addLayout(left_list_layout)
        list_layout.addLayout(right_list_layout)

        self.move_to_selected_button = QPushButton("Move selected -->")
        self.move_to_available_button = QPushButton("Move selected <--")
        left_list_layout.addWidget(self.move_to_selected_button)
        right_list_layout.addWidget(self.move_to_available_button)

        self.publish_button = QPushButton("Publish!")  # Publish button

        # Connect buttons
        self.instructions_button.clicked.connect(self.open_instructions)
        self.settings.get_lq("ScopeFoundryHW_dir").add_listener(
            self.populate_available_list
        )
        self.move_to_selected_button.clicked.connect(self.move_to_selected)
        self.move_to_available_button.clicked.connect(self.move_to_available)
        self.publish_button.clicked.connect(self.publish_selected)

        # Publish layout
        publish_layout = QVBoxLayout()
        publish_widget = self.settings.New_UI(
            ("gh_username", "message", "private_or_public")
        )
        publish_layout.addWidget(publish_widget)
        publish_layout.addWidget(self.publish_button)

        # Add to main layout
        layout = QVBoxLayout()
        layout.addWidget(self.instructions_button)  # Add Instructions button
        layout.addLayout(root_layout)
        layout.addLayout(list_layout)
        layout.addLayout(publish_layout)  # Add Publish button to layout

        self.setLayout(layout)
        self.setWindowTitle("Publish HW layout")

        self.populate_available_list()

    def populate_available_list(self):
        """Populates the available list with subfolders in the parent directory."""
        self.available_list.clear()
        if not os.path.isdir(self.parent_dir):
            QMessageBox.critical(
                self, "Error", f"{self.parent_dir} is not a valid directory."
            )
            return

        for subfolder in os.listdir(self.parent_dir):
            subfolder_path = os.path.join(self.parent_dir, subfolder)
            if os.path.isdir(subfolder_path):
                self.available_list.addItem(subfolder)

    def move_to_selected(self):
        """Moves selected items from the available list to the selected list."""
        for item in self.available_list.selectedItems():
            self.selected_list.addItem(item.text())
            self.available_list.takeItem(self.available_list.row(item))

    def move_to_available(self):
        """Moves selected items from the selected list back to the available list."""
        for item in self.selected_list.selectedItems():
            self.available_list.addItem(item.text())
            self.selected_list.takeItem(self.selected_list.row(item))

    def publish_selected(self):
        """Callback for the Publish button. Add your publishing logic here."""
        selected_folders = [
            self.selected_list.item(i).text() for i in range(self.selected_list.count())
        ]
        # print(f"Publishing the following folders: {selected_folders}")

        for subfolder in selected_folders:
            subfolder_path = os.path.join(self.parent_dir, subfolder)

            # Skip if not a directory
            if not os.path.isdir(subfolder_path):
                continue
            print(f"Publishing {subfolder_path}")

            publish_on_gh(
                self.settings["gh_username"],
                subfolder,
                subfolder_path,
                message=self.settings["message"],
                private_or_public=self.settings["private_or_public"],
            )

        # Add your publishing logic here

    def open_instructions(self):
        """Opens the instructions webpage in the default browser."""
        webbrowser.open(INSTRUCTIONS_URL)

    def select_folder(self):
        """Opens a dialog to select a folder and updates the parent directory."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", self.parent_dir
        )
        if folder:
            self.settings["ScopeFoundryHW_dir"] = folder
            self.current_dir_widget.setText(f"Current Directory: {self.parent_dir}")
            self.clear_lists()
            self.populate_available_list()

    def clear_lists(self):
        """Clears both lists."""
        self.available_list.clear()
        self.selected_list.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Replace with the path to your parent directory
    parent_directory = "/Users/benediktursprung/Library/CloudStorage/OneDrive-Personal/scope_foundries/scopefoundry_trovatello_lab/ScopeFoundryHW2"

    settings = LQCollection()
    settings.new_file("ScopeFoundryHW_dir", initial="/ScopeFoundryHW", is_dir=True)
    settings.New("gh_username", str, initial="ubene")
    settings.New("message", str, initial="Initial commit")
    settings.New(
        "private_or_public",
        str,
        choices=[("private", "--private"), ("public", "--public")],
        initial="--public",
        description="Choose whether to publish the repository as private or public.",
    )
    widget = FolderListWidget(settings=settings)
    widget.show()

    sys.exit(app.exec_())
