from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QInputDialog, QLineEdit, QMenu, QMessageBox

from ...managers import FileManager

if TYPE_CHECKING:
    from ..swab_view import SWABView


class FileHandler:
    """Handles file operations for SWAB view.

    Responsibilities:
    - File tree management
    - File CRUD operations
    - Loading files into editor
    - Saving files from editor
    """

    def __init__(self, view: SWABView) -> None:
        """Initialize file handler.

        Args:
            view: Parent SWAB view
        """
        self.view = view
        self.file_manager = FileManager()
        self.current_file_path: Path | None = None

    def toggle_file_tree(self) -> None:
        """Toggle the visibility of the file tree panel."""
        is_visible = self.view.file_tree_container.isVisible()
        self.view.file_tree_container.setVisible(not is_visible)

    def on_file_double_clicked(self, index) -> None:
        """Handle double-click on file in the tree - load file content into editor.

        Args:
            index: QModelIndex of clicked file
        """
        file_path = Path(self.view.file_model.filePath(index))

        if not self.view.file_model.isDir(index):
            try:
                self.load_file_in_editor(file_path)
            except Exception as e:
                self.view.left_panel.setText(f"Error loading file: {e}\n\nFile: {file_path}")

    def load_file_in_editor(self, file_path: Path) -> None:
        """Load file content into editor.

        Args:
            file_path: Path to file to load
        """
        content = self.file_manager.read_file(file_path)
        mime_type = self.file_manager.detect_mime_type(file_path.name)

        self.view.right_panel.setPlainText(content, mime_type, "utf-8")
        self.current_file_path = file_path
        self.view.save_button.setEnabled(True)

    def save_current_file(self) -> bool:
        """Save the current file.

        Returns:
            True if file saved successfully, False otherwise
        """
        if not self.current_file_path:
            QMessageBox.warning(self.view, "No File Open", "No file is currently open to save.")
            return False

        try:
            content = self.view.right_panel.toPlainText()
            self.file_manager.write_file(self.current_file_path, content)
            return True
        except Exception as e:
            QMessageBox.critical(self.view, "Error Saving File", f"Failed to save file:\n{e}")
            return False

    def show_tree_context_menu(self, position) -> None:
        """Handle right-click context menu on file tree.

        Args:
            position: Position where context menu was requested
        """
        index = self.view.file_tree.indexAt(position)

        if index.isValid():
            file_path = Path(self.view.file_model.filePath(index))
            is_dir = self.view.file_model.isDir(index)
        else:
            file_path = Path(self.view.file_model.filePath(self.view.file_tree.rootIndex()))
            is_dir = True

        menu = QMenu(self.view.file_tree)

        if is_dir:
            new_file_action = menu.addAction("New File...")
            new_file_action.triggered.connect(lambda: self.create_new_file(file_path))

            new_folder_action = menu.addAction("New Folder...")
            new_folder_action.triggered.connect(lambda: self.create_new_folder(file_path))

        if index.isValid():
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_item(file_path, is_dir))

        if not menu.isEmpty():
            menu.exec_(self.view.file_tree.viewport().mapToGlobal(position))

    def create_new_file(self, parent_dir: Path) -> bool:
        """Create a new file in the specified directory.

        Args:
            parent_dir: Directory where file should be created

        Returns:
            True if file created successfully, False otherwise
        """
        filename, ok = QInputDialog.getText(
            self.view,
            "New File",
            f"Enter filename:\n(in {parent_dir.name})",
            QLineEdit.EchoMode.Normal,
            "newfile.py",
        )

        if not ok or not filename:
            return False

        try:
            file_path = self.file_manager.create_file(parent_dir, filename)
            self.load_file_in_editor(file_path)
            return True
        except FileExistsError:
            QMessageBox.warning(self.view, "File Exists", f"A file named '{filename}' already exists in this location.")
            return False
        except Exception as e:
            QMessageBox.critical(self.view, "Error Creating File", f"Failed to create file:\n{e}")
            return False

    def create_new_folder(self, parent_dir: Path) -> bool:
        """Create a new folder in the specified directory.

        Args:
            parent_dir: Directory where folder should be created

        Returns:
            True if folder created successfully, False otherwise
        """
        foldername, ok = QInputDialog.getText(
            self.view,
            "New Folder",
            f"Enter folder name:\n(in {parent_dir.name})",
            QLineEdit.EchoMode.Normal,
            "new_folder",
        )

        if not ok or not foldername:
            return False

        try:
            self.file_manager.create_folder(parent_dir, foldername)
            return True
        except FileExistsError:
            QMessageBox.warning(
                self.view, "Folder Exists", f"A folder named '{foldername}' already exists in this location."
            )
            return False
        except Exception as e:
            QMessageBox.critical(self.view, "Error Creating Folder", f"Failed to create folder:\n{e}")
            return False

    def delete_item(self, item_path: Path, is_dir: bool) -> bool:
        """Delete a file or folder.

        Args:
            item_path: Path to item to delete
            is_dir: Whether item is a directory

        Returns:
            True if item deleted successfully, False otherwise
        """
        item_type = "folder" if is_dir else "file"

        reply = QMessageBox.question(
            self.view,
            "Confirm Delete",
            f"Are you sure you want to delete this {item_type}?\n\n{item_path.name}\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.No:
            return False

        try:
            self.file_manager.delete_item(item_path)

            # Clear editor if deleted file was currently open
            if not is_dir and self.current_file_path == item_path:
                self.view.right_panel.setPlainText("", "text/plain", "utf-8")
                self.current_file_path = None
                self.view.save_button.setEnabled(False)

            return True
        except Exception as e:
            QMessageBox.critical(
                self.view, f"Error Deleting {item_type.capitalize()}", f"Failed to delete {item_type}:\n{e}"
            )
            return False
