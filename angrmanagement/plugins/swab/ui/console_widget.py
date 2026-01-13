from __future__ import annotations

import re
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QMenu, QTextEdit

if TYPE_CHECKING:
    from .swab_view import SWABView


class ConsoleTextEdit(QTextEdit):
    """Custom QTextEdit for console output with interactive WARNING lines.

    Features:
    - Underlines WARNING lines on hover
    - Changes cursor to pointing hand on WARNING lines
    - Context menu with "Debug to this line" action
    - Preserves scroll position during formatting
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMouseTracking(True)
        self._hovered_block = None
        self._parent_view: SWABView | None = None

    def set_parent_view(self, view: SWABView) -> None:
        """Set reference to parent SWABView.

        Args:
            view: Parent SWABView instance for callbacks
        """
        self._parent_view = view

    def mouseMoveEvent(self, event):
        """Handle mouse move to underline WARNING lines on hover.

        Args:
            event: Mouse move event
        """
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
        """Apply underline to the hovered WARNING line.

        Args:
            cursor: Text cursor for the line to underline
        """
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
        """Handle right-click context menu for WARNING lines.

        Args:
            event: Context menu event
        """
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
                debug_action = menu.addAction("Debug to this line")
                action = menu.exec_(event.globalPos())

                if action == debug_action and self._parent_view:
                    self._parent_view._on_debug_to_line(line_text, address)
        else:
            # Show default context menu for non-WARNING lines
            super().contextMenuEvent(event)
