# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

import pytest

from spyder_kernels.utils.lazymodules import LazyModule, FakeObject


def test_non_existent_module():
    """Test that we retun FakeObject's for non-existing modules."""
    mod = LazyModule('no_module', second_level_attrs=['a'])

    # First level attributes must return FakeObject
    assert mod.foo is FakeObject

    # Second level attributes in second_level_attrs should return
    # FakeObject too.
    assert mod.foo.a is FakeObject

    # Other second level attributes should raise an error.
    with pytest.raises(AttributeError):
        mod.foo.b


def test_existing_modules():
    """Test that lazy modules work for existing modules."""
    np = LazyModule('numpy')
    import numpy

    # Both the lazy and actual modules should return the same.
    assert np.ndarray == numpy.ndarray

    # The lazy module should have these extra attributes
    assert np.__spy_mod__
    assert np.__spy_modname__
