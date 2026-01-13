from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...managers import ProjectManager
from ..dialogs import ConfigureProjectDialog, CreateProjectDialog

if TYPE_CHECKING:
    from ..swab_view import SWABView


class ProjectHandler:
    """Handles project operations for SWAB view.

    Responsibilities:
    - Opening existing projects
    - Creating new projects
    - Configuring projects with engines
    - Managing project state
    """

    def __init__(self, view: SWABView) -> None:
        """Initialize project handler.

        Args:
            view: Parent SWAB view
        """
        self.view = view
        self.project_manager = ProjectManager()

    def open_project(self) -> bool:
        """Open an existing project folder.

        Returns:
            True if project opened successfully, False otherwise
        """
        project_path = QFileDialog.getExistingDirectory(
            self.view, "Open Project Folder", os.path.expanduser("~"), QFileDialog.Option.ShowDirsOnly
        )

        if not project_path:
            return False

        try:
            metadata = self.project_manager.open_project(Path(project_path))

            # Update file tree
            self.view.file_tree.setRootIndex(self.view.file_model.index(str(metadata["path"])))
            self.view.file_tree.setVisible(True)
            self.view.file_tree_placeholder.setVisible(False)

            # Enable configure button
            self.view.configure_button.setEnabled(True)
            self.view.configure_button.setToolTip("Configure project simulation engines")

            # Load entry file if found
            if metadata["entry_file"]:
                self.view.file_handler.load_file_in_editor(metadata["entry_file"])

            # Update console
            output = "Project opened successfully!\n\n"
            output += f"Name: {metadata['name']}\n"
            output += f"Location: {metadata['path']}\n\n"

            if metadata["entry_file"]:
                output += f"Loaded file: {metadata['entry_file'].name}\n\n"
            else:
                output += "No entry point file found (main.py, app.py, etc.)\n"
                output += "Double-click any file in the tree to open it.\n\n"

            if metadata["is_configured"]:
                output += "✓ Project is configured\n"
                if metadata["engines"]:
                    output += f"Engines: {', '.join(metadata['engines'])}\n"
            else:
                output += "Click 'Configure' to add simulation engines.\n"

            self.view.left_panel.setText(output)
            return True

        except Exception as e:
            QMessageBox.critical(self.view, "Error Opening Project", f"Failed to open project:\n{e}")
            return False

    def create_project(self) -> bool:
        """Create a new project.

        Returns:
            True if project created successfully, False otherwise
        """
        dialog = CreateProjectDialog(self.view)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return False

        try:
            project_path = Path(dialog.project_path)
            project_name = dialog.project_name

            self.project_manager.create_project(project_path, project_name)

            # Update file tree
            self.view.file_tree.setRootIndex(self.view.file_model.index(str(project_path)))
            self.view.file_tree.setVisible(True)
            self.view.file_tree_placeholder.setVisible(False)

            # Enable configure button
            self.view.configure_button.setEnabled(True)
            self.view.configure_button.setToolTip("Configure project simulation engines")

            # Load main.py into editor
            main_py = project_path / "main.py"
            if main_py.exists():
                self.view.file_handler.load_file_in_editor(main_py)

            # Update console
            self.view.left_panel.setText(
                f"Project created successfully!\n\n"
                f"Name: {project_name}\n"
                f"Location: {project_path}\n\n"
                f"Files created:\n"
                f"  - main.py (loaded in editor)\n"
                f"  - README.md\n\n"
                f"Click 'Configure' to add simulation engines."
            )
            return True

        except Exception as e:
            QMessageBox.critical(self.view, "Error Creating Project", f"Failed to create project:\n{e}")
            return False

    def configure_project(self) -> bool:
        """Configure project with simulation engines.

        Returns:
            True if project configured successfully, False otherwise
        """
        if not self.project_manager.current_project_path:
            QMessageBox.warning(self.view, "No Project", "Please create a project first.")
            return False

        # Check if reconfiguring
        if self.project_manager.is_configured():
            reply = QMessageBox.question(
                self.view,
                "Reconfigure Project",
                "This project is already configured.\n\n"
                "Reconfiguring will override configuration.toml.\n\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return False

        # Show dialog to select engines
        dialog = ConfigureProjectDialog(self.view)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return False

        try:
            result = self.project_manager.configure_project(dialog.selected_engines)

            # Refresh file tree
            self.view.file_tree.setRootIndex(self.view.file_model.index(str(self.project_manager.current_project_path)))

            # Update console
            output = "Project configured successfully!\n\n"
            output += "Simulation Engines:\n"
            for engine in dialog.selected_engines:
                output += f"  - {engine.capitalize()}\n"
            if result["created_folders"]:
                output += "\nFolders created:\n"
                for folder in result["created_folders"]:
                    output += f"  - {folder}/\n"
            output += "\nConfiguration file: configuration.toml\n"

            self.view.left_panel.setText(output)
            return True

        except Exception as e:
            QMessageBox.critical(self.view, "Error Configuring Project", f"Failed to configure project:\n{e}")
            return False

    @property
    def current_project_path(self) -> Path | None:
        """Get the current project path.

        Returns:
            Current project path or None
        """
        return self.project_manager.current_project_path
