from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QProcess

if TYPE_CHECKING:
    from PySide6.QtCore import QObject


class DockerManager:
    """Manages Docker operations for SWAB plugin."""

    def __init__(self, parent: QObject | None = None) -> None:
        """Initialize Docker manager.

        Args:
            parent: Parent QObject for QProcess
        """
        self.parent = parent
        self.process: QProcess | None = None
        self._stdout_callback: Callable[[str], None] | None = None
        self._stderr_callback: Callable[[str], None] | None = None
        self._finished_callback: Callable[[int, QProcess.ExitStatus], None] | None = None
        self._error_callback: Callable[[QProcess.ProcessError], None] | None = None

    def get_images(self) -> list[str]:
        """Get list of available Docker images.

        Returns:
            List of Docker image names in format 'repository:tag'
            Empty list if Docker is not available
        """
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse the output to get image names
                images = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
                return images
            return []

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return []

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running.

        Returns:
            True if Docker is available, False otherwise
        """
        return len(self.get_images()) > 0

    def run(
        self,
        image: str,
        command: str,
        project_path: str,
        container_path: str,
        stdout_callback: Callable[[str], None] | None = None,
        stderr_callback: Callable[[str], None] | None = None,
        finished_callback: Callable[[int, QProcess.ExitStatus], None] | None = None,
        error_callback: Callable[[QProcess.ProcessError], None] | None = None,
    ) -> bool:
        """Run Docker container with volume mount.

        Args:
            image: Docker image name
            command: Command to run in container
            project_path: Host project path to mount
            container_path: Container path where project will be mounted
            stdout_callback: Callback for stdout data
            stderr_callback: Callback for stderr data
            finished_callback: Callback when process finishes
            error_callback: Callback for process errors

        Returns:
            True if process started successfully, False otherwise
        """
        # Check if a process is already running
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            return False

        # Store callbacks
        self._stdout_callback = stdout_callback
        self._stderr_callback = stderr_callback
        self._finished_callback = finished_callback
        self._error_callback = error_callback

        # Create QProcess
        self.process = QProcess(self.parent)

        # Connect signals
        if stdout_callback:
            self.process.readyReadStandardOutput.connect(self._on_stdout)
        if stderr_callback:
            self.process.readyReadStandardError.connect(self._on_stderr)
        if finished_callback:
            self.process.finished.connect(self._on_finished)
        if error_callback:
            self.process.errorOccurred.connect(self._on_error)

        # Store metadata in process
        self.process.setProperty("selected_image", image)
        self.process.setProperty("command", command)

        # Build docker run arguments
        # Using -i (interactive), --rm (remove after exit), and -v (volume mount) flags
        args = [
            "run",
            "-i",
            "--rm",
            "-v", f"{project_path}:{container_path}",
            image
        ] + command.split()

        # Start the process
        self.process.start("docker", args)
        return True

    def kill(self) -> bool:
        """Kill the running Docker process.

        Returns:
            True if process was killed, False if no process running
        """
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()
            return True
        return False

    def is_running(self) -> bool:
        """Check if Docker process is currently running.

        Returns:
            True if process is running, False otherwise
        """
        return self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning

    def _on_stdout(self) -> None:
        """Handle stdout from docker process."""
        if self.process and self._stdout_callback:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if data:
                self._stdout_callback(data)

    def _on_stderr(self) -> None:
        """Handle stderr from docker process."""
        if self.process and self._stderr_callback:
            data = self.process.readAllStandardError().data().decode('utf-8', errors='replace')
            if data:
                self._stderr_callback(data)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle docker process completion."""
        if self._finished_callback:
            self._finished_callback(exit_code, exit_status)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle docker process errors."""
        if self._error_callback:
            self._error_callback(error)
