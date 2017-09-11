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
from spyder.api.manager import Manager


class TextDecorationsManager(Manager):
    """
    Manages the collection of TextDecoration that have been set on the editor
    widget.
    """
    def __init__(self, editor):
        super(TextDecorationsManager, self).__init__(editor)
        self._decorations = []

    def append(self, decoration):
        """
        Adds a text decoration on a CodeEditor instance

        :param decoration: Text decoration to add
        :type decoration: spyder.api.TextDecoration
        """
        if decoration not in self._decorations:
            self._decorations.append(decoration)
            self._order_decorations()
            self.editor.setExtraSelections(self._decorations)
            return True
        return False

    def remove(self, decoration):
        """
        Removes a text decoration from the editor.

        :param decoration: Text decoration to remove
        :type decoration: spyder.api.TextDecoration
        """
        try:
            self._decorations.remove(decoration)
            self.editor.setExtraSelections(self._decorations)
            return True
        except ValueError:
            return False

    def extend(self, decorations):
        """
        Adds several text decorations on a CodeEditor instance.

        Args:
            decorations (list of spyder.api.TextDecoration)
        Returns:
            int: Amount of decorations added.
        """
        not_repeated = set(decorations) - set(self._decorations)
        self._decorations.extend(list(not_repeated))
        self._order_decorations()
        self.editor.setExtraSelections(self._decorations)
        return len(not_repeated)

    def clear(self):
        """Removes all text decoration from the editor."""
        self._decorations[:] = []
        try:
            self.editor.setExtraSelections(self._decorations)
        except RuntimeError:
            pass

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
