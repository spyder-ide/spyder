# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for iofuncs.py
"""

import io
import os
import pytest
import numpy as np
import spyder.utils.iofuncs as iofuncs

LOCATION = os.path.realpath(os.path.join(os.getcwd(),
                                         os.path.dirname(__file__)))


@pytest.fixture
def spydata_values():
    """
    Define spydata file ground truth values.

    The file export_data.spydata contains five variables to be loaded.
    This fixture declares those variables in a static way.
    """
    A = 1
    B = 'ham'
    C = np.eye(3)
    D = {'a': True, 'b': np.eye(4, dtype=np.complex)}
    E = [np.eye(2, dtype=np.int64), 42.0, np.eye(3, dtype=np.bool_)]
    return {'A': A, 'B': B, 'C': C, 'D': D, 'E': E}

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

@pytest.mark.skipif(iofuncs.load_matlab is None, reason="SciPy required")
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
    inf, _ = iofuncs.load_matlab(path)
    valid = True
    for var in sorted(real_values.keys()):
        valid = valid and bool(np.mean(real_values[var] == inf[var]))
    assert valid


def test_spydata_import(spydata_values):
    """
    Test spydata handling and variable importing.

    This test loads all the variables contained inside a spydata tar
    container and compares them against their static values.
    """
    path = os.path.join(LOCATION, 'export_data.spydata')
    data, error = iofuncs.load_dictionary(path)
    assert error is None
    valid = True
    for var in sorted(spydata_values.keys()):
        try:
            valid = valid and bool(np.mean(spydata_values[var] == data[var]))
        except ValueError:
            valid = valid and all([np.all(obj1 == obj2) for obj1, obj2 in
                                   zip(spydata_values[var], data[var])])
    assert valid


@pytest.mark.skipif(iofuncs.load_matlab is None, reason="SciPy required")
def test_matlabstruct():
    """Test support for matlab stlye struct."""
    a = iofuncs.MatlabStruct()
    a.b = 'spam'
    assert a["b"] == 'spam'
    a.c["d"] = 'eggs'
    assert a.c.d == 'eggs'
    assert a == {'c': {'d': 'eggs'}, 'b': 'spam'}
    a['d'] = [1, 2, 3]

    buf = io.BytesIO()
    iofuncs.save_matlab(a, buf)
    buf.seek(0)
    data, error = iofuncs.load_matlab(buf)

    assert error is None
    assert data['b'] == 'spam'
    assert data['c'].d == 'eggs'
    assert data['d'].tolist() == [[1, 2, 3]]


def test_spydata_export(spydata_values):
    """
    Test spydata export and re-import.

    This test saves the variables in ``spydata`` format and then
    reloads and checks them to make sure they save/restore properly
    and no errors occur during the process.
    """
    path = os.path.join(LOCATION, 'export_data_copy.spydata')
    export_error = iofuncs.save_dictionary(spydata_values, path)
    assert export_error is None
    data, import_error = iofuncs.load_dictionary(path)
    assert import_error is None
    valid = True
    for var in sorted(spydata_values.keys()):
        try:
            valid = valid and bool(np.mean(spydata_values[var] == data[var]))
        except ValueError:
            valid = valid and all([np.all(obj1 == obj2) for obj1, obj2 in
                                   zip(spydata_values[var], data[var])])
    assert valid
    try:
        os.remove(path)
    except (IOError, OSError, PermissionError):
        pass


if __name__ == "__main__":
    pytest.main()
