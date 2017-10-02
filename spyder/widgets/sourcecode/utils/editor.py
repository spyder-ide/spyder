# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Editor utils."""

from qtpy.QtGui import QTextBlockUserData


class BlockUserData(QTextBlockUserData):
    def __init__(self, editor):
        QTextBlockUserData.__init__(self)
        self.editor = editor
        self.breakpoint = False
        self.breakpoint_condition = None
        self.code_analysis = []
        self.todo = ''
        self.editor.blockuserdata_list.append(self)

    def is_empty(self):
        return not self.breakpoint and not self.code_analysis and not self.todo

    def __del__(self):
        bud_list = self.editor.blockuserdata_list
        bud_list.pop(bud_list.index(self))
