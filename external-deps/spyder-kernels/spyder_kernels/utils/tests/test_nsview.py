# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for utils.py
"""

# Standard library imports
from collections import defaultdict
import datetime
import sys

# Third party imports
import numpy as np
import pandas as pd
import pytest
import xarray as xr
import PIL.Image

# Local imports
from spyder_kernels.py3compat import PY2
from spyder_kernels.utils.nsview import (
    sort_against, is_supported, value_to_display, get_size,
    get_supported_types, get_type_string, get_numpy_type_string,
    is_editable_type)


def generate_complex_object():
    """Taken from issue #4221."""
    bug = defaultdict(list)
    for i in range(50000):
        a = {j:np.random.rand(10) for j in range(10)}
        bug[i] = a
    return bug


COMPLEX_OBJECT = generate_complex_object()
DF = pd.DataFrame([1,2,3])
DATASET = xr.Dataset({0: pd.DataFrame([1,2]), 1:pd.DataFrame([3,4])})


# --- Tests
# -----------------------------------------------------------------------------
def test_get_size():
    """Test that the size of all values is returned correctly"""

    class RecursionClassNoLen():
        def __getattr__(self, name):
            if name=='size': return self.name
            else:
                return super(object, self).__getattribute__(name)


    length = [list([1,2,3]), tuple([1,2,3]), set([1,2,3]), '123',
              {1:1, 2:2, 3:3}]
    for obj in length:
        assert get_size(obj) == 3

    df = pd.DataFrame([[1,2,3], [1,2,3]])
    assert get_size(df) == (2, 3)

    df = pd.Series([1,2,3])
    assert get_size(df) == (3,)

    df = pd.Index([1,2,3])
    assert get_size(df) == (3,)

    arr = np.array([[1,2,3], [1,2,3]], dtype=np.complex128)
    assert get_size(arr) == (2, 3)

    img = PIL.Image.new('RGB', (256,256))
    assert get_size(img) == (256,256)

    obj = RecursionClassNoLen()
    assert get_size(obj) == 1



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


def test_str_subclass_display():
    """Test for value_to_display of subclasses of str/basestring."""
    class Test(str):
        def __repr__(self):
            return 'test'
    value = Test()
    value_display = value_to_display(value)
    assert 'Test object' in value_display


def test_default_display():
    """Tests for default_display."""
    # Display of defaultdict
    assert (value_to_display(COMPLEX_OBJECT) ==
            'defaultdict object of collections module')

    # Display of array of COMPLEX_OBJECT
    assert (value_to_display(np.array(COMPLEX_OBJECT)) ==
            'ndarray object of numpy module')

    # Display of Dataset
    assert (value_to_display(DATASET) ==
            'Dataset object of xarray.core.dataset module')


@pytest.mark.skipif(
    sys.platform == 'darwin' and sys.version_info[:2] == (3, 8),
    reason="Fails on Mac with Python 3.8")
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
    assert value_to_display([1, 2, [[DF], DATASET]]) == '[1, 2, [[...], Dataset]]'

    # List of complex object
    assert value_to_display([COMPLEX_OBJECT]) == '[defaultdict]'

    # List of composed objects
    li = [COMPLEX_OBJECT, DATASET, 1, {1:2, 3:4}, DF]
    result = '[defaultdict, Dataset, 1, {1:2, 3:4}, Dataframe]'
    assert value_to_display(li) == result

    # List starting with a non-supported object (#5313)
    supported_types = tuple(get_supported_types()['editable'])
    li = [len, 1]
    assert value_to_display(li) == '[builtin_function_or_method, 1]'
    assert is_supported(li, filters=supported_types)


@pytest.mark.skipif(
    sys.platform == 'darwin' and sys.version_info[:2] == (3, 8),
    reason="Fails on Mac with Python 3.8")
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
    assert value_to_display({0:0, 1:1, 2:[[DF], DATASET]}) == '{0:0, 1:1, 2:[[...], Dataset]}'

    # Dict of complex object
    assert value_to_display({0:COMPLEX_OBJECT}) == '{0:defaultdict}'

    # Dict of composed objects
    li = {0:COMPLEX_OBJECT, 1:DATASET, 2:2, 3:{0:0, 1:1}, 4:DF}
    result = '{0:defaultdict, 1:Dataset, 2:2, 3:{0:0, 1:1}, 4:Dataframe}'
    assert value_to_display(li) == result

    # Dict starting with a non-supported object (#5313)
    supported_types = tuple(get_supported_types()['editable'])
    di = {max: len, 1: 1}
    assert value_to_display(di) in (
            '{builtin_function_or_method:builtin_function_or_method, 1:1}',
            '{1:1, builtin_function_or_method:builtin_function_or_method}')
    assert is_supported(di, filters=supported_types)


def test_set_display():
    """Tests for display of sets."""
    long_set = {i for i in range(100)}

    # Simple set
    assert value_to_display({1, 2, 3}) == '{1, 2, 3}'

    # Long set
    disp = '{0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...}'
    assert value_to_display(long_set) == disp

    # Short list of sets
    disp = '[{0, 1, 2, 3, 4, ...}, {0, 1, 2, 3, 4, ...}, {0, 1, 2, 3, 4, ...}]'
    assert value_to_display([long_set] * 3) == disp

    # Long list of sets
    disp = '[' + ''.join('{0, 1, 2, 3, 4, ...}, '*10)[:-2] + ']'
    assert value_to_display([long_set] * 10) == disp[:70] + ' ...'


def test_datetime_display():
    """Simple tests that dates, datetimes and timedeltas display correctly."""
    test_date = datetime.date(2017, 12, 18)
    test_date_2 = datetime.date(2017, 2, 2)

    test_datetime = datetime.datetime(2017, 12, 18, 13, 43, 2)
    test_datetime_2 = datetime.datetime(2017, 8, 18, 0, 41, 27)

    test_timedelta = datetime.timedelta(-1, 2000)
    test_timedelta_2 = datetime.timedelta(0, 3600)

    # Simple dates/datetimes/timedeltas
    assert value_to_display(test_date) == '2017-12-18'
    assert value_to_display(test_datetime) == '2017-12-18 13:43:02'
    assert value_to_display(test_timedelta) == '-1 day, 0:33:20'

    # Lists of dates/datetimes/timedeltas
    assert (value_to_display([test_date, test_date_2]) ==
            '[2017-12-18, 2017-02-02]')
    assert (value_to_display([test_datetime, test_datetime_2]) ==
            '[2017-12-18 13:43:02, 2017-08-18 00:41:27]')
    assert (value_to_display([test_timedelta, test_timedelta_2]) ==
            '[-1 day, 0:33:20, 1:00:00]')

    # Tuple of dates/datetimes/timedeltas
    assert (value_to_display((test_date, test_datetime, test_timedelta)) ==
            '(2017-12-18, 2017-12-18 13:43:02, -1 day, 0:33:20)')

    # Dict of dates/datetimes/timedeltas
    assert (value_to_display({0: test_date,
                              1: test_datetime,
                              2: test_timedelta_2}) ==
            ("{0:2017-12-18, 1:2017-12-18 13:43:02, 2:1:00:00}"))


def test_str_in_container_display():
    """Test that strings are displayed correctly inside lists or dicts."""
    # Assert that both bytes and unicode return the right display
    assert value_to_display([b'a', u'b']) == "['a', 'b']"

    # Encoded unicode gives bytes and it can't be transformed to
    # unicode again. So this test the except part of
    # is_binary_string(value) in value_to_display
    if PY2:
        assert value_to_display([u'Э'.encode('cp1251')]) == "['\xdd']"


def test_ellipses(tmpdir):
    """
    Test that we're adding a binary ellipses when value_to_display of
    a collection is too long and binary.

    For issue 6942
    """
    # Create binary file with all bytes
    file = tmpdir.new(basename='bytes.txt')
    file.write_binary(bytearray(list(range(255))))

    # Read bytes back
    buffer = file.read(mode='rb')

    # Assert that there's a binary ellipses in the representation
    assert b' ...' in value_to_display(buffer)


def test_get_type_string():
    """Test for get_type_string."""
    # Bools
    assert get_type_string(True) == 'bool'

    # Numeric types (PY2 has long, which disappeared in PY3)
    if not PY2:
        expected = ['int', 'float', 'complex']
        numeric_types = [1, 1.5, 1 + 2j]
        assert [get_type_string(t) for t in numeric_types] == expected

    # Lists
    assert get_type_string([1, 2, 3]) == 'list'

    # Sets
    assert get_type_string({1, 2, 3}) == 'set'

    # Dictionaries
    assert get_type_string({'a': 1, 'b': 2}) == 'dict'

    # Tuples
    assert get_type_string((1, 2, 3)) == 'tuple'

    # Strings
    if not PY2:
        assert get_type_string('foo') == 'str'

    # Numpy objects
    assert get_type_string(np.array([1, 2, 3])) == 'NDArray'

    masked_array = np.ma.MaskedArray([1, 2, 3], mask=[True, False, True])
    assert get_type_string(masked_array) == 'MaskedArray'

    matrix = np.matrix([[1, 2], [3, 4]])
    assert get_type_string(matrix) == 'Matrix'

    # Pandas objects
    df = pd.DataFrame([1, 2, 3])
    assert get_type_string(df) == 'DataFrame'

    series = pd.Series([1, 2, 3])
    assert get_type_string(series) == 'Series'

    index = pd.Index([1, 2, 3])
    assert get_type_string(index) in ['Int64Index', 'Index']

    # PIL images
    img = PIL.Image.new('RGB', (256,256))
    assert get_type_string(img) == 'PIL.Image.Image'

    # Datetime objects
    date = datetime.date(2010, 10, 1)
    assert get_type_string(date) == 'datetime.date'

    date = datetime.timedelta(-1, 2000)
    assert get_type_string(date) == 'datetime.timedelta'


def test_is_editable_type():
    """Test for get_type_string."""
    # Bools
    assert is_editable_type(True)

    # Numeric type
    numeric_types = [1, 1.5, 1 + 2j]
    assert all([is_editable_type(t) for t in numeric_types])

    # Lists
    assert is_editable_type([1, 2, 3])

    # Sets
    assert is_editable_type({1, 2, 3})

    # Dictionaries
    assert is_editable_type({'a': 1, 'b': 2})

    # Tuples
    assert is_editable_type((1, 2, 3))

    # Strings
    assert is_editable_type('foo')

    # Numpy objects
    assert is_editable_type(np.array([1, 2, 3]))

    masked_array = np.ma.MaskedArray([1, 2, 3], mask=[True, False, True])
    assert is_editable_type(masked_array)

    matrix = np.matrix([[1, 2], [3, 4]])
    assert is_editable_type(matrix)

    # Pandas objects
    df = pd.DataFrame([1, 2, 3])
    assert is_editable_type(df)

    series = pd.Series([1, 2, 3])
    assert is_editable_type(series)

    index = pd.Index([1, 2, 3])
    assert is_editable_type(index)

    # PIL images
    img = PIL.Image.new('RGB', (256,256))
    assert is_editable_type(img)

    # Datetime objects
    date = datetime.date(2010, 10, 1)
    assert is_editable_type(date)

    date = datetime.timedelta(-1, 2000)
    assert is_editable_type(date)

    # Other objects
    class MyClass:
        a = 1
    assert not is_editable_type(MyClass)

    my_instance = MyClass()
    assert not is_editable_type(my_instance)


def test_get_numpy_type():
    """Test for get_numpy_type_string."""
    # Numpy objects
    assert get_numpy_type_string(np.array([1, 2, 3])) == 'Array'

    matrix = np.matrix([[1, 2], [3, 4]])
    assert get_numpy_type_string(matrix) == 'Array'

    assert get_numpy_type_string(np.int32(1)) == 'Scalar'

    # Regular Python objects
    assert get_numpy_type_string(1.5) == 'Unknown'
    assert get_numpy_type_string([1, 2, 3]) == 'Unknown'
    assert get_numpy_type_string({1: 2}) == 'Unknown'

    # PIL images
    img = PIL.Image.new('RGB', (256,256))
    assert get_numpy_type_string(img) == 'Unknown'

    # Pandas objects
    df = pd.DataFrame([1, 2, 3])
    assert get_numpy_type_string(df) == 'Unknown'


if __name__ == "__main__":
    pytest.main()
