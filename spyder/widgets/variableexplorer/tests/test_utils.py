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


if __name__ == "__main__":
    pytest.main()
