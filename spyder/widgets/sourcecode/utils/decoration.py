# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Copyright © <2013-2016> <Colin Duquesnoy and others, see pyqode/AUTHORS.rst>
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Contains the text decorations manager.
Adapted from https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/managers/decorations.py
"""
from qtpy.QtGui import QTextCharFormat

from spyder.api.manager import Manager


class TextDecorationsManager(Manager):
    """
    Manages the collection of TextDecoration that have been set on the editor
    widget.
    """
    def __init__(self, editor):
        super(TextDecorationsManager, self).__init__(editor)
        self._decorations = []

    def add(self, decorations):
        """
        Add text decorations on a CodeEditor instance.

        Don't add duplicated decorations, and order decorations according
        draw_order and the size of the selection.

        Args:
            decorations (sourcecode.api.TextDecoration) (could be a list)
        Returns:
            int: Amount of decorations added.
        """
        added = 0
        if isinstance(decorations, list):
            not_repeated = set(decorations) - set(self._decorations)
            self._decorations.extend(list(not_repeated))
            added = len(not_repeated)
        elif decorations not in self._decorations:
            self._decorations.append(decorations)
            added = 1

        if added > 0:
            self._order_decorations()
            self.update()
        return added

    def remove(self, decoration):
        """
        Removes a text decoration from the editor.

        :param decoration: Text decoration to remove
        :type decoration: spyder.api.TextDecoration
        """
        try:
            self._decorations.remove(decoration)
            self.update()
            return True
        except ValueError:
            return False

    def clear(self):
        """Removes all text decoration from the editor."""
        self._decorations[:] = []
        try:
            self.update()
        except RuntimeError:
            pass

    def update(self):
        """Update editor extra selections with added decorations.

        NOTE: Update TextDecorations to use editor font, using a different
        font family and point size could cause unwanted behaviors.
        """
        font = self.editor.font()
        for decoration in self._decorations:
            try:
                decoration.format.setFont(
                        font, QTextCharFormat.FontPropertiesSpecifiedOnly)
            except (TypeError, AttributeError):  # Qt < 5.3
                decoration.format.setFontFamily(font.family())
                decoration.format.setFontPointSize(font.pointSize())
        self.editor.setExtraSelections(self._decorations)

    def __iter__(self):
        return iter(self._decorations)

    def __len__(self):
        return len(self._decorations)

    def _order_decorations(self):
        """Order decorations according draw_order and size of selection.

        Highest draw_order will appear on top of the lowest values.

        If draw_order is equal,smaller selections are draw in top of
        bigger selections.
        """
        def order_function(sel):
            end = sel.cursor.selectionEnd()
            start = sel.cursor.selectionStart()
            return sel.draw_order, -(end - start)

        self._decorations = sorted(self._decorations,
                                   key=order_function)
