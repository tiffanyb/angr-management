from __future__ import annotations

import os
import re
from pathlib import Path


class ProjectManager:
    """Manages project creation, opening, and configuration."""

    def __init__(self) -> None:
        """Initialize project manager."""
        self.current_project_path: Path | None = None

    def create_project(self, path: Path, name: str) -> None:
        """Create new project with default structure.

        Args:
            path: Full path where project should be created
            name: Project name

        Raises:
            FileExistsError: If project directory already exists
            OSError: If directory creation fails
        """
        if path.exists():
            raise FileExistsError(f"Directory '{path}' already exists")

        # Create project directory
        path.mkdir(parents=True, exist_ok=False)

        # Create main.py with template code
        main_py = path / "main.py"
        main_py.write_text(
            f'"""\n{name} - Main entry point\n"""\n\n'
            'def main():\n'
            f'    print("Hello from {name}!")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n',
            encoding='utf-8'
        )

        # Create README.md
        readme = path / "README.md"
        readme.write_text(
            f"# {name}\n\n"
            "A Python project created with SWAB.\n",
            encoding='utf-8'
        )

        self.current_project_path = path

    def open_project(self, path: Path) -> dict[str, any]:
        """Open existing project and return metadata.

        Args:
            path: Path to project directory

        Returns:
            Dictionary with project metadata:
            - name: Project name
            - path: Full path
            - entry_file: Path to entry file if found
            - is_configured: Whether project has configuration.toml
            - engines: List of configured engines

        Raises:
            FileNotFoundError: If project path doesn't exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Project directory '{path}' does not exist")

        self.current_project_path = path
        name = path.name

        # Look for entry point file
        entry_files = ["main.py", "app.py", "__main__.py", "README.md"]
        entry_file = None

        for filename in entry_files:
            file_path = path / filename
            if file_path.exists():
                entry_file = file_path
                break

        # Check if project is configured
        config_path = path / "configuration.toml"
        is_configured = config_path.exists()

        # Parse engines from configuration
        engines = []
        if is_configured:
            try:
                config_content = config_path.read_text(encoding='utf-8')
                engine_matches = re.findall(r'\[engines\.(\w+)\]', config_content)
                engines = engine_matches
            except Exception:
                pass

        return {
            'name': name,
            'path': path,
            'entry_file': entry_file,
            'is_configured': is_configured,
            'engines': engines,
        }

    def configure_project(self, engines: list[str]) -> dict[str, any]:
        """Add simulation engines to project.

        Creates engine subdirectories and configuration files.

        Args:
            engines: List of engine names (e.g., ['gazebo', 'renode'])

        Returns:
            Dictionary with:
            - created_folders: List of newly created engine folders
            - config_path: Path to configuration.toml

        Raises:
            ValueError: If no project is currently open
            OSError: If directory/file creation fails
        """
        if not self.current_project_path:
            raise ValueError("No project is currently open")

        created_folders = []

        # Create subfolders for selected engines
        for engine in engines:
            engine_path = self.current_project_path / engine
            if not engine_path.exists():
                engine_path.mkdir(parents=True)
                created_folders.append(engine)

            # Create engine.toml file in the engine folder
            engine_toml = engine_path / "engine.toml"
            engine_toml.write_text(
                "[engine]\n"
                'base = ""\n',
                encoding='utf-8'
            )

        # Create configuration.toml file
        config_path = self.current_project_path / "configuration.toml"
        config_content = "# Project Configuration\n\n"

        for engine in engines:
            config_content += f"[engines.{engine}]\n"
            config_content += 'enabled = "true"\n\n'

        config_path.write_text(config_content, encoding='utf-8')

        return {
            'created_folders': created_folders,
            'config_path': config_path,
        }

    def is_configured(self) -> bool:
        """Check if current project is configured.

        Returns:
            True if configuration.toml exists, False otherwise
        """
        if not self.current_project_path:
            return False
        return (self.current_project_path / "configuration.toml").exists()

    def get_entry_file(self) -> Path | None:
        """Find and return entry point file.

        Returns:
            Path to entry file if found, None otherwise
        """
        if not self.current_project_path:
            return None

        entry_files = ["main.py", "app.py", "__main__.py", "README.md"]

        for filename in entry_files:
            file_path = self.current_project_path / filename
            if file_path.exists():
                return file_path

        return None
