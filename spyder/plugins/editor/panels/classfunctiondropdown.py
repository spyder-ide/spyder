# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
"""
A Class and Function Dropdown Panel for Spyder.
"""

# Third party imports
from intervaltree import IntervalTree
from qtpy.QtCore import QSize, Qt, Slot
from qtpy.QtWidgets import QComboBox, QHBoxLayout

# Local imports
from spyder.api.panel import Panel
from spyder.config.base import _
from spyder.plugins.completion.manager.api import SymbolKind
from spyder.utils import icon_manager as ima


class ClassFunctionDropdown(Panel):
    """
    Class and Function/Method Dropdowns Widget.

    Parameters
    ----------
    editor : :class:`spyder.plugins.editor.widgets.codeeditor.CodeEditor`
        The editor to act on.
    """

    def __init__(self, editor):
        super(ClassFunctionDropdown, self).__init__(editor)

        # Internal data
        self._tree = IntervalTree()
        self._data = None
        self.classes = []
        self.funcs = []

        # Widgets
        self._editor = editor
        self.class_cb = QComboBox()
        self.method_cb = QComboBox()

        # Widget setup
        self.class_cb.addItem(_('<None>'), 0)
        self.method_cb.addItem(_('<None>'), 0)

        # The layout
        hbox = QHBoxLayout()
        hbox.addWidget(self.class_cb)
        hbox.addWidget(self.method_cb)
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)
        self.setLayout(hbox)

        # Signals
        self._editor.sig_cursor_position_changed.connect(
            self._handle_cursor_position_change_event
        )
        self.class_cb.activated.connect(self.combobox_activated)
        self.method_cb.activated.connect(self.combobox_activated)

    def _getVerticalSize(self):
        """Get the default height of a QComboBox."""
        return self.class_cb.height()

    @Slot(int, int)
    def _handle_cursor_position_change_event(self, linenum, column):
        self.update_selected(linenum)

    def sizeHint(self):
        """Override Qt method."""
        return QSize(0, self._getVerticalSize())

    def combobox_activated(self):
        """Move the cursor to the selected definition."""
        sender = self.sender()
        item = sender.itemData(sender.currentIndex())

        if item:
            line = item['location']['range']['start']['line'] + 1
            self.editor.go_to_line(line)

        if sender == self.class_cb:
            self.method_cb.setCurrentIndex(0)

    def update_selected(self, linenum):
        """Updates the dropdowns to reflect the current class and function."""
        possible_parents = list(sorted(self._tree[linenum]))
        for iv in possible_parents:
            item = iv.data
            kind = item.get('kind')

            if kind in [SymbolKind.CLASS]:
                # Update class combobox
                for idx in range(self.class_cb.count()):
                    if self.class_cb.itemData(idx) == item:
                        self.class_cb.setCurrentIndex(idx)
                        break
                else:
                    self.class_cb.setCurrentIndex(0)
            elif kind in [SymbolKind.FUNCTION, SymbolKind.METHOD]:
                # Update func combobox
                for idx in range(self.method_cb.count()):
                    if self.method_cb.itemData(idx) == item:
                        self.method_cb.setCurrentIndex(idx)
                        break
                else:
                    self.method_cb.setCurrentIndex(0)
            else:
                continue

        if len(possible_parents) == 0:
            self.class_cb.setCurrentIndex(0)
            self.method_cb.setCurrentIndex(0)

    def populate(self, combobox, data, add_parents=False):
        """
        Populate the given ``combobox`` with the class or function names.

        Parameters
        ----------
        combobox : :class:`qtpy.QtWidgets.QComboBox`
            The combobox to populate
        data : list of :class:`dict`
            The data to populate with. There should be one list element per
            class or function defintion in the file.
        add_parents : bool
            Add parents to name to create a fully qualified name.

        Returns
        -------
        None
        """
        combobox.clear()
        combobox.addItem(_('<None>'), 0)
        model = combobox.model()
        item = model.item(0)
        item.setFlags(Qt.NoItemFlags)

        cb_data = []
        for item in data:
            fqn = item['name']

            # Create a list of fully-qualified names if requested
            if add_parents:
                begin = item['location']['range']['start']['line']
                end = item['location']['range']['end']['line']
                possible_parents = sorted(self._tree.overlap(begin, end),
                                          reverse=True)
                for iv in possible_parents:
                    if iv.begin == begin and iv.end == end:
                        continue

                    # Check if it is a real parent
                    p_item = iv.data
                    p_begin = p_item['location']['range']['start']['line']
                    p_end = p_item['location']['range']['end']['line']
                    if p_begin <= begin and p_end >= end:
                        fqn = p_item['name'] + "." + fqn

            cb_data.append((fqn, item))

        for fqn, item in cb_data:
            # Set the icon (See: editortools.py)
            icon = None
            name = item['name']
            if item['kind'] in [SymbolKind.CLASS]:
                icon = ima.icon('class')
            else:
                if name.startswith('__'):
                    icon = ima.icon('private2')
                elif name.startswith('_'):
                    icon = ima.icon('private1')
                else:
                    icon = ima.icon('method')

            # Add the combobox item
            if icon is not None:
                combobox.addItem(icon, fqn, item)
            else:
                combobox.addItem(fqn, item)

        line, column = self._editor.get_cursor_line_column()
        self.update_selected(line)

    def update_data(self, data):
        """Update and process symbol data."""
        if data == self._data:
            return

        self._data = data
        self._tree.clear()
        self.classes = []
        self.funcs = []

        for item in data:
            line_start = item['location']['range']['start']['line']
            line_end = item['location']['range']['end']['line']
            kind = item.get('kind')

            block = self._editor.document().findBlockByLineNumber(line_start)
            line_text = line_text = block.text() if block else ''

            # The symbol finder returns classes in import statements as well
            # so we filter them out
            if line_start != line_end and ' import ' not in line_text:
                self._tree[line_start:line_end] = item

                if kind in [SymbolKind.CLASS]:
                    self.classes.append(item)
                elif kind in [SymbolKind.FUNCTION, SymbolKind.METHOD]:
                    self.funcs.append(item)

        self.class_cb.clear()
        self.method_cb.clear()
        self.populate(self.class_cb, self.classes, add_parents=False)
        self.populate(self.method_cb, self.funcs, add_parents=True)
