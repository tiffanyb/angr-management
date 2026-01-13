from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFileSystemModel, QMessageBox, QPushButton, QToolButton, QTreeView, QWidget
from pyqodeng.core.api import CodeEdit

from angrmanagement.ui.views.view import InstanceView

from ..models import Warning
from .builders import UIBuilder
from .console_widget import ConsoleTextEdit
from .handlers import DockerHandler, FileHandler, ProjectHandler

if TYPE_CHECKING:
    from angrmanagement.data.instance import Instance
    from angrmanagement.ui.workspace import Workspace


class SWABView(InstanceView):
    """SWAB plugin coordinator view.

    This view coordinates between handlers for different operations:
    - DockerHandler: Docker container execution and output management
    - ProjectHandler: Project lifecycle and configuration
    - FileHandler: File operations and editor management

    The UI is built by UIBuilder to separate construction logic from business logic.
    """

    def __init__(self, workspace: Workspace, default_docking_position: str, instance: Instance) -> None:
        super().__init__("swab", workspace, default_docking_position, instance)

        self.base_caption = "SWAB"

        # Data
        self.warnings: list[Warning] = []

        # Handlers (initialized before UI so UI can reference them)
        self.docker_handler: DockerHandler | None = None
        self.project_handler: ProjectHandler | None = None
        self.file_handler: FileHandler | None = None

        # UI Components (initialized by UIBuilder)
        self.left_panel: ConsoleTextEdit = None
        self.right_panel: CodeEdit = None
        self.file_tree: QTreeView = None
        self.file_model: QFileSystemModel = None
        self.file_tree_container: QWidget = None
        self.file_tree_placeholder: QWidget = None

        # Buttons
        self.run_button: QPushButton = None
        self.kill_button: QPushButton = None
        self.save_button: QPushButton = None
        self.configure_button: QPushButton = None
        self.open_button: QPushButton = None
        self.create_button: QPushButton = None
        self.refresh_docker_button: QPushButton = None
        self.toggle_tree_button: QToolButton = None
        self.docker_image_dropdown: QComboBox = None

        # Initialize handlers first (so UI callbacks can reference them)
        self._init_handlers()

        # Build UI
        self._init_widgets()

    def _init_handlers(self) -> None:
        """Initialize operation handlers."""
        self.docker_handler = DockerHandler(self)
        self.project_handler = ProjectHandler(self)
        self.file_handler = FileHandler(self)

    def _init_widgets(self) -> None:
        """Initialize the UI widgets using UIBuilder."""
        main_layout = UIBuilder.build_main_layout(self)
        self.setLayout(main_layout)

        # Load docker images initially
        self.docker_handler.refresh_images()

    # ==================== Event Handlers ====================
    # These methods delegate to the appropriate handlers

    def _on_run_clicked(self) -> None:
        """Handle run button click - delegate to Docker handler."""
        selected_image = self.docker_image_dropdown.currentText()
        project_path = self.project_handler.current_project_path

        if not project_path:
            QMessageBox.warning(
                self,
                "No Project Open",
                "Please open or create a project first.\n\n"
                "The project directory will be mounted to the Docker container.",
            )
            return

        self.docker_handler.run(selected_image, project_path)

    def _on_kill_clicked(self) -> None:
        """Handle kill button click - delegate to Docker handler."""
        self.docker_handler.kill()

    def _on_refresh_docker_clicked(self) -> None:
        """Handle refresh docker images button click."""
        self.docker_handler.refresh_images()

    def _on_open_clicked(self) -> None:
        """Handle Open button click - delegate to Project handler."""
        self.project_handler.open_project()

    def _on_create_clicked(self) -> None:
        """Handle Create button click - delegate to Project handler."""
        self.project_handler.create_project()

    def _on_configure_clicked(self) -> None:
        """Handle Configure button click - delegate to Project handler."""
        self.project_handler.configure_project()

    def _on_save_clicked(self) -> None:
        """Handle Save button click - delegate to File handler."""
        self.file_handler.save_current_file()

    def _on_debug_to_line(self, line_text: str, address: str) -> None:
        """Handle 'Debug to this line' context menu action from console.

        Called when user right-clicks on a WARNING line in the console output
        and selects "Debug to this line".

        Args:
            line_text: Full WARNING line text
            address: Extracted address from WARNING line
        """
        current_text = self.left_panel.toPlainText()
        debug_msg = f"\n\n[DEBUG] Debug to line: {line_text}\n[DEBUG] Address: {address}\n"
        self.left_panel.setText(current_text + debug_msg)

        # Scroll to bottom to show the debug message
        scrollbar = self.left_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ==================== View Interface Methods ====================

    def reload(self) -> None:
        """Reload the view."""
        pass

    def refresh(self) -> None:
        """Refresh the view."""
        pass
