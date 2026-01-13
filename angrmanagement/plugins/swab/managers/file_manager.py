from __future__ import annotations

import shutil
from pathlib import Path


class FileManager:
    """Manages file and folder operations."""

    # MIME type mapping for syntax highlighting
    MIME_TYPE_MAP = {
        '.py': 'text/x-python',
        '.c': 'text/x-c',
        '.h': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.cc': 'text/x-c++',
        '.cxx': 'text/x-c++',
        '.hpp': 'text/x-c++',
        '.js': 'text/javascript',
        '.md': 'text/markdown',
        '.toml': 'text/x-toml',
        '.json': 'application/json',
        '.txt': 'text/plain',
    }

    @staticmethod
    def create_file(parent_dir: Path, filename: str) -> Path:
        """Create new file with template content.

        Args:
            parent_dir: Directory where file should be created
            filename: Name of the file to create

        Returns:
            Path to created file

        Raises:
            FileExistsError: If file already exists
            OSError: If file creation fails
        """
        file_path = parent_dir / filename

        if file_path.exists():
            raise FileExistsError(f"File '{filename}' already exists")

        # Create file with template content based on extension
        if filename.endswith(".py"):
            content = "#!/usr/bin/env python3\n# New Python file\n\n"
        elif filename.endswith(".md"):
            content = f"# {file_path.stem}\n\n"
        else:
            content = ""  # Empty file

        file_path.write_text(content, encoding='utf-8')
        return file_path

    @staticmethod
    def create_folder(parent_dir: Path, foldername: str) -> Path:
        """Create new folder.

        Args:
            parent_dir: Directory where folder should be created
            foldername: Name of the folder to create

        Returns:
            Path to created folder

        Raises:
            FileExistsError: If folder already exists
            OSError: If folder creation fails
        """
        folder_path = parent_dir / foldername

        if folder_path.exists():
            raise FileExistsError(f"Folder '{foldername}' already exists")

        folder_path.mkdir(parents=True)
        return folder_path

    @staticmethod
    def delete_item(path: Path) -> None:
        """Delete file or folder.

        Args:
            path: Path to file or folder to delete

        Raises:
            FileNotFoundError: If path doesn't exist
            OSError: If deletion fails
        """
        if not path.exists():
            raise FileNotFoundError(f"Path '{path}' does not exist")

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    @staticmethod
    def read_file(path: Path) -> str:
        """Read file content.

        Args:
            path: Path to file

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
            OSError: If file read fails
        """
        return path.read_text(encoding='utf-8')

    @staticmethod
    def write_file(path: Path, content: str) -> None:
        """Write content to file.

        Args:
            path: Path to file
            content: Content to write

        Raises:
            OSError: If file write fails
        """
        path.write_text(content, encoding='utf-8')

    @staticmethod
    def detect_mime_type(filename: str) -> str:
        """Detect MIME type for syntax highlighting.

        Args:
            filename: Name of the file (or full path)

        Returns:
            MIME type string for syntax highlighting
        """
        path = Path(filename)
        return FileManager.MIME_TYPE_MAP.get(path.suffix, 'text/plain')
