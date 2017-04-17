# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget based on QtGui.QPlainTextEdit
"""
import operator
import copy

from spyder.widgets.sourcecode.folding import FoldScope
from spyder.utils.editor import TextBlockHelper
from spyder.utils.syntaxhighlighters import OutlineExplorerData as OED
from spyder.utils import icon_manager as ima


DUMMY_OED = OED()
DUMMY_OED.fold_level = 0
DUMMY_OED.text = "<None>"


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
    editor :

    Returns
    -------
    folds : list of :class:`FoldScopeHelper`
        A list of all the class or function defintion fold points.
    """
    block = editor.document().firstBlock()
    oed = editor.get_outlineexplorer_data()

    folds = []
    parents = []
    prev = None

    while block.isValid():
        if TextBlockHelper.is_fold_trigger(block):
            try:
                data = oed[block.firstLineNumber()]

                if data.def_type in (OED.CLASS, OED.FUNCTION):
                    fsh = FoldScopeHelper(FoldScope(block), data)

                    # Determine the parents of the item using a stack.
                    _adjust_parent_stack(fsh, prev, parents)

                    # Update the parents of this FoldScopeHelper item
                    fsh.parents = copy.copy(parents)
                    folds.append(fsh)
                    prev = fsh
            except KeyError:
                pass

        block = block.next()

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


class FoldScopeHelper(object):
    """

    Parameters
    ----------
    fold_scope : :class:`spyder.widgets.sourcecode.folding.FoldScope`
    oed : :class:`spyder.utils.syntaxhighlighters.OutlineExplorerData`
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
