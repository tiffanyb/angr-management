from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)


class ConfigureProjectDialog(QDialog):
    """Dialog for configuring project with simulation engines."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Project")
        self.setMinimumWidth(400)

        self.selected_engines = []

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Description label
        description = QLabel("Select simulation engines to add to your project:")
        layout.addWidget(description)

        # Engines group box
        engines_group = QGroupBox("Simulation Engines")
        engines_layout = QVBoxLayout()

        # Gazebo checkbox
        self.gazebo_checkbox = QCheckBox("Gazebo")
        self.gazebo_checkbox.setToolTip("Add Gazebo simulation support")
        engines_layout.addWidget(self.gazebo_checkbox)

        # Renode checkbox
        self.renode_checkbox = QCheckBox("Renode")
        self.renode_checkbox.setToolTip("Add Renode simulation support")
        engines_layout.addWidget(self.renode_checkbox)

        engines_group.setLayout(engines_layout)
        layout.addWidget(engines_group)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _accept_dialog(self) -> None:
        """Collect selected engines and accept."""
        self.selected_engines = []
        if self.gazebo_checkbox.isChecked():
            self.selected_engines.append("gazebo")
        if self.renode_checkbox.isChecked():
            self.selected_engines.append("renode")

        # At least one engine should be selected
        if not self.selected_engines:
            QMessageBox.warning(self, "No Selection", "Please select at least one simulation engine.")
            return

        self.accept()
