from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from angrmanagement.ui.views.view import InstanceView

if TYPE_CHECKING:
    from angrmanagement.data.instance import Instance
    from angrmanagement.ui.workspace import Workspace


class SWABView(InstanceView):
    """
    SWAB plugin view with two panels: left for non-editable text, right for editable code with run button.
    """

    def __init__(self, workspace: Workspace, default_docking_position: str, instance: Instance) -> None:
        super().__init__("swab", workspace, default_docking_position, instance)

        self.base_caption = "SWAB"
        self._init_widgets()

    def _init_widgets(self) -> None:
        """Initialize the UI widgets."""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - non-editable text
        self.left_panel = QTextEdit()
        self.left_panel.setReadOnly(True)
        self.left_panel.setPlaceholderText("Non-editable text panel")
        self.left_panel.setText("Welcome to SWAB!\n\nThis panel displays output and information.")

        # Right panel container
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Run button at the top right
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._on_run_clicked)
        button_layout.addWidget(self.run_button)
        right_layout.addLayout(button_layout)

        # Right panel - editable code area
        self.right_panel = QTextEdit()
        self.right_panel.setPlaceholderText("Write your code here...")
        self.right_panel.setText("# Enter your code here\necho 1")
        right_layout.addWidget(self.right_panel)

        right_container.setLayout(right_layout)

        # Add panels to splitter
        splitter.addWidget(self.left_panel)
        splitter.addWidget(right_container)

        # Set initial sizes (50/50 split)
        splitter.setSizes([400, 400])

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def _on_run_clicked(self) -> None:
        """Handle run button click - execute the command from the right panel."""
        # Get the code/command from the right panel
        code = self.right_panel.toPlainText().strip()

        if not code:
            self.left_panel.setText("Error: No command entered")
            return

        try:
            # Execute the command using shell to support complex commands
            result = subprocess.run(
                code,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Display the output in the left panel
            output = f"Command executed: {code}\n"
            output += f"{'=' * 60}\n"
            output += f"Return code: {result.returncode}\n\n"

            if result.stdout:
                output += f"Output:\n{result.stdout}"

            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"

            self.left_panel.setText(output)

        except subprocess.TimeoutExpired:
            self.left_panel.setText(f"Error: Command timed out after 10 seconds\n\nCommand: {code}")
        except Exception as e:
            self.left_panel.setText(f"Error executing command: {e}\n\nCommand: {code}")

    def reload(self) -> None:
        """Reload the view."""
        pass

    def refresh(self) -> None:
        """Refresh the view."""
        pass
