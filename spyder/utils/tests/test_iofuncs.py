# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for iofuncs.py
"""

import os
import pytest
import numpy as np
import spyder.utils.iofuncs as io

__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))


@pytest.fixture
def real_values():
    path = os.path.join(__location__, 'numpy_data.npz')
    file_s = np.load(path)
    A = file_s['A'].item()
    B = file_s['B']
    C = file_s['C']
    D = file_s['D'].item()
    E = file_s['E']
    return {'A':A, 'B':B, 'C':C, 'D':D, 'E':E}

def test_matlab_import(real_values):
    path = os.path.join(__location__, 'data.mat')
    inf, _ = io.load_matlab(path)
    valid = True
    for var in sorted(real_values.keys()):
        valid = valid and np.sum(real_values[var] == inf[var])
    assert valid
