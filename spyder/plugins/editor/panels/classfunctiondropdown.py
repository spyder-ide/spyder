# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
A Class and Function Dropdown Panel for Spyder.

To demo this panel, run spyder/widgets/sourcecode/codeeditor.py
"""
import operator
import copy

from qtpy.QtWidgets import QComboBox, QHBoxLayout

from qtpy.QtCore import Slot
from qtpy.QtCore import QSize

from spyder.api.panel import Panel
from spyder.plugins.editor.utils.folding import FoldScope
from spyder.plugins.editor.utils.editor import TextBlockHelper
from spyder.plugins.outlineexplorer.api import OutlineExplorerData as OED
from spyder.utils import icon_manager as ima


def populate(combobox, data):
    """
    Populate the given ``combobox`` with the class or function names.

    Parameters
    ----------
    combobox : :class:`qtpy.QtWidets.QComboBox`
        The combobox to populate
    data : list of :class:`FoldScopeHelper`
        The data to populate with. There should be one list element per
        class or function defintion in the file.

    Returns
    -------
    None
    """
    combobox.clear()
    combobox.addItem("<None>", 0)

    # First create a list of fully-qualified names.
    cb_data = []
    for item in data:
        fqn = item.name
        for parent in reversed(item.parents):
            fqn = parent.name + "." + fqn

        cb_data.append((fqn, item))

    for fqn, item in sorted(cb_data, key=operator.itemgetter(0)):
        # Set the icon. Just threw this in here, streight from editortools.py
        icon = None
        if item.def_type == OED.FUNCTION_TOKEN:
            if item.name.startswith('__'):
                icon = ima.icon('private2')
            elif item.name.startswith('_'):
                icon = ima.icon('private1')
            else:
                icon = ima.icon('method')
        else:
            icon = ima.icon('class')

        # Add the combobox item
        if icon is not None:
            combobox.addItem(icon, fqn, item)
        else:
            combobox.addItem(fqn, item)


def _get_fold_levels(editor):
    """
    Return a list of all the class/function definition ranges.

    Parameters
    ----------
    editor : :class:`spyder.plugins.editor.widgets.codeeditor.CodeEditor`

    Returns
    -------
    folds : list of :class:`FoldScopeHelper`
        A list of all the class or function defintion fold points.
    """


    folds = []
    parents = []
    prev = None

    for oedata in editor.outlineexplorer_data_list():
        if TextBlockHelper.is_fold_trigger(oedata.block):
            try:
                if oedata.def_type in (OED.CLASS, OED.FUNCTION):
                    fsh = FoldScopeHelper(FoldScope(oedata.block), oedata)

                    # Determine the parents of the item using a stack.
                    _adjust_parent_stack(fsh, prev, parents)

                    # Update the parents of this FoldScopeHelper item
                    fsh.parents = copy.copy(parents)
                    folds.append(fsh)
                    prev = fsh
            except KeyError:
                pass
    return folds


def _adjust_parent_stack(fsh, prev, parents):
    """
    Adjust the parent stack in-place as the trigger level changes.

    Parameters
    ----------
    fsh : :class:`FoldScopeHelper`
        The :class:`FoldScopeHelper` object to act on.
    prev : :class:`FoldScopeHelper`
        The previous :class:`FoldScopeHelper` object.
    parents : list of :class:`FoldScopeHelper`
        The current list of parent objects.

    Returns
    -------
    None
    """
    if prev is None:
        return

    if fsh.fold_scope.trigger_level < prev.fold_scope.trigger_level:
        diff = prev.fold_scope.trigger_level - fsh.fold_scope.trigger_level
        del parents[-diff:]
    elif fsh.fold_scope.trigger_level > prev.fold_scope.trigger_level:
        parents.append(prev)
    elif fsh.fold_scope.trigger_level == prev.fold_scope.trigger_level:
        pass


def _split_classes_and_methods(folds):
    """
    Split out classes and methods into two separate lists.

    Parameters
    ----------
    folds : list of :class:`FoldScopeHelper`
        The result of :func:`_get_fold_levels`.

    Returns
    -------
    classes, functions: list of :class:`FoldScopeHelper`
        Two separate lists of :class:`FoldScopeHelper` objects. The former
        contains only class definitions while the latter contains only
        function/method definitions.
    """
    classes = []
    functions = []
    for fold in folds:
        if fold.def_type == OED.FUNCTION_TOKEN:
            functions.append(fold)
        elif fold.def_type == OED.CLASS_TOKEN:
            classes.append(fold)

    return classes, functions


def _get_parents(folds, linenum):
    """
    Get the parents at a given linenum.

    If parents is empty, then the linenum belongs to the module.

    Parameters
    ----------
    folds : list of :class:`FoldScopeHelper`
    linenum : int
        The line number to get parents for. Typically this would be the
        cursor position.

    Returns
    -------
    parents : list of :class:`FoldScopeHelper`
        A list of :class:`FoldScopeHelper` objects that describe the defintion
        heirarcy for the given ``linenum``. The 1st index will be the
        top-level parent defined at the module level while the last index
        will be the class or funtion that contains ``linenum``.
    """
    # Note: this might be able to be sped up by finding some kind of
    # abort-early condition.
    parents = []
    for fold in folds:
        start, end = fold.range
        if linenum >= start and linenum <= end:
            parents.append(fold)
        else:
            continue

    return parents


def update_selected_cb(parents, combobox):
    """
    Update the combobox with the selected item based on the parents.

    Parameters
    ----------
    parents : list of :class:`FoldScopeHelper`
    combobox : :class:`qtpy.QtWidets.QComboBox`
        The combobox to populate

    Returns
    -------
    None
    """
    if parents is not None and len(parents) == 0:
        combobox.setCurrentIndex(0)
    else:
        item = parents[-1]
        for i in range(combobox.count()):
            if combobox.itemData(i) == item:
                combobox.setCurrentIndex(i)
                break


class FoldScopeHelper(object):
    """
    This is a helper class to make using FoldScope easier.

    It is a wrapper around a FoldScope object and an OutlineExplorerData
    object, raises certain attributes to this level, and gives them more
    descriptive names.

    It defines some nicely-formatted ``str`` and ``repr`` and allows
    for easy tracking of the parents of a given FoldScope.

    Parameters
    ----------
    fold_scope : :class:`spyder.plugins.editor.utils.folding.FoldScope`
    oed : :class:`spyder.plugins.outlineexplorer.api.OutlineExplorerData`

    Properties
    ----------
    parents : list of :class:`FoldScopeHelper`
        The parents of this ``FoldScopeHelper`` object. The 1st index will
        be the top-level parent defined at the module level while the
        last index will be the class or funtion that contains this object.
    """

    def __init__(self, fold_scope, oed):
        self._fold_scope = fold_scope
        self._oed = oed
        self.parents = []

    def __str__(self):
        fmt = "<{}: {} {} at line {}>"
        if self.parents:        # is not None or is not empty list.
            fmt = "<{}: {} {} at line {}, parents: {}>"
            return fmt.format(self.__class__.__name__,
                              self.def_type.upper(),
                              self.name,
                              self.line,
                              self.parents,
                              )
        return fmt.format(self.__class__.__name__,
                          self.def_type.upper(),
                          self.name,
                          self.line,
                          )

    def __repr__(self):
        fmt = "<{} object {} '{}', line {} (at {:#x})>"
        return fmt.format(self.__class__.__name__,
                          self.def_type.upper(),
                          self.name,
                          self.line,
                          id(self))

    @property
    def fold_scope(self):
        return self._fold_scope

    @property
    def range(self):
        return self.fold_scope.get_range()

    @property
    def start_line(self):
        return self.range[0]

    @property
    def end_line(self):
        return self.range[1]

    @property
    def oed(self):
        return self._oed

    @property
    def name(self):
        return self.oed.def_name

    @property
    def line(self):
        return self.start_line

    @property
    def def_type(self):
        if self.oed.def_type == OED.FUNCTION:
            return OED.FUNCTION_TOKEN
        elif self.oed.def_type == OED.CLASS:
            return OED.CLASS_TOKEN
        else:
            return "Unknown"


class ClassFunctionDropdown(Panel):
    """
    Class and Function/Method Dropdowns Widget.

    Parameters
    ----------
    editor : :class:`spyder.plugins.editor.widgets.codeeditor.CodeEditor`
        The editor to act on.
    """

    def __init__(self, editor):
        Panel.__init__(self, editor)
        self._editor = editor
        self._editor.sig_cursor_position_changed.connect(
            self._handle_cursor_position_change_event
        )

        # The layout
        hbox = QHBoxLayout()
        self.class_cb = QComboBox()
        self.method_cb = QComboBox()
        hbox.addWidget(self.class_cb)
        hbox.addWidget(self.method_cb)
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.setLayout(hbox)

        # Internal data
        self.folds = None
        self.parents = None
        self.classes = None
        self.funcs = None

        # Initial data for the dropdowns.
        self.class_cb.addItem("<None>", 0)
        self.method_cb.addItem("<None>", 0)

        # Attach some events.
        self.class_cb.activated.connect(self.combobox_activated)
        self.method_cb.activated.connect(self.combobox_activated)

    def sizeHint(self):
        """Override Qt method."""
        return QSize(0, self._getVerticalSize())

    def _getVerticalSize(self):
        """Get the default height of a QComboBox."""
        return self.class_cb.height()

    def _update_data(self):
        """Update the internal data values."""
        _old = self.folds
        self.folds = _get_fold_levels(self.editor)

        # only update our dropdown lists if the folds have changed.
        if self.folds != _old:
            self.classes, self.funcs = _split_classes_and_methods(self.folds)
            self.populate_dropdowns()

    def populate_dropdowns(self):
        self.class_cb.clear()
        self.method_cb.clear()

        populate(self.class_cb, self.classes)
        populate(self.method_cb, self.funcs)

    def combobox_activated(self):
        """Move the cursor to the selected definition."""
        sender = self.sender()
        data = sender.itemData(sender.currentIndex())

        if isinstance(data, FoldScopeHelper):
            self.editor.go_to_line(data.line + 1)

    def update_selected(self, linenum):
        """Updates the dropdowns to reflect the current class and function."""
        self.parents = _get_parents(self.funcs, linenum)
        update_selected_cb(self.parents, self.method_cb)

        self.parents = _get_parents(self.classes, linenum)
        update_selected_cb(self.parents, self.class_cb)

    @Slot(int, int)
    def _handle_cursor_position_change_event(self, linenum, column):
        self._update_data()
        self.update_selected(linenum)
