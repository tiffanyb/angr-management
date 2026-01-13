from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class CreateProjectDialog(QDialog):
    """Dialog for creating a new project folder."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setMinimumWidth(500)

        self.project_name = None
        self.project_path = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Form layout for project details
        form_layout = QFormLayout()

        # Project name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("my_project")
        form_layout.addRow("Project Name:", self.name_input)

        # Project location input with browse button
        location_layout = QHBoxLayout()
        self.location_input = QLineEdit()
        self.location_input.setText(os.path.expanduser("~"))
        location_layout.addWidget(self.location_input)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_button)

        form_layout.addRow("Location:", location_layout)

        # Full path display
        self.full_path_label = QLabel()
        self.full_path_label.setStyleSheet("color: gray;")
        self._update_full_path()
        form_layout.addRow("Full Path:", self.full_path_label)

        layout.addLayout(form_layout)

        # Connect signals to update full path
        self.name_input.textChanged.connect(self._update_full_path)
        self.location_input.textChanged.connect(self._update_full_path)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _browse_location(self) -> None:
        """Open file dialog to select project location."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Location", self.location_input.text())
        if directory:
            self.location_input.setText(directory)

    def _update_full_path(self) -> None:
        """Update the full path label based on location and name."""
        location = self.location_input.text()
        name = self.name_input.text()
        if location and name:
            full_path = os.path.join(location, name)
            self.full_path_label.setText(full_path)
        else:
            self.full_path_label.setText("")

    def _accept_dialog(self) -> None:
        """Validate and accept the dialog."""
        name = self.name_input.text().strip()
        location = self.location_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a project name.")
            return

        if not location:
            QMessageBox.warning(self, "Invalid Input", "Please select a project location.")
            return

        self.project_name = name
        self.project_path = os.path.join(location, name)

        # Check if directory already exists
        if os.path.exists(self.project_path):
            QMessageBox.warning(
                self,
                "Directory Exists",
                f"The directory '{self.project_path}' already exists.\nPlease choose a different project name or location."
            )
            return

        self.accept()
