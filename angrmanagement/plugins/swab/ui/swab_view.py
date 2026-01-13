from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from pyqodeng.core.panels import LineNumberPanel
from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from angrmanagement.ui.views.view import InstanceView

from ..managers import DockerManager, FileManager, ProjectManager
from ..models import Warning
from ..utils import WarningParser
from .console_widget import ConsoleTextEdit
from .dialogs import ConfigureProjectDialog, CreateProjectDialog, DockerRunDialog

if TYPE_CHECKING:
    from angrmanagement.data.instance import Instance
    from angrmanagement.ui.workspace import Workspace


class SWABView(InstanceView):
    """SWAB plugin coordinator view.

    Manages UI and coordinates between managers for:
    - Docker container execution
    - Project lifecycle
    - File operations
    - Warning detection and display
    """

    def __init__(self, workspace: Workspace, default_docking_position: str, instance: Instance) -> None:
        super().__init__("swab", workspace, default_docking_position, instance)

        self.base_caption = "SWAB"

        # Managers
        self.docker_manager = DockerManager(parent=self)
        self.project_manager = ProjectManager()
        self.file_manager = FileManager()

        # Data
        self.warnings: list[Warning] = []
        self.current_file_path: Path | None = None

        # UI Components (initialized in _init_widgets)
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
        self.docker_image_dropdown: QComboBox = None

        self._init_widgets()

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
        self.left_panel.setText(
            "Welcome to SWAB!\n\n"
            "To get started:\n"
            "1. Click 'Open' to open an existing project, or\n"
            "2. Click 'Create' to create a new project\n"
            "3. Select a Docker image and click 'Run'"
        )

        # Right panel container (IDE-like with file tree and code editor)
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Top button bar
        right_layout.addLayout(self._create_button_bar())

        # IDE-like layout with file tree and code editor
        ide_splitter = self._create_ide_layout()
        right_layout.addWidget(ide_splitter)
        right_container.setLayout(right_layout)

        # Add panels to main splitter
        splitter.addWidget(self.left_panel)
        splitter.addWidget(right_container)
        splitter.setSizes([400, 400])  # 50/50 split

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Load docker images initially
        self._refresh_docker_images()

    def _create_button_bar(self) -> QHBoxLayout:
        """Create the top button bar.

        Returns:
            Layout containing all buttons and controls
        """
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

        # Configure button
        self.configure_button = QPushButton("Configure")
        self.configure_button.clicked.connect(self._on_configure_clicked)
        self.configure_button.setEnabled(False)
        self.configure_button.setToolTip("Configure project (create a project first)")
        button_layout.addWidget(self.configure_button)

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._on_save_clicked)
        self.save_button.setEnabled(False)
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

        # Kill button
        self.kill_button = QPushButton("Kill")
        self.kill_button.clicked.connect(self._on_kill_clicked)
        self.kill_button.setEnabled(False)
        self.kill_button.setToolTip("Kill the running Docker container")
        button_layout.addWidget(self.kill_button)

        return button_layout

    def _create_ide_layout(self) -> QSplitter:
        """Create the IDE-like layout with file tree and code editor.

        Returns:
            Splitter containing file tree and code editor
        """
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

        # Hide unnecessary columns
        self.file_tree.setColumnHidden(1, True)  # Size
        self.file_tree.setColumnHidden(2, True)  # Type
        self.file_tree.setColumnHidden(3, True)  # Date Modified

        # Setup interactions
        self.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.file_tree.doubleClicked.connect(self._on_file_double_clicked)
        self.file_tree.setVisible(False)  # Hide until project is opened

        tree_layout.addWidget(self.file_tree_placeholder)
        tree_layout.addWidget(self.file_tree)
        self.file_tree_container.setLayout(tree_layout)

        # Code editor panel
        self.right_panel = CodeEdit()
        self.right_panel.use_spaces_instead_of_tabs = True
        self.right_panel.tab_length = 4

        # Add panels and modes
        self.right_panel.panels.append(LineNumberPanel())
        self.right_panel.modes.append(CaretLineHighlighterMode())
        self.right_panel.modes.append(PygmentsSyntaxHighlighter(self.right_panel.document()))
        self.right_panel.modes.append(AutoIndentMode())
        self.right_panel.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        # Set initial content
        self.right_panel.setPlainText("# Enter your Python code here\nprint('Hello from SWAB!')", "text/x-python", "utf-8")

        # Set font
        code_font = QFont("Monospace", 14)
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        self.right_panel.setFont(code_font)
        self.right_panel.zoom_in(3)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self.right_panel).activated.connect(self._on_run_clicked)
        QShortcut(QKeySequence.StandardKey.Save, self.right_panel).activated.connect(self._on_save_clicked)

        # Add to splitter
        ide_splitter.addWidget(self.file_tree_container)
        ide_splitter.addWidget(self.right_panel)
        ide_splitter.setSizes([200, 600])

        return ide_splitter

    # ==================== Docker Operations ====================

    def _refresh_docker_images(self) -> None:
        """Refresh the docker images dropdown."""
        images = self.docker_manager.get_images()

        self.docker_image_dropdown.clear()
        if images:
            self.docker_image_dropdown.addItems(images)
        else:
            self.docker_image_dropdown.addItem("No images found")

    def _on_run_clicked(self) -> None:
        """Handle run button click - show dialog and execute with Docker."""
        selected_image = self.docker_image_dropdown.currentText()

        # Validate Docker availability
        if not selected_image or selected_image == "No images found":
            QMessageBox.warning(
                self,
                "Docker Not Available",
                "Docker is not available or no images found.\n\n"
                "Please ensure Docker is installed and running, then click the refresh button."
            )
            return

        # Validate project is open
        if not self.project_manager.current_project_path:
            QMessageBox.warning(
                self,
                "No Project Open",
                "Please open or create a project first.\n\n"
                "The project directory will be mounted to the Docker container."
            )
            return

        # Check if already running
        if self.docker_manager.is_running():
            QMessageBox.warning(self, "Process Running", "A Docker process is already running. Please wait for it to complete.")
            return

        # Show dialog to get command and container path
        dialog = DockerRunDialog(selected_image, self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        command = dialog.command
        container_path = dialog.container_path

        # Initialize console output
        self.left_panel.setText(
            f"Docker Run Started\n{'=' * 60}\n"
            f"Image: {selected_image}\n"
            f"Command: {command}\n"
            f"Project: {self.project_manager.current_project_path}\n"
            f"Mounted at: {container_path}\n\n"
            f"--- Output ---\n"
        )

        # Start Docker process
        success = self.docker_manager.run(
            image=selected_image,
            command=command,
            project_path=str(self.project_manager.current_project_path),
            container_path=container_path,
            stdout_callback=self._on_docker_stdout,
            stderr_callback=self._on_docker_stderr,
            finished_callback=self._on_docker_finished,
            error_callback=self._on_docker_error,
        )

        if success:
            self.kill_button.setEnabled(True)
            self.run_button.setEnabled(False)

    def _on_kill_clicked(self) -> None:
        """Handle kill button click - terminate the running Docker process."""
        if self.docker_manager.kill():
            current_text = self.left_panel.toPlainText()
            self.left_panel.setText(current_text + "\n\n[KILL] Terminating Docker container...\n")
            self._scroll_console_to_bottom()
            self.kill_button.setEnabled(False)
            self.run_button.setEnabled(True)

    def _on_docker_stdout(self, data: str) -> None:
        """Handle stdout from docker process."""
        current_text = self.left_panel.toPlainText()
        self.left_panel.setText(current_text + data)
        self._scroll_console_to_bottom()

    def _on_docker_stderr(self, data: str) -> None:
        """Handle stderr from docker process."""
        current_text = self.left_panel.toPlainText()
        self.left_panel.setText(current_text + f"[STDERR] {data}")
        self._scroll_console_to_bottom()

    def _on_docker_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle docker process completion."""
        current_text = self.left_panel.toPlainText()
        completion_msg = f"\n\n{'=' * 60}\nDocker Run Completed\nExit Code: {exit_code}\n"

        # Extract warnings from console output
        self.warnings = WarningParser.parse(current_text)
        if self.warnings:
            completion_msg += f"Found {len(self.warnings)} warning(s)\n"

            # Refresh disassembly view to show warning annotations
            disasm_view = self.workspace.view_manager.first_view_in_category("disassembly")
            if disasm_view:
                disasm_view.refresh()

        self.left_panel.setText(current_text + completion_msg)
        self._scroll_console_to_bottom()

        # Re-enable buttons
        self.kill_button.setEnabled(False)
        self.run_button.setEnabled(True)

    def _on_docker_error(self, error: QProcess.ProcessError) -> None:
        """Handle docker process errors."""
        current_text = self.left_panel.toPlainText()
        self.left_panel.setText(current_text + f"\n\n[ERROR] Docker process error: {error}\n")
        self._scroll_console_to_bottom()

    def _on_debug_to_line(self, line_text: str, address: str) -> None:
        """Handle 'Debug to this line' context menu action.

        Args:
            line_text: Full WARNING line text
            address: Extracted address from WARNING line
        """
        current_text = self.left_panel.toPlainText()
        debug_msg = f"\n\n[DEBUG] Debug to line: {line_text}\n[DEBUG] Address: {address}\n"
        self.left_panel.setText(current_text + debug_msg)
        self._scroll_console_to_bottom()

    # ==================== Project Operations ====================

    def _on_open_clicked(self) -> None:
        """Handle Open button click - open an existing project folder."""
        from PySide6.QtWidgets import QFileDialog

        project_path = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )

        if not project_path:
            return

        try:
            metadata = self.project_manager.open_project(Path(project_path))

            # Update file tree
            self.file_tree.setRootIndex(self.file_model.index(str(metadata['path'])))
            self.file_tree.setVisible(True)
            self.file_tree_placeholder.setVisible(False)

            # Enable configure button
            self.configure_button.setEnabled(True)
            self.configure_button.setToolTip("Configure project simulation engines")

            # Load entry file if found
            if metadata['entry_file']:
                self._load_file_in_editor(metadata['entry_file'])

            # Update console
            output = f"Project opened successfully!\n\n"
            output += f"Name: {metadata['name']}\n"
            output += f"Location: {metadata['path']}\n\n"

            if metadata['entry_file']:
                output += f"Loaded file: {metadata['entry_file'].name}\n\n"
            else:
                output += "No entry point file found (main.py, app.py, etc.)\n"
                output += "Double-click any file in the tree to open it.\n\n"

            if metadata['is_configured']:
                output += "✓ Project is configured\n"
                if metadata['engines']:
                    output += f"Engines: {', '.join(metadata['engines'])}\n"
            else:
                output += "Click 'Configure' to add simulation engines.\n"

            self.left_panel.setText(output)

        except Exception as e:
            QMessageBox.critical(self, "Error Opening Project", f"Failed to open project:\n{e}")

    def _on_create_clicked(self) -> None:
        """Handle Create button click - show dialog to create new project."""
        dialog = CreateProjectDialog(self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        try:
            project_path = Path(dialog.project_path)
            project_name = dialog.project_name

            self.project_manager.create_project(project_path, project_name)

            # Update file tree
            self.file_tree.setRootIndex(self.file_model.index(str(project_path)))
            self.file_tree.setVisible(True)
            self.file_tree_placeholder.setVisible(False)

            # Enable configure button
            self.configure_button.setEnabled(True)
            self.configure_button.setToolTip("Configure project simulation engines")

            # Load main.py into editor
            main_py = project_path / "main.py"
            if main_py.exists():
                self._load_file_in_editor(main_py)

            # Update console
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
            QMessageBox.critical(self, "Error Creating Project", f"Failed to create project:\n{e}")

    def _on_configure_clicked(self) -> None:
        """Handle Configure button click - configure project with simulation engines."""
        if not self.project_manager.current_project_path:
            QMessageBox.warning(self, "No Project", "Please create a project first.")
            return

        # Check if reconfiguring
        if self.project_manager.is_configured():
            reply = QMessageBox.question(
                self,
                "Reconfigure Project",
                "This project is already configured.\n\n"
                "Reconfiguring will override configuration.toml.\n\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Show dialog to select engines
        dialog = ConfigureProjectDialog(self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        try:
            result = self.project_manager.configure_project(dialog.selected_engines)

            # Refresh file tree
            self.file_tree.setRootIndex(self.file_model.index(str(self.project_manager.current_project_path)))

            # Update console
            output = "Project configured successfully!\n\n"
            output += "Simulation Engines:\n"
            for engine in dialog.selected_engines:
                output += f"  - {engine.capitalize()}\n"
            if result['created_folders']:
                output += f"\nFolders created:\n"
                for folder in result['created_folders']:
                    output += f"  - {folder}/\n"
            output += f"\nConfiguration file: configuration.toml\n"

            self.left_panel.setText(output)

        except Exception as e:
            QMessageBox.critical(self, "Error Configuring Project", f"Failed to configure project:\n{e}")

    # ==================== File Operations ====================

    def _toggle_file_tree(self) -> None:
        """Toggle the visibility of the file tree panel."""
        is_visible = self.file_tree_container.isVisible()
        self.file_tree_container.setVisible(not is_visible)

    def _on_file_double_clicked(self, index) -> None:
        """Handle double-click on file in the tree - load file content into editor."""
        file_path = Path(self.file_model.filePath(index))

        if not self.file_model.isDir(index):
            try:
                self._load_file_in_editor(file_path)
            except Exception as e:
                self.left_panel.setText(f"Error loading file: {e}\n\nFile: {file_path}")

    def _load_file_in_editor(self, file_path: Path) -> None:
        """Load file content into editor.

        Args:
            file_path: Path to file to load
        """
        content = self.file_manager.read_file(file_path)
        mime_type = self.file_manager.detect_mime_type(file_path.name)

        self.right_panel.setPlainText(content, mime_type, "utf-8")
        self.current_file_path = file_path
        self.save_button.setEnabled(True)

    def _on_save_clicked(self) -> None:
        """Handle Save button click - save the current file."""
        if not self.current_file_path:
            QMessageBox.warning(self, "No File Open", "No file is currently open to save.")
            return

        try:
            content = self.right_panel.toPlainText()
            self.file_manager.write_file(self.current_file_path, content)
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", f"Failed to save file:\n{e}")

    def _on_tree_context_menu(self, position) -> None:
        """Handle right-click context menu on file tree."""
        index = self.file_tree.indexAt(position)

        if index.isValid():
            file_path = Path(self.file_model.filePath(index))
            is_dir = self.file_model.isDir(index)
        else:
            file_path = Path(self.file_model.filePath(self.file_tree.rootIndex()))
            is_dir = True

        menu = QMenu(self.file_tree)

        if is_dir:
            new_file_action = menu.addAction("New File...")
            new_file_action.triggered.connect(lambda: self._create_new_file(file_path))

            new_folder_action = menu.addAction("New Folder...")
            new_folder_action.triggered.connect(lambda: self._create_new_folder(file_path))

        if index.isValid():
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_item(file_path, is_dir))

        if not menu.isEmpty():
            menu.exec_(self.file_tree.viewport().mapToGlobal(position))

    def _create_new_file(self, parent_dir: Path) -> None:
        """Create a new file in the specified directory."""
        filename, ok = QInputDialog.getText(
            self,
            "New File",
            f"Enter filename:\n(in {parent_dir.name})",
            QLineEdit.EchoMode.Normal,
            "newfile.py"
        )

        if not ok or not filename:
            return

        try:
            file_path = self.file_manager.create_file(parent_dir, filename)
            self._load_file_in_editor(file_path)
        except FileExistsError:
            QMessageBox.warning(self, "File Exists", f"A file named '{filename}' already exists in this location.")
        except Exception as e:
            QMessageBox.critical(self, "Error Creating File", f"Failed to create file:\n{e}")

    def _create_new_folder(self, parent_dir: Path) -> None:
        """Create a new folder in the specified directory."""
        foldername, ok = QInputDialog.getText(
            self,
            "New Folder",
            f"Enter folder name:\n(in {parent_dir.name})",
            QLineEdit.EchoMode.Normal,
            "new_folder"
        )

        if not ok or not foldername:
            return

        try:
            self.file_manager.create_folder(parent_dir, foldername)
        except FileExistsError:
            QMessageBox.warning(self, "Folder Exists", f"A folder named '{foldername}' already exists in this location.")
        except Exception as e:
            QMessageBox.critical(self, "Error Creating Folder", f"Failed to create folder:\n{e}")

    def _delete_item(self, item_path: Path, is_dir: bool) -> None:
        """Delete a file or folder."""
        item_type = "folder" if is_dir else "file"

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete this {item_type}?\n\n{item_path.name}\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        try:
            self.file_manager.delete_item(item_path)

            # Clear editor if deleted file was currently open
            if not is_dir and self.current_file_path == item_path:
                self.right_panel.setPlainText("", "text/plain", "utf-8")
                self.current_file_path = None
                self.save_button.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, f"Error Deleting {item_type.capitalize()}", f"Failed to delete {item_type}:\n{e}")

    # ==================== Utility Methods ====================

    def _scroll_console_to_bottom(self) -> None:
        """Scroll console to bottom."""
        scrollbar = self.left_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reload(self) -> None:
        """Reload the view."""
        pass

    def refresh(self) -> None:
        """Refresh the view."""
        pass
