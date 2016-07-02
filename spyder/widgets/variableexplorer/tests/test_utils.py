# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License

"""
Tests for utils.py
"""

# Third party imports
import pytest

# Local imports
from spyder.widgets.variableexplorer.utils import sort_against


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
    

if __name__ == "__main__":
    pytest.main()
