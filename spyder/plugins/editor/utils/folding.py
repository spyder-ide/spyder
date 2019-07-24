# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains some implementations of fold detectors.

Adapted from pyqode/core/api/folding.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/folding.py>
"""

# Standard library imports
import sys
import re

# Local imports
from spyder.plugins.editor.api.folding import FoldDetector
from spyder.plugins.editor.utils.editor import TextBlockHelper


class FoldScope(object):
    """
    Utility class for manipulating fold-able code scope (fold/unfold,
    get range, child and parent scopes and so on).

    A scope is built from a fold trigger (QTextBlock).
    """

    @property
    def trigger_level(self):
        """
        Returns the fold level of the block trigger.
        :return:
        """
        return TextBlockHelper.get_fold_lvl(self._trigger)

    @property
    def scope_level(self):
        """
        Returns the fold level of the first block of the foldable scope (
        just after the trigger).

        :return:
        """
        return TextBlockHelper.get_fold_lvl(self._trigger.next())

    @property
    def collapsed(self):
        """Returns True if the block is collasped, False if it is expanded."""
        return TextBlockHelper.is_collapsed(self._trigger)

    def __init__(self, block):
        """
        Create a fold-able region from a fold trigger block.

        :param block: The block **must** be a fold trigger.
        :type block: QTextBlock

        :raise: `ValueError` if the text block is not a fold trigger.
        """
        if not TextBlockHelper.is_fold_trigger(block):
            raise ValueError('Not a fold trigger')
        self._trigger = block

    def get_range(self, ignore_blank_lines=True):
        """
        Gets the fold region range (start and end line).

        .. note:: Start line do no encompass the trigger line.

        :param ignore_blank_lines: True to ignore blank lines at the end of the
            scope (the method will rewind to find that last meaningful block
            that is part of the fold scope).
        :returns: tuple(int, int)
        """
        ref_lvl = self.trigger_level
        first_line = self._trigger.blockNumber()
        block = self._trigger.next()
        last_line = block.blockNumber()
        lvl = self.scope_level
        if ref_lvl == lvl:  # for zone set programmatically such as imports
                            # in pyqode.python
            ref_lvl -= 1
        while (block.isValid() and
                TextBlockHelper.get_fold_lvl(block) > ref_lvl):
            last_line = block.blockNumber()
            block = block.next()

        if ignore_blank_lines and last_line:
            block = block.document().findBlockByNumber(last_line)
            while block.blockNumber() and block.text().strip() == '':
                block = block.previous()
                last_line = block.blockNumber()
        return first_line, last_line

    def fold(self):
        """Folds the region."""
        start, end = self.get_range()
        TextBlockHelper.set_collapsed(self._trigger, True)
        block = self._trigger.next()
        while block.blockNumber() <= end and block.isValid():
            block.setVisible(False)
            block = block.next()

    def unfold(self):
        """Unfolds the region."""
        # set all direct child blocks which are not triggers to be visible
        self._trigger.setVisible(True)
        TextBlockHelper.set_collapsed(self._trigger, False)
        for block in self.blocks(ignore_blank_lines=False):
            block.setVisible(True)
            if TextBlockHelper.is_fold_trigger(block):
                TextBlockHelper.set_collapsed(block, False)

    def blocks(self, ignore_blank_lines=True):
        """
        This generator generates the list of blocks directly under the fold
        region. This list does not contain blocks from child regions.

        :param ignore_blank_lines: True to ignore last blank lines.
        """
        start, end = self.get_range(ignore_blank_lines=ignore_blank_lines)
        block = self._trigger.next()
        while block.blockNumber() <= end and block.isValid():
            yield block
            block = block.next()

    def child_regions(self):
        """This generator generates the list of direct child regions."""
        start, end = self.get_range()
        block = self._trigger.next()
        ref_lvl = self.scope_level
        while block.blockNumber() <= end and block.isValid():
            lvl = TextBlockHelper.get_fold_lvl(block)
            trigger = TextBlockHelper.is_fold_trigger(block)
            if lvl == ref_lvl and trigger:
                yield FoldScope(block)
            block = block.next()

    def parent(self):
        """
        Return the parent scope.

        :return: FoldScope or None
        """
        if TextBlockHelper.get_fold_lvl(self._trigger) > 0 and \
                self._trigger.blockNumber():
            block = self._trigger.previous()
            ref_lvl = self.trigger_level - 1
            while (block.blockNumber() and
                    (not TextBlockHelper.is_fold_trigger(block) or
                     TextBlockHelper.get_fold_lvl(block) > ref_lvl)):
                block = block.previous()
            try:
                return FoldScope(block)
            except ValueError:
                return None
        return None

    def text(self, max_lines=sys.maxsize):
        """
        Get the scope text, with a possible maximum number of lines.

        :param max_lines: limit the number of lines returned to a maximum.
        :return: str
        """
        ret_val = []
        block = self._trigger.next()
        _, end = self.get_range()
        while (block.isValid() and block.blockNumber() <= end and
               len(ret_val) < max_lines):
            ret_val.append(block.text())
            block = block.next()
        return '\n'.join(ret_val)

    @staticmethod
    def find_parent_scope(block):
        """
        Find parent scope, if the block is not a fold trigger.

        :param block: block from which the research will start
        """
        # if we moved up for more than n lines, just give up otherwise this
        # would take too much time.
        limit = 5000
        counter = 0
        original = block
        if not TextBlockHelper.is_fold_trigger(block):
            # search level of next non blank line
            while block.text().strip() == '' and block.isValid():
                block = block.next()
            ref_lvl = TextBlockHelper.get_fold_lvl(block) - 1
            block = original
            while (block.blockNumber() and counter < limit and
                   (not TextBlockHelper.is_fold_trigger(block) or
                    TextBlockHelper.get_fold_lvl(block) > ref_lvl)):
                counter += 1
                block = block.previous()
        if counter < limit:
            return block
        return None

    def __repr__(self):
        return 'FoldScope(start=%r, end=%d)' % self.get_range()


class IndentFoldDetector(FoldDetector):
    """Simple fold detector based on the line indentation level."""

    def detect_fold_level(self, prev_block, block):
        """
        Detects fold level by looking at the block indentation.

        :param prev_block: previous text block
        :param block: current block to highlight
        """
        text = block.text()
        prev_lvl = TextBlockHelper().get_fold_lvl(prev_block)
        cont_line_regex = (r"(and|or|'|\+|\-|\*|\^|>>|<<|"
                           r"\*|\*{2}|\||\*|//|/|,|\\|\")$")
        # round down to previous indentation guide to ensure contiguous block
        # fold level evolution.
        indent_len = 0
        if (prev_lvl and prev_block is not None and
           not self.editor.is_comment(prev_block)):
            # ignore commented lines (could have arbitary indentation)
            prev_text = prev_block.text()
            indent_len = (len(prev_text) - len(prev_text.lstrip())) // prev_lvl
            # Verify if the previous line ends with a continuation line
            # with a regex
            if (re.search(cont_line_regex, prev_block.text()) and
                    indent_len > prev_lvl):
                # Calculate act level of line
                act_lvl = (len(text) - len(text.lstrip())) // indent_len
                if act_lvl == prev_lvl:
                    # If they are the same, don't change the level
                    return prev_lvl
                if prev_lvl > act_lvl:
                    return prev_lvl - 1
                return prev_lvl + 1
        if indent_len == 0:
            indent_len = len(self.editor.indent_chars)
        act_lvl = (len(text) - len(text.lstrip())) // indent_len
        return act_lvl


class CharBasedFoldDetector(FoldDetector):
    """
    Fold detector based on trigger charachters (e.g. a { increase fold level
    and } decrease fold level).
    """
    def __init__(self, open_chars=('{'), close_chars=('}')):
        super(CharBasedFoldDetector, self).__init__()
        self.open_chars = open_chars
        self.close_chars = close_chars

    def detect_fold_level(self, prev_block, block):
        if prev_block:
            prev_text = prev_block.text().strip()
        else:
            prev_text = ''
        text = block.text().strip()
        if text in self.open_chars:
            return TextBlockHelper.get_fold_lvl(prev_block) + 1
        if prev_text.endswith(self.open_chars) and prev_text not in \
                self.open_chars:
            return TextBlockHelper.get_fold_lvl(prev_block) + 1
        if self.close_chars in prev_text:
            return TextBlockHelper.get_fold_lvl(prev_block) - 1
        return TextBlockHelper.get_fold_lvl(prev_block)


if __name__ == '__main__':
    """Print folding blocks of this file for debugging"""
    from spyder.plugins.editor.api.folding import print_tree
    from spyder.utils.qthelpers import qapplication
    from spyder.plugins.editor.widgets.codeeditor import CodeEditor

    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = __file__

    app = qapplication()
    editor = CodeEditor(parent=None)
    editor.setup_editor(language='Python')

    editor.set_text_from_file(fname)

    print_tree(editor)
