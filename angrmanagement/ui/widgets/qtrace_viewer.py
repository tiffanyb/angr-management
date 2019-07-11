from PySide2.QtWidgets import QWidget, QHBoxLayout, QGraphicsScene, \
        QGraphicsView, QGraphicsItemGroup
from PySide2.QtGui import QPen, QBrush, QLinearGradient, QPixmap, \
        QColor, QPainter
from PySide2.QtCore import Qt, QRectF, QSize

import logging
l = logging.getLogger(name=__name__)
l.setLevel('DEBUG')
class QTraceViewer(QWidget):
    TAG_SPACING = 50
    def __init__(self, workspace, disasm_view, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.disasm_view = disasm_view
        self._trace = None
        self.view = None
        self.scene = None
        self._trace_stat = None
        self.mark = None
        self.selected_ins = None
        self._init_widgets()

        self.LEGEND_X = -50
        self.LEGEND_Y = 0
        self.LEGEND_WIDTH = 10

        self.TRACE_FUNC_X = 0
        self.TRACE_FUNC_Y = 0
        self.TRACE_FUNC_WIDTH = 50
        self.TRACE_FUNC_HEIGHT = 1000

        self.MARK_X = self.LEGEND_X
        self.MARK_WIDTH = self.TRACE_FUNC_X - self.LEGEND_X + self.TRACE_FUNC_WIDTH
        self.MARK_HEIGHT = 5


    def _init_widgets(self):
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self.trace_func = QGraphicsItemGroup()
        self.scene.addItem(self.trace_func)

        self.legend = None

        layout = QHBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
        self.setFixedWidth(500)

    def _show_legend(self):
        pen = QPen(Qt.transparent)

        gradient = QLinearGradient(self.LEGEND_X, self.LEGEND_Y,
                self.LEGEND_X, self.LEGEND_Y + self.height)
        gradient.setColorAt(0.0, Qt.red)
        gradient.setColorAt(0.4, Qt.yellow)
        gradient.setColorAt(0.6, Qt.green)
        gradient.setColorAt(0.8, Qt.blue)
        brush = QBrush(gradient)

        self.legend = self.scene.addRect(self.LEGEND_X, self.LEGEND_Y,
                self.LEGEND_WIDTH, self.height, pen, brush)

    def mark_instruction(self, addr):
        self.selected_ins = addr
        if self.mark is not None:
            self.scene.removeItem(self.mark)
        self.mark = QGraphicsItemGroup()
        self.scene.addItem(self.mark)

        positions = self._trace_stat.get_positions(addr)
        for p in positions:
            color = self._get_mark_color(p, self._trace_stat.count)
            y = self._get_mark_y(p, self._trace_stat.count)
            self.mark.addToGroup(self.scene.addRect(self.MARK_X, y, self.MARK_WIDTH,
                    self.MARK_HEIGHT, QPen(color), QBrush(color)))

    def _get_mark_color(self, i, total):
        return self.legend_img.pixelColor(self.LEGEND_WIDTH / 2,
                self.height * i / total + 1)

    def _get_mark_y(self, i, total):
        # TODO: change trace_func_height
        return self.TRACE_FUNC_Y + self.trace_func_unit_height * i

    def _graphicsitem_to_pixmap(self, graph):
        if graph.scene() is not None:
            r = graph.boundingRect()
            pixmap = QPixmap(r.width(), r.height())
            pixmap.fill(QColor(0, 0, 0, 0));
            painter = QPainter(pixmap)
            painter.drawRect(r)
            graph.scene().render(painter, QRectF(), graph.sceneBoundingRect())
            return pixmap
        else:
            return None

    def _show_trace_func(self):
        x = self.TRACE_FUNC_X
        y = self.TRACE_FUNC_Y
        prev_name = None
        for (bbl, func, name) in self._trace_stat.trace_func:
            l.debug('Draw function %x %s' % (func, name))
            color = self._trace_stat.get_func_color(func)
            self.trace_func.addToGroup( self.scene.addRect(x, y,
                self.TRACE_FUNC_WIDTH, self.trace_func_unit_height,
                QPen(color), QBrush(color)))
            if name != prev_name:
                tag = self.scene.addText(name)
                tag.setPos(x + self.TRACE_FUNC_WIDTH +
                        self.TAG_SPACING, y - tag.boundingRect().height() / 2)
                self.trace_func.addToGroup(tag)
                anchor = self.scene.addLine(
                        self.TRACE_FUNC_X + self.TRACE_FUNC_WIDTH, y,
                        x + self.TRACE_FUNC_WIDTH + self.TAG_SPACING, y)
                self.trace_func.addToGroup(anchor)
                prev_name = name
            y += self.trace_func_unit_height
        self.height = y


    def _set_mark_color(self):
        pixmap = self._graphicsitem_to_pixmap(self.legend)
        self.legend_img = pixmap.toImage()
        for p in range(self._trace_stat.count):
            color = self._get_mark_color(p, self._trace_stat.count)
            self._trace_stat.set_mark_color(p, color)

    def set_trace(self, trace):
        self._trace_stat = trace
        self.trace_func_unit_height = self.TRACE_FUNC_HEIGHT / self._trace_stat.count
        self._show_trace_func()
        self._show_legend()
        self._set_mark_color()
        if self.selected_ins is not None:
            self.mark_instruction(self.selected_ins)
