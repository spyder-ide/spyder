# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for profiler.py
"""


# Third party imports
import pytest

# Local imports
from spyder.plugins.profiler.widgets.profiler_data_tree import TreeWidgetItem
from spyder.utils.palette import SpyderPalette


ERROR = SpyderPalette.COLOR_ERROR_1
SUCESS = SpyderPalette.COLOR_SUCCESS_1


# --- Tests
# -----------------------------------------------------------------------------
def test_format_measure():
    """ Test ProfilerDataTree.format_measure()."""
    fm = TreeWidgetItem.format_measure
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


def test_color_string():
    """ Test ProfilerDataTree.color_diff()."""
    cs = TreeWidgetItem.color_diff
    assert cs(0.) == ('', 'black')
    assert cs(1.) == ('+1000.00 ms', ERROR)
    assert cs(-1.) == ('-1000.00 ms', SUCESS)
    assert cs(0) == ('', 'black')
    assert cs(1) == ('+1', ERROR)
    assert cs(-1) == ('-1', SUCESS)


if __name__ == "__main__":
    pytest.main()
