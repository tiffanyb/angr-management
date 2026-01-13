from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


class DockerRunDialog(QDialog):
    """Dialog for configuring Docker run command and container path."""

    def __init__(self, selected_image: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Docker Run Configuration")
        self.setMinimumWidth(500)

        self.selected_image = selected_image
        self.command = None
        self.container_path = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Image info label
        image_label = QLabel(f"Docker Image: {self.selected_image}")
        image_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(image_label)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Command input
        self.command_input = QLineEdit()
        self.command_input.setText("uv run swab /workspace")
        self.command_input.setPlaceholderText("e.g., /bin/bash -c 'python main.py'")
        form_layout.addRow("Command to run:", self.command_input)

        # Container path input
        self.container_path_input = QLineEdit()
        self.container_path_input.setText("/workspace")
        self.container_path_input.setPlaceholderText("e.g., /workspace, /app, /project")
        form_layout.addRow("Copy project to:", self.container_path_input)

        layout.addLayout(form_layout)

        # Help text
        help_text = QLabel(
            "The current project will be copied to the specified path in the container.\n"
            "You can reference files in your command using this path."
        )
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _accept_dialog(self) -> None:
        """Validate and accept the dialog."""
        command = self.command_input.text().strip()
        container_path = self.container_path_input.text().strip()

        if not command:
            QMessageBox.warning(self, "Invalid Input", "Please enter a command to run.")
            return

        if not container_path:
            QMessageBox.warning(self, "Invalid Input", "Please enter a container path.")
            return

        if not container_path.startswith("/"):
            QMessageBox.warning(self, "Invalid Path", "Container path must be an absolute path (start with /).")
            return

        self.command = command
        self.container_path = container_path
        self.accept()
