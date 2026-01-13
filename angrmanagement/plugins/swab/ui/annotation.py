from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QGraphicsEllipseItem

if TYPE_CHECKING:
    from ..models import Warning


class QWarningAnnotation(QGraphicsEllipseItem):
    """A yellow dot annotation for SWAB warnings in disassembly view.

    Displays a small yellow circle next to instructions with warnings.
    """

    def __init__(self, warning: Warning, insn_addr: int | None = None, *args, **kwargs) -> None:
        """Initialize warning annotation.

        Args:
            warning: Warning object with address and message
            insn_addr: Instruction address where the annotation should appear.
                      If None, uses warning.address (for backward compatibility)
            *args: Additional positional arguments for QGraphicsEllipseItem
            **kwargs: Additional keyword arguments for QGraphicsEllipseItem
        """
        # Position the dot with a Y offset to align with instruction line
        # (x, y, width, height) - move Y down by 2 pixels for better alignment
        super().__init__(-4, 2, 8, 8, *args, **kwargs)  # 8x8 pixel yellow dot
        self.warning = warning
        # Use the instruction address if provided (handles Thumb mode correctly)
        # Otherwise fall back to warning address
        self.addr = insn_addr if insn_addr is not None else warning.address
        self.message = warning.message
        self.setBrush(QBrush(QColor(255, 215, 0)))  # Gold/yellow color
        self.setPen(QColor(200, 170, 0))  # Darker border
        self.setToolTip(f"Warning at {warning.to_hex()}:\n{warning.message}")
        self.setZValue(100)  # Ensure it's drawn on top

    def boundingRect(self):
        """Return the bounding rectangle of the annotation.

        Returns:
            Bounding rectangle for the annotation
        """
        return super().boundingRect()

    def paint(self, painter, option, widget=None):
        """Paint the annotation.

        Args:
            painter: QPainter to use for drawing
            option: Style options
            widget: Widget being painted on
        """
        super().paint(painter, option, widget)
