from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
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
