# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2013-2016 Colin Duquesnoy and others (see pyqode/AUTHORS.rst)
# Copyright (c) 2016- Spyder Project Contributors (see AUTHORS.txt)
#
# Distributed under the terms of the MIT License
# (see NOTICE.txt in the Spyder root directory for details)
# -----------------------------------------------------------------------------

"""
This module contains the code folding API.

Adapted from pyqode/core/api/folding.py of the
`PyQode project <https://github.com/pyQode/pyQode>`_.
Original file:
<https://github.com/pyQode/pyqode.core/blob/master/pyqode/core/api/folding.py>
"""

# Future imports
from __future__ import print_function

# Standard library imports
import sys

# Local imports
from spyder.plugins.editor.utils.editor import TextBlockHelper


def print_tree(editor, file=sys.stdout, print_blocks=False, return_list=False):
    """
    Prints the editor fold tree to stdout, for debugging purpose.

    :param editor: CodeEditor instance.
    :param file: file handle where the tree will be printed. Default is stdout.
    :param print_blocks: True to print all blocks, False to only print blocks
        that are fold triggers
    """
    output_list = []

    block = editor.document().firstBlock()
    while block.isValid():
        lvl = TextBlockHelper().get_fold_lvl(block)
        visible = 'V' if block.isVisible() else 'I'
        if return_list:
            output_list.append([block.blockNumber() + 1, lvl, visible])
        else:
            print('l%d:%s%s' %
                  (block.blockNumber() + 1, lvl, visible),
                  file=file)
        block = block.next()

    if return_list:
        return output_list


class FoldDetector(object):
    """
    Base class for fold detectors.

    A fold detector takes care of detecting the text blocks fold levels that
    are used by the FoldingPanel to render the document outline.

    To use a FoldDetector, simply set it on a syntax_highlighter::

        editor.syntax_highlighter.fold_detector = my_fold_detector

    Some implementations of fold detectors can be found in:
    ``spyder/widgets/sourcecode/folding.py``.
    """
    @property
    def editor(self):
        if self._editor:
            return self._editor()
        return None

    def __init__(self):
        # Reference to the parent editor, automatically set by the syntax
        # highlighter before process any block.
        self._editor = None
        # Fold level limit, any level greater or equal is skipped.
        # Default is sys.maxsize (i.e. all levels are accepted)
        self.limit = sys.maxsize

    def process_block(self, current_block, previous_block, text):
        """
        Processes a block and setup its folding info.

        This method call ``detect_fold_level`` and handles most of the tricky
        corner cases so that all you have to do is focus on getting the proper
        fold level foreach meaningful block, skipping the blank ones.

        :param current_block: current block to process
        :param previous_block: previous block
        :param text: current block text
        """
        prev_fold_level = TextBlockHelper.get_fold_lvl(previous_block)
        if text.strip() == '' or self.editor.is_comment(current_block):
            # blank or comment line always have the same level
            # as the previous line
            fold_level = prev_fold_level
        else:
            fold_level = self.detect_fold_level(
                previous_block, current_block)
            if fold_level > self.limit:
                fold_level = self.limit
        prev_fold_level = TextBlockHelper.get_fold_lvl(previous_block)

        if fold_level > prev_fold_level:
            # apply on previous blank or comment lines
            block = current_block.previous()
            while block.isValid() and (block.text().strip() == ''
                                       or self.editor.is_comment(block)):
                TextBlockHelper.set_fold_lvl(block, fold_level)
                block = block.previous()
            TextBlockHelper.set_fold_trigger(
                block, True)
        # update block fold level
        if text.strip() and not self.editor.is_comment(previous_block):
            TextBlockHelper.set_fold_trigger(
                previous_block, fold_level > prev_fold_level)
        TextBlockHelper.set_fold_lvl(current_block, fold_level)
        # user pressed enter at the beginning of a fold trigger line
        # the previous blank or comment line will keep the trigger state
        # and the new line (which actually contains the trigger) must use
        # the prev state (and prev state must then be reset).
        prev = current_block.previous()  # real prev block (may be blank)
        if (prev and prev.isValid() and
            (prev.text().strip() == '' or self.editor.is_comment(prev)) and
                TextBlockHelper.is_fold_trigger(prev)):
            # prev line has the correct trigger fold state
            TextBlockHelper.set_collapsed(
                current_block, TextBlockHelper.is_collapsed(
                    prev))
            # make empty or comment line not a trigger
            TextBlockHelper.set_fold_trigger(prev, False)
            TextBlockHelper.set_collapsed(prev, False)

    def detect_fold_level(self, prev_block, block):
        """
        Detects the block fold level.

        The default implementation is based on the block **indentation**.

        .. note:: Blocks fold level must be contiguous, there cannot be
            a difference greater than 1 between two successive block fold
            levels.

        :param prev_block: first previous **non-blank** block or None if this
            is the first line of the document
        :param block: The block to process.
        :return: Fold level
        """
        raise NotImplementedError
