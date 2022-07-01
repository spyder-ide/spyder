# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
Contains the text decorations manager.

Adapted from pyqode/core/managers/decorations.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/managers/decorations.py>
"""

# Third party imports
from qtpy.QtCore import QObject, QTimer, Slot
from qtpy.QtGui import QTextCharFormat

# Local imports
from spyder.api.manager import Manager


# Timeout to avoid almost simultaneous calls to update decorations, which
# introduces a lot of sluggishness in the editor.
UPDATE_TIMEOUT = 15  # milliseconds


class TextDecorationsManager(Manager, QObject):
    """
    Manages the collection of TextDecoration that have been set on the editor
    widget.
    """
    def __init__(self, editor):
        super(TextDecorationsManager, self).__init__(editor)
        QObject.__init__(self, None)
        self._decorations = []

        # Timer to not constantly update decorations.
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(UPDATE_TIMEOUT)
        self.update_timer.timeout.connect(
            self._update)

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
        update: Bool: should the decorations be updated immediately?
            Set to False to avoid updating several times while removing
            several decorations
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
        self.update()

    def update(self):
        """
        Update decorations.

        This starts a timer to update decorations only after
        UPDATE_TIMEOUT has passed. That avoids multiple calls to
        _update in a very short amount of time.
        """
        self.update_timer.start()

    @Slot()
    def _update(self):
        """Update editor extra selections with added decorations.

        NOTE: Update TextDecorations to use editor font, using a different
        font family and point size could cause unwanted behaviors.
        """
        try:
            font = self.editor.font()

            # Get the current visible block numbers
            first, last = self.editor.get_buffer_block_numbers()

            # Update visible decorations
            visible_decorations = []
            for decoration in self._decorations:
                need_update_sel = False
                cursor = decoration.cursor
                sel_start = cursor.selectionStart()
                # This is required to update extra selections from the point
                # an initial selection was made.
                # Fixes spyder-ide/spyder#14282
                if sel_start is not None:
                    doc = cursor.document()
                    block_nb_start = doc.findBlock(sel_start).blockNumber()
                    need_update_sel = first <= block_nb_start <= last

                block_nb = decoration.cursor.block().blockNumber()
                if (first <= block_nb <= last or need_update_sel or
                        decoration.kind == 'current_cell'):
                    visible_decorations.append(decoration)
                    try:
                        decoration.format.setFont(
                            font, QTextCharFormat.FontPropertiesSpecifiedOnly)
                    except (TypeError, AttributeError):  # Qt < 5.3
                        decoration.format.setFontFamily(font.family())
                        decoration.format.setFontPointSize(font.pointSize())

            self.editor.setExtraSelections(visible_decorations)
        except RuntimeError:
            # This is needed to fix spyder-ide/spyder#9173.
            return

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
