# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor widget based on QtGui.QPlainTextEdit
"""
from spyder.utils.syntaxhighlighters import OutlineExplorerData as OED


DUMMY_OED = OED()
DUMMY_OED.fold_level = 0
DUMMY_OED.text = "<None>"


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
