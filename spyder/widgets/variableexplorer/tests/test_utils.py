# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for utils.py
"""

from collections import defaultdict

# Third party imports
import numpy as np
import pandas as pd
import pytest

# Local imports
from spyder.config.base import get_supported_types
from spyder.widgets.variableexplorer.utils import (sort_against,
    is_supported, value_to_display)


def generate_complex_object():
    """Taken from issue #4221."""
    bug = defaultdict(list)
    for i in range(50000):
        a = {j:np.random.rand(10) for j in range(10)}
        bug[i] = a
    return bug


COMPLEX_OBJECT = generate_complex_object()
DF = pd.DataFrame([1,2,3])
PANEL = pd.Panel({0: pd.DataFrame([1,2]), 1:pd.DataFrame([3,4])})


# --- Tests
# -----------------------------------------------------------------------------
def test_sort_against():
    lista = [5, 6, 7]
    listb = [2, 3, 1]
    res = sort_against(lista, listb)
    assert res == [7, 5, 6]


def test_sort_against_is_stable():
    lista = [3, 0, 1]
    listb = [1, 1, 1]
    res = sort_against(lista, listb)
    assert res == lista


def test_none_values_are_supported():
    """Tests that None values are displayed by default"""
    supported_types = get_supported_types()
    mode = 'editable'
    none_var = None
    none_list = [2, None, 3, None]
    none_dict = {'a': None, 'b': 4}
    none_tuple = (None, [3, None, 4], 'eggs')
    assert is_supported(none_var, filters=tuple(supported_types[mode]))
    assert is_supported(none_list, filters=tuple(supported_types[mode]))
    assert is_supported(none_dict, filters=tuple(supported_types[mode]))
    assert is_supported(none_tuple, filters=tuple(supported_types[mode]))


def test_default_display():
    """Tests for default_display."""
    # Display of defaultdict
    assert (value_to_display(COMPLEX_OBJECT) ==
            'defaultdict object of collections module')

    # Display of array of COMPLEX_OBJECT
    assert (value_to_display(np.array(COMPLEX_OBJECT)) ==
            'ndarray object of numpy module')

    # Display of Panel
    assert (value_to_display(PANEL) ==
            'Panel object of pandas.core.panel module')


def test_list_display():
    """Tests for display of lists."""
    long_list = list(range(100))

    # Simple list
    assert value_to_display([1, 2, 3]) == '[1, 2, 3]'

    # Long list
    assert (value_to_display(long_list) ==
            '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...]')

    # Short list of lists
    assert (value_to_display([long_list] * 3) ==
            '[[0, 1, 2, 3, 4, ...], [0, 1, 2, 3, 4, ...], [0, 1, 2, 3, 4, ...]]')

    # Long list of lists
    result = '[' + ''.join('[0, 1, 2, 3, 4, ...], '*10)[:-2] + ']'
    assert value_to_display([long_list] * 10) == result[:70] + ' ...'

    # Multiple level lists
    assert (value_to_display([[1, 2, 3, [4], 5]] + long_list) ==
            '[[1, 2, 3, [...], 5], 0, 1, 2, 3, 4, 5, 6, 7, 8, ...]')
    assert value_to_display([1, 2, [DF]]) == '[1, 2, [Dataframe]]'
    assert value_to_display([1, 2, [[DF], PANEL]]) == '[1, 2, [[...], Panel]]'

    # List of complex object
    assert value_to_display([COMPLEX_OBJECT]) == '[defaultdict]'

    # List of composed objects
    li = [COMPLEX_OBJECT, PANEL, 1, {1:2, 3:4}, DF]
    result = '[defaultdict, Panel, 1, {1:2, 3:4}, Dataframe]'
    assert value_to_display(li) == result


def test_dict_display():
    """Tests for display of dicts."""
    long_list = list(range(100))
    long_dict = dict(zip(list(range(100)), list(range(100))))

    # Simple dict
    assert value_to_display({0:0, 'a':'b'}) == "{0:0, 'a':'b'}"

    # Long dict
    assert (value_to_display(long_dict) ==
            '{0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, ...}')

    # Short list of lists
    assert (value_to_display({1:long_dict, 2:long_dict}) ==
            '{1:{0:0, 1:1, 2:2, 3:3, 4:4, ...}, 2:{0:0, 1:1, 2:2, 3:3, 4:4, ...}}')

    # Long dict of dicts
    result = ('{(0, 0, 0, 0, 0, ...):[0, 1, 2, 3, 4, ...], '
               '(1, 1, 1, 1, 1, ...):[0, 1, 2, 3, 4, ...]}')
    assert value_to_display({(0,)*100:long_list, (1,)*100:long_list}) == result[:70] + ' ...'

    # Multiple level dicts
    assert (value_to_display({0: {1:1, 2:2, 3:3, 4:{0:0}, 5:5}, 1:1}) ==
            '{0:{1:1, 2:2, 3:3, 4:{...}, 5:5}, 1:1}')
    assert value_to_display({0:0, 1:1, 2:2, 3:DF}) == '{0:0, 1:1, 2:2, 3:Dataframe}'
    assert value_to_display({0:0, 1:1, 2:[[DF], PANEL]}) == '{0:0, 1:1, 2:[[...], Panel]}'

    # Dict of complex object
    assert value_to_display({0:COMPLEX_OBJECT}) == '{0:defaultdict}'

    # Dict of composed objects
    li = {0:COMPLEX_OBJECT, 1:PANEL, 2:2, 3:{0:0, 1:1}, 4:DF}
    result = '{0:defaultdict, 1:Panel, 2:2, 3:{0:0, 1:1}, 4:Dataframe}'
    assert value_to_display(li) == result


if __name__ == "__main__":
    pytest.main()
