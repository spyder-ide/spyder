# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for iofuncs.py
"""

import pytest
import numpy as np
import spyder.utils.iofuncs as io

@pytest.fixture
def real_values():
    file_s = np.load('numpy_data.npz')
    A = file_s['A'].item()
    B = file_s['B']
    C = file_s['C']
    D = file_s['D'].item()
    E = file_s['E']
    return {'A':A, 'B':B, 'C':C, 'D':D, 'E':E}

def test_matlab_import(real_values):
    inf = io.load_matlab('data.mat')[0]
    valid = True
    for var in sorted(real_values.keys()):
        valid = valid and np.sum(real_values[var] == inf[var])
    assert valid
