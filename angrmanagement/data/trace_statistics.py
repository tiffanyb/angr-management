from PySide2.QtGui import QColor

import logging
import random
from collections import defaultdict

from angr.errors import SimEngineError

l = logging.getLogger(name=__name__)
l.setLevel('DEBUG')

class TraceStatistics:

    BBL_FILL_COLOR = QColor(00, 0xf0, 0xf0, 15)
    BBL_BORDER_COLOR = QColor(00, 0xf0, 0xf0)

    def __init__(self, workspace, trace):
        self.workspace = workspace
        self.trace = trace
        self.trace_func = list()
        self._statistics = None
        self._positions = None
        self._func_color = dict()
        self.count = None
        self.statistics(trace)
        self._mark_color = dict()


    def statistics(self, trace):
        """
        trace: bbl address list
        """
        self._statistics = defaultdict(int)
        self._positions = defaultdict(list)

        p = 0
        for bbl_addr in trace:
            try:
                block = self.workspace.instance.project.factory.block(bbl_addr)
            except SimEngineError:
                continue
            ins_addrs = block.instruction_addrs
            for addr in ins_addrs:
                self._statistics[addr] += 1
                self._positions[addr].append(p)

            func_address = self.workspace.instance.cfg.get_any_node(bbl_addr).function_address
            func_name = self.workspace.instance.project.kb.functions[func_address].name
            self.trace_func.append((bbl_addr, func_address, func_name))
            p += 1

        self.count = len(self.trace_func)
        # self.trace_func = [(a, self._func_addr(a), self._func_name(a))
             # for a in trace if
             # self.workspace.instance.cfg.get_any_node(a) is not None]


    def _func_addr(self, a):
        return self.workspace.instance.cfg.get_any_node(a).function_address

    def _func_name(self, a):
        return self.workspace.instance.project.kb.functions[self._func_addr(a)].name

    def get_count(self, ins):
        if ins in self._statistics:
            return self._statistics[ins]
        else:
            return 0

    def get_color(self, addr, i):
        pos = self._get_position(addr, i)
        return self._compute_color(pos)

    def get_func_color(self, func):
        if func in self._func_color:
            return self._func_color[func]
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        self._func_color[func] = QColor(r, g, b)
        return QColor(r, g, b)

    def set_mark_color(self, p, color):
        self._mark_color[p] = color

    def get_mark_color(self, addr, i):
        return self._mark_color[self._get_position(addr, i)]

    def _get_position(self, addr, i):
        return self._positions[addr][i]

    def _compute_color(self, pos):
        r = 10
        g = 10
        b = 255 / len(self.trace) * (pos+1)
        return QColor(r, g, b)

    def get_positions(self, addr):
        return self._positions[addr]
