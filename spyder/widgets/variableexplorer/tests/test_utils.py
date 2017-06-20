# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for utils.py
"""

# Third party imports
import pytest

# Local imports
from spyder.config.base import get_supported_types
from spyder.widgets.variableexplorer.utils import sort_against, is_supported


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
    # None values should be displayed by default
    supported_types = get_supported_types()
    mode = 'editable'
    none_var = None
    none_list = [2, None, 3, None]
    assert is_supported(none_var, filters=tuple(supported_types[mode]))
    assert is_supported(none_list, filters=tuple(supported_types[mode]))


if __name__ == "__main__":
    pytest.main()
