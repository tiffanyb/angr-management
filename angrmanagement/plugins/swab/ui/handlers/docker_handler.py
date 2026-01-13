from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QDialog, QMessageBox

from ...managers import DockerManager
from ...utils import WarningParser
from ..dialogs import DockerRunDialog

if TYPE_CHECKING:
    from pathlib import Path

    from ..swab_view import SWABView


class DockerHandler:
    """Handles Docker operations for SWAB view.

    Responsibilities:
    - Running Docker containers
    - Killing Docker processes
    - Managing Docker images
    - Processing Docker output
    - Extracting warnings from output
    """

    def __init__(self, view: SWABView) -> None:
        """Initialize Docker handler.

        Args:
            view: Parent SWAB view
        """
        self.view = view
        self.docker_manager = DockerManager(parent=view)

    def refresh_images(self) -> None:
        """Refresh the docker images dropdown."""
        images = self.docker_manager.get_images()

        self.view.docker_image_dropdown.clear()
        if images:
            self.view.docker_image_dropdown.addItems(images)
        else:
            self.view.docker_image_dropdown.addItem("No images found")

    def run(self, selected_image: str, project_path: Path) -> bool:
        """Start Docker container with selected image.

        Args:
            selected_image: Docker image name
            project_path: Project directory to mount

        Returns:
            True if Docker process started successfully, False otherwise
        """
        # Validate Docker availability
        if not selected_image or selected_image == "No images found":
            QMessageBox.warning(
                self.view,
                "Docker Not Available",
                "Docker is not available or no images found.\n\n"
                "Please ensure Docker is installed and running, then click the refresh button.",
            )
            return False

        # Check if already running
        if self.docker_manager.is_running():
            QMessageBox.warning(
                self.view, "Process Running", "A Docker process is already running. Please wait for it to complete."
            )
            return False

        # Show dialog to get command and container path
        dialog = DockerRunDialog(selected_image, self.view)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return False

        command = dialog.command
        container_path = dialog.container_path

        # Initialize console output
        self.view.left_panel.setText(
            f"Docker Run Started\n{'=' * 60}\n"
            f"Image: {selected_image}\n"
            f"Command: {command}\n"
            f"Project: {project_path}\n"
            f"Mounted at: {container_path}\n\n"
            f"--- Output ---\n"
        )

        # Start Docker process
        success = self.docker_manager.run(
            image=selected_image,
            command=command,
            project_path=str(project_path),
            container_path=container_path,
            stdout_callback=self._on_stdout,
            stderr_callback=self._on_stderr,
            finished_callback=self._on_finished,
            error_callback=self._on_error,
        )

        if success:
            self.view.kill_button.setEnabled(True)
            self.view.run_button.setEnabled(False)

        return success

    def kill(self) -> bool:
        """Kill the running Docker process.

        Returns:
            True if kill command was sent, False otherwise
        """
        if self.docker_manager.kill():
            current_text = self.view.left_panel.toPlainText()
            self.view.left_panel.setText(current_text + "\n\n[KILL] Terminating Docker container...\n")
            self._scroll_console_to_bottom()
            self.view.kill_button.setEnabled(False)
            self.view.run_button.setEnabled(True)
            return True
        return False

    def _on_stdout(self, data: str) -> None:
        """Handle stdout from docker process.

        Args:
            data: Output data from Docker
        """
        current_text = self.view.left_panel.toPlainText()
        self.view.left_panel.setText(current_text + data)
        self._scroll_console_to_bottom()

    def _on_stderr(self, data: str) -> None:
        """Handle stderr from docker process.

        Args:
            data: Error data from Docker
        """
        current_text = self.view.left_panel.toPlainText()
        self.view.left_panel.setText(current_text + f"[STDERR] {data}")
        self._scroll_console_to_bottom()

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle docker process completion.

        Args:
            exit_code: Process exit code
            exit_status: Process exit status
        """
        current_text = self.view.left_panel.toPlainText()
        completion_msg = f"\n\n{'=' * 60}\nDocker Run Completed\nExit Code: {exit_code}\n"

        # Extract warnings from console output
        self.view.warnings = WarningParser.parse(current_text)
        if self.view.warnings:
            completion_msg += f"Found {len(self.view.warnings)} warning(s)\n"

            # Refresh disassembly view to show warning annotations
            disasm_view = self.view.workspace.view_manager.first_view_in_category("disassembly")
            if disasm_view:
                disasm_view.refresh()

        self.view.left_panel.setText(current_text + completion_msg)
        self._scroll_console_to_bottom()

        # Re-enable buttons
        self.view.kill_button.setEnabled(False)
        self.view.run_button.setEnabled(True)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle docker process errors.

        Args:
            error: Process error type
        """
        current_text = self.view.left_panel.toPlainText()
        self.view.left_panel.setText(current_text + f"\n\n[ERROR] Docker process error: {error}\n")
        self._scroll_console_to_bottom()

    def _scroll_console_to_bottom(self) -> None:
        """Scroll console to bottom."""
        scrollbar = self.view.left_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
