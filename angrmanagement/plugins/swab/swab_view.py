from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from angrmanagement.ui.views.view import InstanceView

if TYPE_CHECKING:
    from angrmanagement.data.instance import Instance
    from angrmanagement.ui.workspace import Workspace


class CreateProjectDialog(QDialog):
    """Dialog for creating a new project folder."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setMinimumWidth(500)

        self.project_name = None
        self.project_path = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Form layout for project details
        form_layout = QFormLayout()

        # Project name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("my_project")
        form_layout.addRow("Project Name:", self.name_input)

        # Project location input with browse button
        location_layout = QHBoxLayout()
        self.location_input = QLineEdit()
        self.location_input.setText(os.path.expanduser("~"))
        location_layout.addWidget(self.location_input)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_button)

        form_layout.addRow("Location:", location_layout)

        # Full path display
        self.full_path_label = QLabel()
        self.full_path_label.setStyleSheet("color: gray;")
        self._update_full_path()
        form_layout.addRow("Full Path:", self.full_path_label)

        layout.addLayout(form_layout)

        # Connect signals to update full path
        self.name_input.textChanged.connect(self._update_full_path)
        self.location_input.textChanged.connect(self._update_full_path)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _browse_location(self) -> None:
        """Open file dialog to select project location."""
        directory = QFileDialog.getExistingDirectory(self, "Select Project Location", self.location_input.text())
        if directory:
            self.location_input.setText(directory)

    def _update_full_path(self) -> None:
        """Update the full path label based on location and name."""
        import os
        location = self.location_input.text()
        name = self.name_input.text()
        if location and name:
            full_path = os.path.join(location, name)
            self.full_path_label.setText(full_path)
        else:
            self.full_path_label.setText("")

    def _accept_dialog(self) -> None:
        """Validate and accept the dialog."""

        name = self.name_input.text().strip()
        location = self.location_input.text().strip()

        if not name:
            # Show error - project name required
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", "Please enter a project name.")
            return

        if not location:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Invalid Input", "Please select a project location.")
            return

        self.project_name = name
        self.project_path = os.path.join(location, name)

        # Check if directory already exists
        if os.path.exists(self.project_path):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Directory Exists",
                f"The directory '{self.project_path}' already exists.\nPlease choose a different project name or location."
            )
            return

        self.accept()


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
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Selection", "Please select at least one simulation engine.")
            return

        self.accept()


class SWABView(InstanceView):
    """
    SWAB plugin view with two panels: left for non-editable text, right for editable code with run button.
    """

    def __init__(self, workspace: Workspace, default_docking_position: str, instance: Instance) -> None:
        super().__init__("swab", workspace, default_docking_position, instance)

        self.base_caption = "SWAB"
        self.current_file_path = None
        self.current_project_path = None  # Track current project directory
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
        self.left_panel.setPlaceholderText("Output will appear here...")
        self.left_panel.setText("Welcome to SWAB!\n\nWrite Python code in the right panel and click Run.")

        # Right panel container (IDE-like with file tree and code editor)
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Run button at the top right
        button_layout = QHBoxLayout()

        # Toggle button for file tree
        self.toggle_tree_button = QToolButton()
        self.toggle_tree_button.setText("≡")
        self.toggle_tree_button.setToolTip("Toggle file tree")
        self.toggle_tree_button.setCheckable(True)
        self.toggle_tree_button.setChecked(True)
        self.toggle_tree_button.clicked.connect(self._toggle_file_tree)
        button_layout.addWidget(self.toggle_tree_button)

        button_layout.addStretch()

        # Open button
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self._on_open_clicked)
        self.open_button.setToolTip("Open an existing project folder")
        button_layout.addWidget(self.open_button)

        # Create button
        self.create_button = QPushButton("Create")
        self.create_button.clicked.connect(self._on_create_clicked)
        button_layout.addWidget(self.create_button)

        # Configure button (initially disabled until project is created)
        self.configure_button = QPushButton("Configure")
        self.configure_button.clicked.connect(self._on_configure_clicked)
        self.configure_button.setEnabled(False)  # Disabled by default
        self.configure_button.setToolTip("Configure project (create a project first)")
        button_layout.addWidget(self.configure_button)

        # Save button (initially disabled until a file is opened)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)  # Disabled by default
        self.save_button.setToolTip("Save current file")
        button_layout.addWidget(self.save_button)

        # Run button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._on_run_clicked)
        button_layout.addWidget(self.run_button)
        right_layout.addLayout(button_layout)

        # Create IDE-like layout with file tree and code editor
        ide_splitter = QSplitter(Qt.Orientation.Horizontal)

        # File tree panel
        self.file_tree_container = QWidget()
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)

        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_tree.setModel(self.file_model)

        # Set root to user's home directory by default
        import os
        home_dir = os.path.expanduser("~")
        self.file_tree.setRootIndex(self.file_model.index(home_dir))

        # Hide unnecessary columns
        self.file_tree.setColumnHidden(1, True)  # Size
        self.file_tree.setColumnHidden(2, True)  # Type
        self.file_tree.setColumnHidden(3, True)  # Date Modified

        # Enable context menu
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Connect double-click to open file
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)

        tree_layout.addWidget(self.file_tree)
        self.file_tree_container.setLayout(tree_layout)

        # Code editor panel
        self.right_panel = CodeEdit()
        self.right_panel.use_spaces_instead_of_tabs = True
        self.right_panel.tab_length = 4

        # Add syntax highlighting for Python (before setting font)
        self.right_panel.modes.append(CaretLineHighlighterMode())
        self.right_panel.modes.append(PygmentsSyntaxHighlighter(self.right_panel.document()))
        self.right_panel.modes.append(AutoIndentMode())

        # Set word wrap mode
        self.right_panel.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        # Set initial Python code
        self.right_panel.setPlainText("# Enter your Python code here\nprint('Hello from SWAB!')", "text/x-python", "utf-8")

        # Set larger font for code editor AFTER setting text and modes
        # This ensures the font isn't overridden by other initialization
        code_font = QFont("Monospace", 14)
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        self.right_panel.setFont(code_font)

        # Also set the font size using the zoom functionality as backup
        self.right_panel.zoom_in(3)  # Increase zoom level

        # Add keyboard shortcut: Cmd+Enter (or Ctrl+Enter on non-Mac) to run code
        self.run_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.right_panel)
        self.run_shortcut.activated.connect(self._on_run_clicked)

        # Add keyboard shortcut: Cmd+S (or Ctrl+S on non-Mac) to save file
        self.save_shortcut = QShortcut(QKeySequence.StandardKey.Save, self.right_panel)
        self.save_shortcut.activated.connect(self._on_save_clicked)

        # Add file tree and code editor to IDE splitter
        ide_splitter.addWidget(self.file_tree_container)
        ide_splitter.addWidget(self.right_panel)
        ide_splitter.setSizes([200, 600])  # File tree smaller than editor

        right_layout.addWidget(ide_splitter)
        right_container.setLayout(right_layout)

        # Add panels to splitter
        splitter.addWidget(self.left_panel)
        splitter.addWidget(right_container)

        # Set initial sizes (50/50 split)
        splitter.setSizes([400, 400])

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def _toggle_file_tree(self) -> None:
        """Toggle the visibility of the file tree panel."""
        is_visible = self.file_tree_container.isVisible()
        self.file_tree_container.setVisible(not is_visible)

    def _on_tree_context_menu(self, position) -> None:
        """Handle right-click context menu on file tree."""
        index = self.file_tree.indexAt(position)

        # Get the file path of the clicked item
        if index.isValid():
            file_path = self.file_model.filePath(index)
            is_dir = self.file_model.isDir(index)
        else:
            # If no item clicked, use the root of the tree
            file_path = self.file_model.filePath(self.file_tree.rootIndex())
            is_dir = True

        # Create context menu
        menu = QMenu(self.file_tree)

        if is_dir:
            # If it's a directory, show "New File" and "New Folder" options
            new_file_action = menu.addAction("New File...")
            new_file_action.triggered.connect(lambda: self._create_new_file(file_path))

            new_folder_action = menu.addAction("New Folder...")
            new_folder_action.triggered.connect(lambda: self._create_new_folder(file_path))

        if index.isValid():
            # If an item is selected, show "Delete" option
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_item(file_path, is_dir))

        # Show the menu at the cursor position
        if not menu.isEmpty():
            menu.exec_(self.file_tree.viewport().mapToGlobal(position))

    def _create_new_file(self, parent_dir: str) -> None:
        """Create a new file in the specified directory."""
        # Ask user for filename
        filename, ok = QInputDialog.getText(
            self,
            "New File",
            f"Enter filename:\n(in {os.path.basename(parent_dir)})",
            QLineEdit.EchoMode.Normal,
            "newfile.py"
        )

        if not ok or not filename:
            return

        # Create the full file path
        file_path = os.path.join(parent_dir, filename)

        # Check if file already exists
        if os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "File Exists",
                f"A file or folder named '{filename}' already exists in this location."
            )
            return

        try:
            # Create the file with empty or template content
            with open(file_path, "w", encoding="utf-8") as f:
                if filename.endswith(".py"):
                    f.write("#!/usr/bin/env python3\n# New Python file\n\n")
                elif filename.endswith(".md"):
                    f.write(f"# {os.path.splitext(filename)[0]}\n\n")
                else:
                    f.write("")  # Empty file

            # Load the new file into the editor
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Detect file type for syntax highlighting
            mime_type = "text/plain"
            if filename.endswith(".py"):
                mime_type = "text/x-python"
            elif filename.endswith(".md"):
                mime_type = "text/markdown"
            elif filename.endswith((".c", ".h")):
                mime_type = "text/x-c"
            elif filename.endswith((".cpp", ".cc", ".cxx", ".hpp")):
                mime_type = "text/x-c++"
            elif filename.endswith(".js"):
                mime_type = "text/javascript"

            self.right_panel.setPlainText(content, mime_type, "utf-8")
            self.current_file_path = file_path
            self.save_button.setEnabled(True)

            # Update output panel
            self.left_panel.setText(
                f"New file created!\n\n"
                f"Name: {filename}\n"
                f"Location: {parent_dir}\n\n"
                f"The file has been loaded in the editor."
            )

        except Exception as e:
            QMessageBox.critical(self, "Error Creating File", f"Failed to create file:\n{e}")

    def _create_new_folder(self, parent_dir: str) -> None:
        """Create a new folder in the specified directory."""
        # Ask user for folder name
        foldername, ok = QInputDialog.getText(
            self,
            "New Folder",
            f"Enter folder name:\n(in {os.path.basename(parent_dir)})",
            QLineEdit.EchoMode.Normal,
            "new_folder"
        )

        if not ok or not foldername:
            return

        # Create the full folder path
        folder_path = os.path.join(parent_dir, foldername)

        # Check if folder already exists
        if os.path.exists(folder_path):
            QMessageBox.warning(
                self,
                "Folder Exists",
                f"A file or folder named '{foldername}' already exists in this location."
            )
            return

        try:
            # Create the folder
            os.makedirs(folder_path)

            # Update output panel
            self.left_panel.setText(
                f"New folder created!\n\n"
                f"Name: {foldername}\n"
                f"Location: {parent_dir}\n"
                f"Full path: {folder_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error Creating Folder", f"Failed to create folder:\n{e}")

    def _delete_item(self, item_path: str, is_dir: bool) -> None:
        """Delete a file or folder."""
        import shutil

        item_name = os.path.basename(item_path)
        item_type = "folder" if is_dir else "file"

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this {item_type}?\n\n{item_name}\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            if is_dir:
                # Delete directory and all contents
                shutil.rmtree(item_path)
            else:
                # Delete file
                os.remove(item_path)

            # If the deleted file was currently open, clear the editor
            if not is_dir and self.current_file_path == item_path:
                self.right_panel.setPlainText("", "text/plain", "utf-8")
                self.current_file_path = None
                self.save_button.setEnabled(False)

            # Update output panel
            self.left_panel.setText(
                f"{item_type.capitalize()} deleted successfully!\n\n"
                f"Name: {item_name}\n"
                f"Path: {item_path}"
            )

        except Exception as e:
            QMessageBox.critical(self, f"Error Deleting {item_type.capitalize()}", f"Failed to delete {item_type}:\n{e}")

    def _on_open_clicked(self) -> None:
        """Handle Open button click - open an existing project folder."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        # Open file dialog to select a folder
        project_path = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )

        if not project_path:
            return  # User cancelled

        try:
            # Check if the directory exists
            if not os.path.exists(project_path):
                QMessageBox.warning(self, "Invalid Path", "The selected directory does not exist.")
                return

            # Set this as the current project
            self.current_project_path = project_path
            project_name = os.path.basename(project_path)

            # Update file tree to show the project folder
            self.file_tree.setRootIndex(self.file_model.index(project_path))

            # Enable Configure button since we have a project open
            self.configure_button.setEnabled(True)
            self.configure_button.setToolTip("Configure project simulation engines")

            # Look for common entry point files to load
            entry_files = ["main.py", "app.py", "__main__.py", "README.md"]
            loaded_file = None

            for filename in entry_files:
                file_path = os.path.join(project_path, filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Detect file type for syntax highlighting
                        mime_type = "text/plain"
                        if file_path.endswith(".py"):
                            mime_type = "text/x-python"
                        elif file_path.endswith(".md"):
                            mime_type = "text/markdown"

                        self.right_panel.setPlainText(content, mime_type, "utf-8")
                        self.current_file_path = file_path
                        self.save_button.setEnabled(True)  # Enable Save button
                        loaded_file = filename
                        break
                    except Exception:
                        continue

            # Update output panel
            output = f"Project opened successfully!\n\n"
            output += f"Name: {project_name}\n"
            output += f"Location: {project_path}\n\n"

            if loaded_file:
                output += f"Loaded file: {loaded_file}\n\n"
            else:
                output += "No entry point file found (main.py, app.py, etc.)\n"
                output += "Double-click any file in the tree to open it.\n\n"

            # Check if project is configured
            config_path = os.path.join(project_path, "configuration.toml")
            if os.path.exists(config_path):
                output += "✓ Project is configured\n"
                # Parse configuration to show engines
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_content = f.read()
                        import re
                        engine_matches = re.findall(r'\[engines\.(\w+)\]', config_content)
                        if engine_matches:
                            output += f"Engines: {', '.join(engine_matches)}\n"
                except Exception:
                    pass
            else:
                output += "Click 'Configure' to add simulation engines.\n"

            self.left_panel.setText(output)

        except Exception as e:
            QMessageBox.critical(self, "Error Opening Project", f"Failed to open project:\n{e}")

    def _on_create_clicked(self) -> None:
        """Handle Create button click - show dialog to create new project."""
        dialog = CreateProjectDialog(self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:

            project_path = dialog.project_path
            project_name = dialog.project_name

            try:
                # Create the project directory if it doesn't exist
                if not os.path.exists(project_path):
                    os.makedirs(project_path)

                # Create a basic project structure
                # Create main.py with template code
                main_py_path = os.path.join(project_path, "main.py")
                if not os.path.exists(main_py_path):
                    with open(main_py_path, "w", encoding="utf-8") as f:
                        f.write(f'"""\n{project_name} - Main entry point\n"""\n\n')
                        f.write('def main():\n')
                        f.write('    print("Hello from {}!")\n\n'.format(project_name))
                        f.write('if __name__ == "__main__":\n')
                        f.write('    main()\n')

                # Create README.md
                readme_path = os.path.join(project_path, "README.md")
                if not os.path.exists(readme_path):
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(f"# {project_name}\n\n")
                        f.write("A Python project created with SWAB.\n")

                # Update file tree to show the new project
                self.file_tree.setRootIndex(self.file_model.index(project_path))

                # Load main.py into editor
                with open(main_py_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.right_panel.setPlainText(content, "text/x-python", "utf-8")
                self.current_file_path = main_py_path
                self.save_button.setEnabled(True)  # Enable Save button

                # Store the current project path and enable Configure button
                self.current_project_path = project_path
                self.configure_button.setEnabled(True)
                self.configure_button.setToolTip("Configure project simulation engines")

                # Update output panel
                self.left_panel.setText(
                    f"Project created successfully!\n\n"
                    f"Name: {project_name}\n"
                    f"Location: {project_path}\n\n"
                    f"Files created:\n"
                    f"  - main.py (loaded in editor)\n"
                    f"  - README.md\n\n"
                    f"Click 'Configure' to add simulation engines."
                )

            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error Creating Project", f"Failed to create project:\n{e}")

    def _on_configure_clicked(self) -> None:
        """Handle Configure button click - configure project with simulation engines."""
        if not self.current_project_path:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Project", "Please create a project first.")
            return

        import os
        from PySide6.QtWidgets import QMessageBox

        # Step 1: Show dialog to let user select engines
        dialog = ConfigureProjectDialog(self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return  # User cancelled

        selected_engines = dialog.selected_engines

        # Step 2: Check if project is already configured
        config_path = os.path.join(self.current_project_path, "configuration.toml")
        if os.path.exists(config_path):
            # Step 3: Check if user's current choice will override existing files
            files_to_override = []

            # Always list configuration.toml as it will be overridden
            files_to_override.append("configuration.toml")

            # Check if any of the selected engines already have folders
            for engine in selected_engines:
                engine_path = os.path.join(self.current_project_path, engine)
                if os.path.exists(engine_path):
                    files_to_override.append(f"{engine}/")

            # Only show warning if there are files that will be overridden
            if len(files_to_override) > 1 or files_to_override[0] == "configuration.toml":
                # Show warning dialog with list of files
                override_list = "\n".join(f"  • {file}" for file in files_to_override)
                message = (
                    "This project is already configured.\n\n"
                    "Reconfiguring will override the following files:\n\n"
                    f"{override_list}\n\n"
                    "Do you want to continue?"
                )

                reply = QMessageBox.question(
                    self,
                    "Reconfigure Project",
                    message,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No  # Default to No for safety
                )

                if reply == QMessageBox.StandardButton.No:
                    return

        # Step 4: Proceed with configuration
        try:
            # Create subfolders for selected engines
            created_folders = []
            for engine in selected_engines:
                engine_path = os.path.join(self.current_project_path, engine)
                if not os.path.exists(engine_path):
                    os.makedirs(engine_path)
                    created_folders.append(engine)

            # Create configuration.toml file
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("# Project Configuration\n\n")

                # Write engine configurations
                for engine in selected_engines:
                    f.write(f"[engines.{engine}]\n")
                    f.write('enabled = "true"\n\n')

            # Refresh file tree to show new folders
            self.file_tree.setRootIndex(self.file_model.index(self.current_project_path))

            # Update output panel
            output = "Project configured successfully!\n\n"
            output += "Simulation Engines:\n"
            for engine in selected_engines:
                output += f"  - {engine.capitalize()}\n"
            output += f"\nFolders created:\n"
            for folder in created_folders:
                output += f"  - {folder}/\n"
            output += f"\nConfiguration file: configuration.toml\n"

            self.left_panel.setText(output)

        except Exception as e:
            QMessageBox.critical(self, "Error Configuring Project", f"Failed to configure project:\n{e}")

    def _on_file_double_clicked(self, index) -> None:
        """Handle double-click on file in the tree - load file content into editor."""
        file_path = self.file_model.filePath(index)

        # Only load if it's a file, not a directory
        if not self.file_model.isDir(index):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Detect file type for syntax highlighting
                mime_type = "text/plain"
                if file_path.endswith(".py"):
                    mime_type = "text/x-python"
                elif file_path.endswith((".c", ".h")):
                    mime_type = "text/x-c"
                elif file_path.endswith((".cpp", ".cc", ".cxx", ".hpp")):
                    mime_type = "text/x-c++"
                elif file_path.endswith(".js"):
                    mime_type = "text/javascript"
                elif file_path.endswith(".md"):
                    mime_type = "text/markdown"

                self.right_panel.setPlainText(content, mime_type, "utf-8")
                self.current_file_path = file_path
                self.save_button.setEnabled(True)  # Enable Save button

                # Update welcome message
                self.left_panel.setText(f"File loaded: {file_path}\n\nClick Run to execute Python code.")

            except Exception as e:
                self.left_panel.setText(f"Error loading file: {e}\n\nFile: {file_path}")

    def _on_save_clicked(self) -> None:
        """Handle Save button click - save the current file."""
        from PySide6.QtWidgets import QMessageBox

        # Check if there's a file currently open
        if not self.current_file_path:
            QMessageBox.warning(self, "No File Open", "No file is currently open to save.")
            return

        try:
            # Get the content from the editor
            content = self.right_panel.toPlainText()

            # Write to file
            with open(self.current_file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Update output panel
            filename = os.path.basename(self.current_file_path)
            self.left_panel.setText(
                f"File saved successfully!\n\n"
                f"File: {filename}\n"
                f"Path: {self.current_file_path}\n\n"
                f"Last saved: {self._get_current_time()}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")

    def _get_current_time(self) -> str:
        """Get current time as a formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _on_run_clicked(self) -> None:
        """Handle run button click - execute the Python code from the right panel."""
        # Get the Python code from the right panel
        code = self.right_panel.toPlainText().strip()

        if not code:
            self.left_panel.setText("Error: No code entered")
            return

        try:
            # Execute the Python code using subprocess to capture output
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Display the output in the left panel
            output = f"Python Code Executed\n"
            output += f"{'=' * 60}\n"
            output += f"Return code: {result.returncode}\n\n"

            if result.stdout:
                output += f"Output:\n{result.stdout}"

            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"

            self.left_panel.setText(output)

        except subprocess.TimeoutExpired:
            self.left_panel.setText(f"Error: Code execution timed out after 10 seconds\n\nCode:\n{code}")
        except Exception as e:
            self.left_panel.setText(f"Error executing code: {e}\n\nCode:\n{code}")

    def reload(self) -> None:
        """Reload the view."""
        pass

    def refresh(self) -> None:
        """Refresh the view."""
        pass
