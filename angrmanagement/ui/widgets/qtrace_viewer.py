from PySide2.QtWidgets import QWidget, QHBoxLayout, QGraphicsScene, \
        QGraphicsView, QGraphicsItemGroup
from PySide2.QtGui import QPen, QBrush, QLinearGradient, QPixmap, \
        QColor
from PySide2.QtCore import Qt

import logging
l = logging.getLogger(name=__name__)
l.setLevel('DEBUG')
class QTraceViewer(QWidget):
    def __init__(self, workspace, disasm_view, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.disasm_view = disasm_view
        self._trace = None
        self.view = None
        self.scene = None
        self._trace_stat = None
        self.mark = None
        self._init_widgets()

        self.LEGEND_X = -50
        self.LEGEND_Y = 0
        self.LEGEND_WIDTH = 10

        self.TRACE_FUNC_X = 0
        self.TRACE_FUNC_Y = 0
        self.TRACE_FUNC_WIDTH = 50
        self.TRACE_FUNC_HEIGHT = 100

        self.MARK_X = self.LEGEND_X
        self.MARK_WIDTH = self.TRACE_FUNC_X - self.LEGEND_X + self.TRACE_FUNC_WIDTH
        self.MARK_HEIGHT = 5


    def _init_widgets(self):
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self.trace_func = QGraphicsItemGroup()
        self.legend = QGraphicsItemGroup()

        self.scene.addItem(self.legend)
        self.scene.addItem(self.trace_func)


        layout = QHBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def _show_legend(self):
        pen = QPen()
        gradient = QLinearGradient(-50, 0, -50, 300)
        gradient.setColorAt(0.0, Qt.red)
        gradient.setColorAt(0.4, Qt.yellow)
        gradient.setColorAt(0.6, Qt.green)
        gradient.setColorAt(0.8, Qt.blue)
        brush = QBrush(gradient)

        self.legend = self.scene.addRect(self.LEGEND_X, self.LEGEND_Y,
                self.LEGEND_WIDTH, self.height,
            QPen(), brush)
        # qPix = QPixmap.grabWidget(self.scene)
        """
        qPix = QWidget.grab(self.scene.activeWindow())
        self.legend_img = qPix.toImage()
        l.debug('Image height: %d', self.legend_img.height())
        if self.legend_img.save('/tmp/a.png',
                'png'):
            l.debug('save')
        else:
            l.debug('save unsuccessfully')
        color = QColor(self.legend_img.pixel(25, 20))

        self.scene.addRect(self.LEGEND_X, 20, self.FUNC_TRACE_X - , 5, pen, QBrush(color))
        (r, g, b) = color.red(), color.green(), color.blue()
        l.debug('R: %d, G: %d, B: %d', r, g, b)
        """

    def mark_instruction(self, addr):
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
        # TODO: change color
        return QColor(10, 10, 10)

    def _get_mark_y(self, i, total):
        # TODO: change trace_func_height
        return self.TRACE_FUNC_Y + self.TRACE_FUNC_HEIGHT * i

    def _show_trace_func(self):
        x = 0
        y = 0
        prev_name = None
        for (bbl, func, name) in self._trace_stat.trace_func:
            l.debug('Draw function %x %s' % (func, name))
            color = self._trace_stat.get_func_color(func)
            self.trace_func.addToGroup( self.scene.addRect(x, y,
                self.TRACE_FUNC_WIDTH, self.TRACE_FUNC_HEIGHT,
                QPen(color), QBrush(color)))
            if name != prev_name:
                tag = self.scene.addText(name)
                tag.setPos(x + 100, y - tag.boundingRect().height() / 2)
                self.trace_func.addToGroup(tag)
                anchor = self.scene.addLine(
                        self.TRACE_FUNC_X + self.TRACE_FUNC_WIDTH, y +
                        5,
                        x+100, y + 5)
                self.trace_func.addToGroup(anchor)
                prev_name = name
            y += 100
        self.height = y


    def set_trace(self, trace):
        self._trace_stat = trace
        self._show_trace_func()
        self._show_legend()
