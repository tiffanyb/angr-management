from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        import os
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
        import os

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
            reply = QMessageBox.question(
                self,
                "Directory Exists",
                f"The directory '{self.project_path}' already exists. Use it anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
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

        # Create button
        self.create_button = QPushButton("Create")
        self.create_button.clicked.connect(self._on_create_clicked)
        button_layout.addWidget(self.create_button)

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

    def _on_create_clicked(self) -> None:
        """Handle Create button click - show dialog to create new project."""
        dialog = CreateProjectDialog(self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            import os

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

                # Update output panel
                self.left_panel.setText(
                    f"Project created successfully!\n\n"
                    f"Name: {project_name}\n"
                    f"Location: {project_path}\n\n"
                    f"Files created:\n"
                    f"  - main.py (loaded in editor)\n"
                    f"  - README.md\n"
                )

            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error Creating Project", f"Failed to create project:\n{e}")

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

                self.right_panel.setPlainText(content, mime_type, "utf-8")
                self.current_file_path = file_path

                # Update welcome message
                self.left_panel.setText(f"File loaded: {file_path}\n\nClick Run to execute Python code.")

            except Exception as e:
                self.left_panel.setText(f"Error loading file: {e}\n\nFile: {file_path}")

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
