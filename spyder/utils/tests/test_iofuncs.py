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

LOCATION = os.path.realpath(os.path.join(os.getcwd(),
                                         os.path.dirname(__file__)))


@pytest.fixture
def real_values():
    """
    Load a Numpy pickled file.

    The file numpy_data.npz contains six variables, each one represents the
    expected test values after a manual conversion of the same variables
    defined and evaluated in MATLAB. The manual type conversion was done
    over several variable types, such as: Matrices/Vectors, Scalar and
    Complex numbers, Structs, Strings and Cell Arrays. The set of variables
    was defined to allow and test the deep conversion of a compound type,
    i.e., a struct that contains other types that need to be converted,
    like other structs, matrices and Cell Arrays.
    """
    path = os.path.join(LOCATION, 'numpy_data.npz')
    file_s = np.load(path)
    A = file_s['A'].item()
    B = file_s['B']
    C = file_s['C']
    D = file_s['D'].item()
    E = file_s['E']
    return {'A':A, 'B':B, 'C':C, 'D':D, 'E':E}

def test_matlab_import(real_values):
    """
    Test the automatic conversion and import of variables from MATLAB.

    This test loads a file stored in MATLAB, the variables defined are
    equivalent to the manually converted values done over Numpy. This test
    allows to evaluate the function which processes the conversion automa-
    tically. i.e., The automatic conversion results should be equal to the
    manual conversion of the variables.
    """
    path = os.path.join(LOCATION, 'data.mat')
    inf, _ = io.load_matlab(path)
    valid = True
    for var in sorted(real_values.keys()):
        valid = valid and bool(np.mean(real_values[var] == inf[var]))
    assert valid
