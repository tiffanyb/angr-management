from __future__ import annotations

import os
import re
import subprocess
from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from pyqodeng.core.panels import LineNumberPanel
from PySide6.QtCore import Qt, QProcess, QPoint
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption, QTextCursor, QTextCharFormat
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileSystemModel,
    QFormLayout,
    QGraphicsEllipseItem,
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


class ConsoleTextEdit(QTextEdit):
    """
    Custom QTextEdit for console output with interactive WARNING lines.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMouseTracking(True)
        self._hovered_block = None
        self._parent_view = None

    def set_parent_view(self, view):
        """Set reference to parent SWABView."""
        self._parent_view = view

    def mouseMoveEvent(self, event):
        """Handle mouse move to underline WARNING lines on hover."""
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()

        # Check if this is a WARNING line
        if line_text.startswith('WARNING:'):
            # Underline the current line
            if self._hovered_block != cursor.blockNumber():
                self._hovered_block = cursor.blockNumber()
                self._apply_hover_effect(cursor)
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            # Remove underline if we're not on a WARNING line
            if self._hovered_block is not None:
                self._remove_hover_effect()
                self._hovered_block = None
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)

        super().mouseMoveEvent(event)

    def _apply_hover_effect(self, cursor):
        """Apply underline to the hovered WARNING line."""
        # Store current cursor position and scroll position
        old_cursor = self.textCursor()
        scrollbar = self.verticalScrollBar()
        scroll_pos = scrollbar.value()

        # Create format with underline
        fmt = QTextCharFormat()
        fmt.setFontUnderline(True)

        # Apply to the line
        cursor.mergeCharFormat(fmt)

        # Restore cursor and scroll position
        self.setTextCursor(old_cursor)
        scrollbar.setValue(scroll_pos)

    def _remove_hover_effect(self):
        """Remove underline from previously hovered line."""
        if self._hovered_block is None:
            return

        # Store scroll position
        scrollbar = self.verticalScrollBar()
        scroll_pos = scrollbar.value()

        # Find the previously hovered block
        cursor = QTextCursor(self.document().findBlockByNumber(self._hovered_block))
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)

        # Create format without underline
        fmt = QTextCharFormat()
        fmt.setFontUnderline(False)

        # Apply to the line
        cursor.setCharFormat(fmt)

        # Restore scroll position
        scrollbar.setValue(scroll_pos)

    def contextMenuEvent(self, event):
        """Handle right-click context menu for WARNING lines."""
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()

        # Check if this is a WARNING line with an address
        if line_text.startswith('WARNING:') and '[' in line_text and ']' in line_text:
            # Extract address from the line
            match = re.search(r'\[([^:]+):\s*([^\]]+)\]', line_text)
            if match:
                address = match.group(2).strip()

                # Create custom context menu
                menu = QMenu(self)
                debug_action = menu.addAction(f"Debug to this line")
                action = menu.exec_(event.globalPos())

                if action == debug_action and self._parent_view:
                    self._parent_view._on_debug_to_line(line_text, address)
        else:
            # Show default context menu for non-WARNING lines
            super().contextMenuEvent(event)


class QWarningAnnotation(QGraphicsEllipseItem):
    """
    A yellow dot annotation for SWAB warnings.
    """

    def __init__(self, addr: int, message: str, *args, **kwargs) -> None:
        # Position the dot with a Y offset to align with instruction line
        # (x, y, width, height) - move Y down by 2 pixels for better alignment
        super().__init__(-4, 2, 8, 8, *args, **kwargs)  # 8x8 pixel yellow dot
        self.addr = addr
        self.message = message
        self.setBrush(QBrush(QColor(255, 215, 0)))  # Gold/yellow color
        self.setPen(QColor(200, 170, 0))  # Darker border
        self.setToolTip(f"Warning at {hex(addr)}:\n{message}")
        self.setZValue(100)  # Ensure it's drawn on top

    def boundingRect(self):
        """Return the bounding rectangle of the annotation."""
        return super().boundingRect()

    def paint(self, painter, option, widget=None):
        """Paint the annotation."""
        super().paint(painter, option, widget)


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


class DockerRunDialog(QDialog):
    """Dialog for configuring Docker run command and container path."""

    def __init__(self, selected_image: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Docker Run Configuration")
        self.setMinimumWidth(500)

        self.selected_image = selected_image
        self.command = None
        self.container_path = None

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # Image info label
        image_label = QLabel(f"Docker Image: {self.selected_image}")
        image_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(image_label)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Command input
        self.command_input = QLineEdit()
        self.command_input.setText("uv run swab /workspace")
        self.command_input.setPlaceholderText("e.g., /bin/bash -c 'python main.py'")
        form_layout.addRow("Command to run:", self.command_input)

        # Container path input
        self.container_path_input = QLineEdit()
        self.container_path_input.setText("/workspace")
        self.container_path_input.setPlaceholderText("e.g., /workspace, /app, /project")
        form_layout.addRow("Copy project to:", self.container_path_input)

        layout.addLayout(form_layout)

        # Help text
        help_text = QLabel(
            "The current project will be copied to the specified path in the container.\n"
            "You can reference files in your command using this path."
        )
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_dialog)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _accept_dialog(self) -> None:
        """Validate and accept the dialog."""
        command = self.command_input.text().strip()
        container_path = self.container_path_input.text().strip()

        if not command:
            QMessageBox.warning(self, "Invalid Input", "Please enter a command to run.")
            return

        if not container_path:
            QMessageBox.warning(self, "Invalid Input", "Please enter a container path.")
            return

        if not container_path.startswith("/"):
            QMessageBox.warning(self, "Invalid Path", "Container path must be an absolute path (start with /).")
            return

        self.command = command
        self.container_path = container_path
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
        self.docker_process = None  # QProcess for running docker commands
        self.warnings = []  # Store extracted warnings from Docker output
        self._init_widgets()

    @staticmethod
    def extract_warning(console_output: str) -> list[dict[str, str]]:
        """
        Extract warning messages from Docker console output.

        Parses multi-line warning messages and extracts:
        - CPU address from the first line (second element in brackets)
        - Warning message from the second line

        Example input:
            WARNING:swab.engine: Engine renode: renode:rcc: [cpu1: 0x8005C3E] writing value 0x0 to offset 0x1C
            WARNING:swab.engine: Engine renode: renode:rcc: Unhandled write to offset 0x1C, value 0x0.

        Returns:
            List of dictionaries with 'address' and 'message' keys.
            Example: [{'address': '0x8005C3E', 'message': 'Unhandled write to offset 0x1C, value 0x0.'}]
        """
        warnings = []
        lines = console_output.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a WARNING line with an address
            if line.startswith('WARNING:') and '[' in line and ']' in line:
                # Extract the address (second element in brackets)
                # Pattern: [cpu1: 0x8005C3E] - we want the second part
                bracket_match = re.search(r'\[([^:]+):\s*([^\]]+)\]', line)

                if bracket_match:
                    address = bracket_match.group(2).strip()  # Get the second element (the address)

                    # Look for the next line which should contain the warning message
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()

                        # Check if next line is also a WARNING line
                        if next_line.startswith('WARNING:'):
                            # Extract the message after the last colon
                            message_match = re.search(r':\s*([^:]+)$', next_line)
                            if message_match:
                                message = message_match.group(1).strip()

                                warnings.append({
                                    'address': address,
                                    'message': message
                                })

                                # Skip the next line since we've already processed it
                                i += 1

            i += 1

        return warnings

    def _init_widgets(self) -> None:
        """Initialize the UI widgets."""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - console with interactive WARNING lines
        self.left_panel = ConsoleTextEdit()
        self.left_panel.set_parent_view(self)
        self.left_panel.setPlaceholderText("Output will appear here...")
        self.left_panel.setText("Welcome to SWAB!\n\nTo get started:\n1. Click 'Open' to open an existing project, or\n2. Click 'Create' to create a new project\n3. Select a Docker image and click 'Run'")

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

        # Docker image dropdown
        self.docker_image_dropdown = QComboBox()
        self.docker_image_dropdown.setToolTip("Select Docker image")
        self.docker_image_dropdown.setMinimumWidth(200)
        button_layout.addWidget(self.docker_image_dropdown)

        # Refresh docker images button
        self.refresh_docker_button = QPushButton("🔄")
        self.refresh_docker_button.setToolTip("Refresh Docker images")
        self.refresh_docker_button.setMaximumWidth(40)
        self.refresh_docker_button.clicked.connect(self._refresh_docker_images)
        button_layout.addWidget(self.refresh_docker_button)

        # Run button
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self._on_run_clicked)
        button_layout.addWidget(self.run_button)

        # Kill button (initially disabled until a process is running)
        self.kill_button = QPushButton("Kill")
        self.kill_button.clicked.connect(self._on_kill_clicked)
        self.kill_button.setEnabled(False)
        self.kill_button.setToolTip("Kill the running Docker container")
        button_layout.addWidget(self.kill_button)

        right_layout.addLayout(button_layout)

        # Load docker images initially
        self._refresh_docker_images()

        # Create IDE-like layout with file tree and code editor
        ide_splitter = QSplitter(Qt.Orientation.Horizontal)

        # File tree panel
        self.file_tree_container = QWidget()
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder widget for when no project is open
        self.file_tree_placeholder = QWidget()
        self.file_tree_placeholder.setStyleSheet("background-color: white;")

        self.file_tree = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_tree.setModel(self.file_model)

        # Don't set any root initially - will be set when project is opened/created
        # This keeps the file tree empty until a project is loaded

        # Hide unnecessary columns
        self.file_tree.setColumnHidden(1, True)  # Size
        self.file_tree.setColumnHidden(2, True)  # Type
        self.file_tree.setColumnHidden(3, True)  # Date Modified

        # Enable context menu
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

        # Connect double-click to open file
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)

        # Hide the file tree initially until a project is opened
        self.file_tree.setVisible(False)

        tree_layout.addWidget(self.file_tree_placeholder)
        tree_layout.addWidget(self.file_tree)
        self.file_tree_container.setLayout(tree_layout)

        # Code editor panel
        self.right_panel = CodeEdit()
        self.right_panel.use_spaces_instead_of_tabs = True
        self.right_panel.tab_length = 4

        # Add line number panel
        self.right_panel.panels.append(LineNumberPanel())

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

            # Don't update left panel - preserve console output

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

            # Don't update left panel - preserve console output

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

            # Don't update left panel - preserve console output

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
            self.file_tree.setVisible(True)  # Show the file tree when project is opened
            self.file_tree_placeholder.setVisible(False)  # Hide the placeholder

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
                self.file_tree.setVisible(True)  # Show the file tree when project is created
                self.file_tree_placeholder.setVisible(False)  # Hide the placeholder

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

                # Create engine.toml file in the engine folder
                engine_toml_path = os.path.join(engine_path, "engine.toml")
                with open(engine_toml_path, "w", encoding="utf-8") as f:
                    f.write("[engine]\n")
                    f.write('base = ""\n')

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

                # Don't update left panel - preserve console output

            except Exception as e:
                # Only show error in left panel if file fails to load
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

            # Don't update left panel - preserve console output
            # File saved successfully (silently)

        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")

    def _get_current_time(self) -> str:
        """Get current time as a formatted string."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _refresh_docker_images(self) -> None:
        """Refresh the docker images dropdown."""
        try:
            # Get list of docker images
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Parse the output to get image names
                images = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

                # Update dropdown
                self.docker_image_dropdown.clear()
                if images:
                    self.docker_image_dropdown.addItems(images)
                else:
                    self.docker_image_dropdown.addItem("No images found")

            else:
                self.docker_image_dropdown.clear()
                self.docker_image_dropdown.addItem("Docker not available")
                self.left_panel.setText(f"Error: Could not list Docker images\n\n{result.stderr}")

        except FileNotFoundError:
            self.docker_image_dropdown.clear()
            self.docker_image_dropdown.addItem("Docker not installed")
        except subprocess.TimeoutExpired:
            self.docker_image_dropdown.clear()
            self.docker_image_dropdown.addItem("Docker timeout")
        except Exception as e:
            self.docker_image_dropdown.clear()
            self.docker_image_dropdown.addItem("Error")
            self.left_panel.setText(f"Error refreshing Docker images: {e}")

    def _on_run_clicked(self) -> None:
        """Handle run button click - show dialog to get command and execute with Docker."""
        # Get selected docker image
        selected_image = self.docker_image_dropdown.currentText()

        # Check if docker is available
        if not selected_image or selected_image in ["No images found", "Docker not available", "Docker not installed", "Docker timeout", "Error"]:
            QMessageBox.warning(
                self,
                "Docker Not Available",
                "Docker is not available or no images found.\n\n"
                "Please ensure Docker is installed and running, then click the refresh button."
            )
            return

        # Check if a project is open
        if not self.current_project_path:
            QMessageBox.warning(
                self,
                "No Project Open",
                "Please open or create a project first.\n\n"
                "The project directory will be mounted to the Docker container."
            )
            return

        # Check if a process is already running
        if self.docker_process is not None and self.docker_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(
                self,
                "Process Running",
                "A Docker process is already running. Please wait for it to complete."
            )
            return

        # Show custom dialog to get command and container path
        dialog = DockerRunDialog(selected_image, self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return  # User cancelled

        command = dialog.command
        container_path = dialog.container_path

        # Initialize output
        self.left_panel.setText(
            f"Docker Run Started\n{'=' * 60}\n"
            f"Image: {selected_image}\n"
            f"Command: {command}\n"
            f"Project: {self.current_project_path}\n"
            f"Mounted at: {container_path}\n\n"
            f"--- Output ---\n"
        )

        # Create QProcess
        self.docker_process = QProcess(self)

        # Connect signals for real-time output
        self.docker_process.readyReadStandardOutput.connect(self._on_docker_stdout)
        self.docker_process.readyReadStandardError.connect(self._on_docker_stderr)
        self.docker_process.finished.connect(self._on_docker_finished)
        self.docker_process.errorOccurred.connect(self._on_docker_error)

        # Store command info for later use
        self.docker_process.setProperty("selected_image", selected_image)
        self.docker_process.setProperty("command", command)

        # Start the docker run command with volume mount
        # Using -i (interactive), --rm (remove after exit), and -v (volume mount) flags
        # Mount the current project directory to the specified container path
        args = [
            "run",
            "-i",
            "--rm",
            "-v", f"{self.current_project_path}:{container_path}",
            selected_image
        ] + command.split()

        self.docker_process.start("docker", args)

        # Enable Kill button and disable Run button while process is running
        self.kill_button.setEnabled(True)
        self.run_button.setEnabled(False)

    def _on_docker_stdout(self) -> None:
        """Handle stdout from docker process - append to left panel in real-time."""
        if self.docker_process:
            data = self.docker_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            if data:
                # Append to existing text
                current_text = self.left_panel.toPlainText()
                self.left_panel.setText(current_text + data)
                # Auto-scroll to bottom
                scrollbar = self.left_panel.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def _on_docker_stderr(self) -> None:
        """Handle stderr from docker process - append to left panel in real-time."""
        if self.docker_process:
            data = self.docker_process.readAllStandardError().data().decode('utf-8', errors='replace')
            if data:
                # Append stderr with prefix
                current_text = self.left_panel.toPlainText()
                self.left_panel.setText(current_text + f"[STDERR] {data}")
                # Auto-scroll to bottom
                scrollbar = self.left_panel.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    def _on_docker_finished(self, exit_code: int, exit_status) -> None:
        """Handle docker process completion."""
        if self.docker_process:
            selected_image = self.docker_process.property("selected_image")
            command = self.docker_process.property("command")

            # Append completion message
            current_text = self.left_panel.toPlainText()
            completion_msg = f"\n\n{'=' * 60}\nDocker Run Completed\nExit Code: {exit_code}\n"
            self.left_panel.setText(current_text + completion_msg)

            # Extract warnings from console output
            self.warnings = self.extract_warning(current_text)
            if self.warnings:
                warning_summary = f"Found {len(self.warnings)} warning(s)\n"
                self.left_panel.setText(current_text + completion_msg + warning_summary)

                # Refresh disassembly view to show warning annotations
                disasm_view = self.workspace.view_manager.first_view_in_category("disassembly")
                if disasm_view:
                    disasm_view.refresh()

            # Auto-scroll to bottom
            scrollbar = self.left_panel.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            # Disable Kill button and re-enable Run button
            self.kill_button.setEnabled(False)
            self.run_button.setEnabled(True)

    def _on_docker_error(self, error) -> None:
        """Handle docker process errors."""
        if self.docker_process:
            error_msg = f"\n\n[ERROR] Docker process error: {error}\n"
            current_text = self.left_panel.toPlainText()
            self.left_panel.setText(current_text + error_msg)

            # Auto-scroll to bottom
            scrollbar = self.left_panel.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _on_kill_clicked(self) -> None:
        """Handle kill button click - terminate the running Docker process."""
        if self.docker_process and self.docker_process.state() != QProcess.ProcessState.NotRunning:
            # Append kill message to output
            current_text = self.left_panel.toPlainText()
            kill_msg = f"\n\n[KILL] Terminating Docker container...\n"
            self.left_panel.setText(current_text + kill_msg)

            # Auto-scroll to bottom
            scrollbar = self.left_panel.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

            # Kill the process
            self.docker_process.kill()

            # Disable Kill button and re-enable Run button
            self.kill_button.setEnabled(False)
            self.run_button.setEnabled(True)

    def _on_debug_to_line(self, line_text: str, address: str) -> None:
        """
        Handle 'Debug to this line' context menu action for WARNING lines.

        Args:
            line_text: The full WARNING line text
            address: The extracted address from the WARNING line
        """
        # Append debug message to console
        current_text = self.left_panel.toPlainText()
        debug_msg = f"\n\n[DEBUG] Debug to line: {line_text}\n[DEBUG] Address: {address}\n"
        self.left_panel.setText(current_text + debug_msg)

        # Auto-scroll to bottom to show the new message
        scrollbar = self.left_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reload(self) -> None:
        """Reload the view."""
        pass

    def refresh(self) -> None:
        """Refresh the view."""
        pass
