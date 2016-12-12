"""
This module contains the code folding API.

"""
from __future__ import print_function
import logging
import sys
from pyqode.core.api.utils import TextBlockHelper


def print_tree(editor, file=sys.stdout, print_blocks=False):
    """
    Prints the editor fold tree to stdout, for debugging purpose.

    :param editor: CodeEdit instance.
    :param file: file handle where the tree will be printed. Default is stdout.
    :param print_blocks: True to print all blocks, False to only print blocks
        that are fold triggers
    """
    block = editor.document().firstBlock()
    while block.isValid():
        trigger = TextBlockHelper().is_fold_trigger(block)
        trigger_state = TextBlockHelper().is_collapsed(block)
        lvl = TextBlockHelper().get_fold_lvl(block)
        visible = 'V' if block.isVisible() else 'I'
        if trigger:
            trigger = '+' if trigger_state else '-'
            print('l%d:%s%s%s' %
                  (block.blockNumber() + 1, lvl, trigger, visible),
                  file=file)
        elif print_blocks:
            print('l%d:%s%s' %
                  (block.blockNumber() + 1, lvl, visible), file=file)
        block = block.next()


def _logger():
    return logging.getLogger(__name__)


class FoldDetector(object):
    """
    Base class for fold detectors.

    A fold detector takes care of detecting the text blocks fold levels that
    are used by the FoldingPanel to render the document outline.

    To use a FoldDetector, simply set it on a syntax_highlighter::

        editor.syntax_highlighter.fold_detector = my_fold_detector
    """
    @property
    def editor(self):
        if self._editor:
            return self._editor()
        return None

    def __init__(self):
        #: Reference to the parent editor, automatically set by the syntax
        #: highlighter before process any block.
        self._editor = None
        #: Fold level limit, any level greater or equal is skipped.
        #: Default is sys.maxsize (i.e. all levels are accepted)
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
        if text.strip() == '':
            # blank line always have the same level as the previous line
            fold_level = prev_fold_level
        else:
            fold_level = self.detect_fold_level(
                previous_block, current_block)
            if fold_level > self.limit:
                fold_level = self.limit

        prev_fold_level = TextBlockHelper.get_fold_lvl(previous_block)

        if fold_level > prev_fold_level:
            # apply on previous blank lines
            block = current_block.previous()
            while block.isValid() and block.text().strip() == '':
                TextBlockHelper.set_fold_lvl(block, fold_level)
                block = block.previous()
            TextBlockHelper.set_fold_trigger(
                block, True)

        # update block fold level
        if text.strip():
            TextBlockHelper.set_fold_trigger(
                previous_block, fold_level > prev_fold_level)
        TextBlockHelper.set_fold_lvl(current_block, fold_level)

        # user pressed enter at the beginning of a fold trigger line
        # the previous blank line will keep the trigger state and the new line
        # (which actually contains the trigger) must use the prev state (
        # and prev state must then be reset).
        prev = current_block.previous()  # real prev block (may be blank)
        if (prev and prev.isValid() and prev.text().strip() == '' and
                TextBlockHelper.is_fold_trigger(prev)):
            # prev line has the correct trigger fold state
            TextBlockHelper.set_collapsed(
                current_block, TextBlockHelper.is_collapsed(
                    prev))
            # make empty line not a trigger
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


class IndentFoldDetector(FoldDetector):
    """
    Simple fold detector based on the line indentation level
    """

    def detect_fold_level(self, prev_block, block):
        """
        Detects fold level by looking at the block indentation.

        :param prev_block: previous text block
        :param block: current block to highlight
        """
        text = block.text()
        # round down to previous indentation guide to ensure contiguous block
        # fold level evolution.
        return (len(text) - len(text.lstrip())) // self.editor.tab_length


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


class FoldScope(object):
    """
    Utility class for manipulating fold-able code scope (fold/unfold,
    get range, child and parent scopes and so on).

    A scope is built from a fold trigger (QTextBlock).
    """

    @property
    def trigger_level(self):
        """
        Returns the fold level of the block trigger
        :return:
        """
        return TextBlockHelper.get_fold_lvl(self._trigger)

    @property
    def scope_level(self):
        """
        Returns the fold level of the first block of the foldable scope (
        just after the trigger)

        :return:
        """
        return TextBlockHelper.get_fold_lvl(self._trigger.next())

    @property
    def collapsed(self):
        """
        Returns True if the block is collasped, False if it is expanded.

        """
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
        """
        Folds the region.
        """
        start, end = self.get_range()
        TextBlockHelper.set_collapsed(self._trigger, True)
        block = self._trigger.next()
        while block.blockNumber() <= end and block.isValid():
            block.setVisible(False)
            block = block.next()

    def unfold(self):
        """
        Unfolds the region.
        """
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
        """
        This generator generates the list of direct child regions.
        """
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
