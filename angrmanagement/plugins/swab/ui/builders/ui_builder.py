from __future__ import annotations

from typing import TYPE_CHECKING

from pyqodeng.core.api import CodeEdit
from pyqodeng.core.modes import AutoIndentMode, CaretLineHighlighterMode, PygmentsSyntaxHighlighter
from pyqodeng.core.panels import LineNumberPanel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextOption
from PySide6.QtWidgets import (
    QComboBox,
    QFileSystemModel,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..console_widget import ConsoleTextEdit

if TYPE_CHECKING:
    from ..swab_view import SWABView


class UIBuilder:
    """Builds UI components for SWAB view.

    Responsibilities:
    - Creating layouts
    - Building button bars
    - Setting up panels and widgets
    - Configuring shortcuts
    """

    @staticmethod
    def build_main_layout(view: SWABView) -> QVBoxLayout:
        """Build the main layout for SWAB view.

        Args:
            view: SWAB view to build layout for

        Returns:
            Main vertical layout
        """
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create splitter for two panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - console
        view.left_panel = UIBuilder._build_console_panel(view)

        # Right panel - IDE
        right_container = UIBuilder._build_right_panel(view)

        # Add panels to main splitter
        splitter.addWidget(view.left_panel)
        splitter.addWidget(right_container)
        splitter.setSizes([400, 400])  # 50/50 split

        main_layout.addWidget(splitter)
        return main_layout

    @staticmethod
    def _build_console_panel(view: SWABView) -> ConsoleTextEdit:
        """Build the left console panel.

        Args:
            view: SWAB view

        Returns:
            Console text edit widget
        """
        console = ConsoleTextEdit()
        console.set_parent_view(view)
        console.setPlaceholderText("Output will appear here...")
        console.setText(
            "Welcome to SWAB!\n\n"
            "To get started:\n"
            "1. Click 'Open' to open an existing project, or\n"
            "2. Click 'Create' to create a new project\n"
            "3. Select a Docker image and click 'Run'"
        )
        return console

    @staticmethod
    def _build_right_panel(view: SWABView) -> QWidget:
        """Build the right panel container (IDE-like).

        Args:
            view: SWAB view

        Returns:
            Right panel container widget
        """
        right_container = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Top button bar
        right_layout.addLayout(UIBuilder._build_button_bar(view))

        # IDE-like layout with file tree and code editor
        ide_splitter = UIBuilder._build_ide_layout(view)
        right_layout.addWidget(ide_splitter)

        right_container.setLayout(right_layout)
        return right_container

    @staticmethod
    def _build_button_bar(view: SWABView) -> QHBoxLayout:
        """Create the top button bar.

        Args:
            view: SWAB view

        Returns:
            Layout containing all buttons and controls
        """
        button_layout = QHBoxLayout()

        # Toggle button for file tree
        view.toggle_tree_button = QToolButton()
        view.toggle_tree_button.setText("≡")
        view.toggle_tree_button.setToolTip("Toggle file tree")
        view.toggle_tree_button.setCheckable(True)
        view.toggle_tree_button.setChecked(True)
        view.toggle_tree_button.clicked.connect(view.file_handler.toggle_file_tree)
        button_layout.addWidget(view.toggle_tree_button)

        button_layout.addStretch()

        # Open button
        view.open_button = QPushButton("Open")
        view.open_button.clicked.connect(view._on_open_clicked)
        view.open_button.setToolTip("Open an existing project folder")
        button_layout.addWidget(view.open_button)

        # Create button
        view.create_button = QPushButton("Create")
        view.create_button.clicked.connect(view._on_create_clicked)
        button_layout.addWidget(view.create_button)

        # Configure button
        view.configure_button = QPushButton("Configure")
        view.configure_button.clicked.connect(view._on_configure_clicked)
        view.configure_button.setEnabled(False)
        view.configure_button.setToolTip("Configure project (create a project first)")
        button_layout.addWidget(view.configure_button)

        # Save button
        view.save_button = QPushButton("Save")
        view.save_button.clicked.connect(view._on_save_clicked)
        view.save_button.setEnabled(False)
        view.save_button.setToolTip("Save current file")
        button_layout.addWidget(view.save_button)

        # Docker image dropdown
        view.docker_image_dropdown = QComboBox()
        view.docker_image_dropdown.setToolTip("Select Docker image")
        view.docker_image_dropdown.setMinimumWidth(200)
        button_layout.addWidget(view.docker_image_dropdown)

        # Refresh docker images button
        view.refresh_docker_button = QPushButton("🔄")
        view.refresh_docker_button.setToolTip("Refresh Docker images")
        view.refresh_docker_button.setMaximumWidth(40)
        view.refresh_docker_button.clicked.connect(view._on_refresh_docker_clicked)
        button_layout.addWidget(view.refresh_docker_button)

        # Run button
        view.run_button = QPushButton("Run")
        view.run_button.clicked.connect(view._on_run_clicked)
        button_layout.addWidget(view.run_button)

        # Kill button
        view.kill_button = QPushButton("Kill")
        view.kill_button.clicked.connect(view._on_kill_clicked)
        view.kill_button.setEnabled(False)
        view.kill_button.setToolTip("Kill the running Docker container")
        button_layout.addWidget(view.kill_button)

        return button_layout

    @staticmethod
    def _build_ide_layout(view: SWABView) -> QSplitter:
        """Create the IDE-like layout with file tree and code editor.

        Args:
            view: SWAB view

        Returns:
            Splitter containing file tree and code editor
        """
        ide_splitter = QSplitter(Qt.Orientation.Horizontal)

        # File tree panel
        file_tree_container = UIBuilder._build_file_tree(view)
        view.file_tree_container = file_tree_container

        # Code editor panel
        code_editor = UIBuilder._build_code_editor(view)
        view.right_panel = code_editor

        # Add to splitter
        ide_splitter.addWidget(file_tree_container)
        ide_splitter.addWidget(code_editor)
        ide_splitter.setSizes([200, 600])

        return ide_splitter

    @staticmethod
    def _build_file_tree(view: SWABView) -> QWidget:
        """Build the file tree panel.

        Args:
            view: SWAB view

        Returns:
            File tree container widget
        """
        container = QWidget()
        tree_layout = QVBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder widget for when no project is open
        view.file_tree_placeholder = QWidget()
        view.file_tree_placeholder.setStyleSheet("background-color: white;")

        view.file_tree = QTreeView()
        view.file_model = QFileSystemModel()
        view.file_model.setRootPath("")
        view.file_tree.setModel(view.file_model)

        # Hide unnecessary columns
        view.file_tree.setColumnHidden(1, True)  # Size
        view.file_tree.setColumnHidden(2, True)  # Type
        view.file_tree.setColumnHidden(3, True)  # Date Modified

        # Setup interactions
        view.file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.file_tree.customContextMenuRequested.connect(view.file_handler.show_tree_context_menu)
        view.file_tree.doubleClicked.connect(view.file_handler.on_file_double_clicked)
        view.file_tree.setVisible(False)  # Hide until project is opened

        tree_layout.addWidget(view.file_tree_placeholder)
        tree_layout.addWidget(view.file_tree)
        container.setLayout(tree_layout)

        return container

    @staticmethod
    def _build_code_editor(view: SWABView) -> CodeEdit:
        """Build the code editor panel.

        Args:
            view: SWAB view

        Returns:
            Code editor widget
        """
        editor = CodeEdit()
        editor.use_spaces_instead_of_tabs = True
        editor.tab_length = 4

        # Add panels and modes
        editor.panels.append(LineNumberPanel())
        editor.modes.append(CaretLineHighlighterMode())
        editor.modes.append(PygmentsSyntaxHighlighter(editor.document()))
        editor.modes.append(AutoIndentMode())
        editor.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        # Set initial content
        editor.setPlainText("# Enter your Python code here\nprint('Hello from SWAB!')", "text/x-python", "utf-8")

        # Set font
        code_font = QFont("Monospace", 14)
        code_font.setStyleHint(QFont.StyleHint.Monospace)
        editor.setFont(code_font)
        editor.zoom_in(3)

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), editor).activated.connect(view._on_run_clicked)
        QShortcut(QKeySequence.StandardKey.Save, editor).activated.connect(view._on_save_clicked)

        return editor
