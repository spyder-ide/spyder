# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for iofuncs.py.
"""

# Standard library imports
import io
import os
import copy

# Third party imports
import pytest
import numpy as np

# Local imports
import spyder_kernels.utils.iofuncs as iofuncs
from spyder_kernels.py3compat import is_text_string, PY2


# Full path to this file's parent directory for loading data
LOCATION = os.path.realpath(os.path.join(os.getcwd(),
                                         os.path.dirname(__file__)))


# =============================================================================
# ---- Helper functions and classes
# =============================================================================
def are_namespaces_equal(actual, expected):
    if actual is None and expected is None:
        return True
    are_equal = True
    for var in sorted(expected.keys()):
        try:
            are_equal = are_equal and bool(np.mean(
                expected[var] == actual[var]))
        except ValueError:
            are_equal = are_equal and all(
                [np.all(obj1 == obj2) for obj1, obj2 in zip(expected[var],
                                                            actual[var])])
        print(str(var) + ": " + str(are_equal))
    return are_equal


class CustomObj(object):
    """A custom class of objects for testing."""
    def __init__(self, data):
        self.data = None
        if data:
            self.data = data

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class UnDeepCopyableObj(CustomObj):
    """A class of objects that cannot be deepcopied."""
    def __getstate__(self):
        raise RuntimeError()


class UnPickleableObj(UnDeepCopyableObj):
    """A class of objects that can deepcopied, but not pickled."""
    def __deepcopy__(self, memo):
        new_one = self.__class__.__new__(self.__class__)
        new_one.__dict__.update(self.__dict__)
        return new_one


# =============================================================================
# ---- Fixtures
# =============================================================================
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
    D = {'a': True, 'b': np.eye(4, dtype=np.complex128)}
    E = [np.eye(2, dtype=np.int64), 42.0, np.eye(3, dtype=np.bool_), np.eye(4, dtype=object)]
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
    file_s = np.load(path, allow_pickle=True)
    A = file_s['A'].item()
    B = file_s['B']
    C = file_s['C']
    D = file_s['D'].item()
    E = file_s['E']
    return {'A': A, 'B': B, 'C': C, 'D': D, 'E': E}


@pytest.fixture
def namespace_objects_full(spydata_values):
    """
    Define a dictionary of objects of a variety of different types to be saved.

    This fixture reprisents the state of the namespace before saving and
    filtering out un-deep-copyable, un-pickleable, and uninteresting objects.
    """
    namespace_dict = copy.deepcopy(spydata_values)
    namespace_dict['expected_error_string'] = (
        'Some objects could not be saved: '
        'undeepcopyable_instance, unpickleable_instance')
    namespace_dict['module_obj'] = io
    namespace_dict['class_obj'] = Exception
    namespace_dict['function_obj'] = os.path.join
    namespace_dict['unpickleable_instance'] = UnPickleableObj("spam")
    namespace_dict['undeepcopyable_instance'] = UnDeepCopyableObj("ham")
    namespace_dict['custom_instance'] = CustomObj("eggs")

    return namespace_dict


@pytest.fixture
def namespace_objects_filtered(spydata_values):
    """
    Define a dictionary of the objects from the namespace that can be saved.

    This fixture reprisents the state of the namespace after saving and
    filtering out un-deep-copyable, un-pickleable, and uninteresting objects.
    """
    namespace_dict = copy.deepcopy(spydata_values)
    namespace_dict['custom_instance'] = CustomObj("eggs")

    return namespace_dict


@pytest.fixture
def namespace_objects_nocopyable():
    """
    Define a dictionary of that cannot be deepcopied.
    """
    namespace_dict = {}
    namespace_dict['expected_error_string'] = 'No supported objects to save'
    namespace_dict['class_obj'] = Exception
    namespace_dict['undeepcopyable_instance'] = UnDeepCopyableObj("ham")

    return namespace_dict


@pytest.fixture
def namespace_objects_nopickleable():
    """
    Define a dictionary of objects that cannot be pickled.
    """
    namespace_dict = {}
    namespace_dict['expected_error_string'] = 'No supported objects to save'
    namespace_dict['function_obj'] = os.path.join
    namespace_dict['unpickleable_instance'] = UnPickleableObj("spam")

    return namespace_dict


@pytest.fixture
def input_namespace(request):
    if request.param is None:
        return None
    else:
        return request.getfixturevalue(request.param)


@pytest.fixture
def expected_namespace(request):
    if request.param is None:
        return None
    else:
        return request.getfixturevalue(request.param)


# =============================================================================
# ---- Tests
# =============================================================================
def test_npz_import():
    """
    Test the load of .npz files as dictionaries.
    """
    filename = os.path.join(LOCATION, 'import_data.npz')
    data = iofuncs.load_array(filename)
    assert isinstance(data, tuple)
    variables, error = data
    assert variables['val1'] == np.array(1) and not error


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


@pytest.mark.skipif(PY2, reason="Fails on Python 2")
@pytest.mark.parametrize('spydata_file_name', ['export_data.spydata',
                                               'export_data_renamed.spydata'])
def test_spydata_import(spydata_file_name, spydata_values):
    """
    Test spydata handling and variable importing.

    This test loads all the variables contained inside a spydata tar
    container and compares them against their static values.
    It tests both a file with the original name, and one that has been renamed
    in order to catch Issue #9 .
    """
    path = os.path.join(LOCATION, spydata_file_name)
    data, error = iofuncs.load_dictionary(path)
    assert error is None
    assert are_namespaces_equal(data, spydata_values)


def test_spydata_import_witherror():
    """
    Test that import fails gracefully with a fn not present in the namespace.

    Checks that the error is caught, the message is passed back,
    and the current working directory is restored afterwards.
    """
    original_cwd = os.getcwd()
    path = os.path.join(LOCATION, 'export_data_withfunction.spydata')
    data, error = iofuncs.load_dictionary(path)
    assert error and is_text_string(error)
    assert data is None
    assert os.getcwd() == original_cwd


def test_spydata_import_missing_file():
    """
    Test that import fails properly when file is missing, and resets the cwd.
    """
    original_cwd = os.getcwd()
    path = os.path.join(LOCATION, 'non_existant_path_2019-01-23.spydata')
    try:
        iofuncs.load_dictionary(path)
    except IOError:
        pass
    else:
        # Fail if exception did not occur when it should
        assert False
    assert os.getcwd() == original_cwd


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


@pytest.mark.parametrize('input_namespace,expected_namespace,filename', [
    ('spydata_values', 'spydata_values', 'export_data_copy'),
    ('namespace_objects_full', 'namespace_objects_filtered', 'export_data_2'),
    ('namespace_objects_nocopyable', None, 'export_data_none_1'),
    ('namespace_objects_nopickleable', None, 'export_data_none_2'),
    ], indirect=['input_namespace', 'expected_namespace'])
def test_spydata_export(input_namespace, expected_namespace,
                        filename):
    """
    Test spydata export and re-import.

    This test saves the variables in ``spydata`` format and then
    reloads and checks them to make sure they save/restore properly
    and no errors occur during the process.
    """
    path = os.path.join(LOCATION, filename + '.spydata')
    expected_error = None
    if 'expected_error_string' in input_namespace:
        expected_error = input_namespace['expected_error_string']
        del input_namespace['expected_error_string']
    cwd_original = os.getcwd()

    try:
        export_error = iofuncs.save_dictionary(input_namespace, path)
        assert export_error == expected_error
        if expected_namespace is None:
            assert not os.path.isfile(path)
        else:
            data_actual, import_error = iofuncs.load_dictionary(path)
            assert import_error is None
            print(data_actual.keys())
            print(expected_namespace.keys())
            assert are_namespaces_equal(data_actual, expected_namespace)
        assert cwd_original == os.getcwd()
    finally:
        if os.path.isfile(path):
            try:
                os.remove(path)
            except (IOError, OSError, PermissionError):
                pass


if __name__ == "__main__":
    pytest.main()
