# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for profiler.py
"""


# Third party imports
from qtpy.QtGui import QIcon
import pytest

# Local imports
from spyder.plugins.profiler.widgets.main_widget import ProfilerDataTree
from spyder.utils.palette import SpyderPalette


ERROR = SpyderPalette.COLOR_ERROR_1
SUCESS = SpyderPalette.COLOR_SUCCESS_1


# --- Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def profiler_datatree_bot(qtbot):
    """Set up Profiler widget."""
    # Avoid qtawesome startup errors
    ProfilerDataTree.create_icon = lambda x, y: QIcon()
    tree = ProfilerDataTree(None)
    qtbot.addWidget(tree)
    tree.show()
    yield tree
    tree.destroy()


# --- Tests
# -----------------------------------------------------------------------------
def test_format_measure(profiler_datatree_bot):
    """ Test ProfilerDataTree.format_measure()."""
    tree = profiler_datatree_bot
    fm = tree.format_measure
    assert fm(125) == '125'
    assert fm(1.25e-8) == '12.50 ns'
    assert fm(1.25e-5) == u'12.50 \u03BCs'
    assert fm(1.25e-2) == '12.50 ms'
    assert fm(12.5) == '12.50 s'
    assert fm(125.5) == '2.5 min'
    assert fm(12555.5) == '3h:29min'

    assert fm(-125) == '125'
    assert fm(-1.25e-8) == '12.50 ns'
    assert fm(-1.25e-5) == u'12.50 \u03BCs'
    assert fm(-1.25e-2) == '12.50 ms'
    assert fm(-12.5) == '12.50 s'
    assert fm(-125.5) == '2.5 min'
    assert fm(-12555.5) == '3h:29min'


def test_color_string(profiler_datatree_bot):
    """ Test ProfilerDataTree.color_string()."""
    tree = profiler_datatree_bot
    cs = tree.color_string

    tree.compare_file = 'test'
    assert cs([5.0]) == ['5.00 s', ['', 'black']]
    assert cs([1.251e-5, 1.251e-5]) == [u'12.51 \u03BCs', ['', 'black']]
    assert cs([5.0, 4.0]) == ['5.00 s', ['+1000.00 ms', ERROR]]
    assert cs([4.0, 5.0]) == ['4.00 s', ['-1000.00 ms', SUCESS]]

    tree.compare_file = None
    assert cs([4.0, 5.0]) == ['4.00 s', ['', 'black']]


def test_format_output(profiler_datatree_bot):
    """ Test ProfilerDataTree.format_output()."""
    tree = profiler_datatree_bot
    fo = tree.format_output

    # Mock Stats class to be able to use fixed data for input.
    class Stats:
        stats = {}

    tree.stats1 = [Stats(), Stats()]
    tree.stats1[0].stats = {('key1'): (1, 1000, 3.5, 1.5, {}),
                            ('key2'): (1, 1200, 2.0, 2.0, {})
                            }
    tree.stats1[1].stats = {('key1'): (1, 1000, 3.7, 1.3, {}),
                            ('key2'): (1, 1199, 2.4, 2.4, {})
                            }

    tree.compare_file = 'test'
    assert list((fo('key1'))) == [['1000', ['', 'black']],
                                  ['3.50 s', ['-200.00 ms', SUCESS]],
                                  ['1.50 s', ['+200.00 ms', ERROR]]]
    assert list((fo('key2'))) == [['1200', ['+1', ERROR]],
                                  ['2.00 s', ['-400.00 ms', SUCESS]],
                                  ['2.00 s', ['-400.00 ms', SUCESS]]]


if __name__ == "__main__":
    pytest.main()
