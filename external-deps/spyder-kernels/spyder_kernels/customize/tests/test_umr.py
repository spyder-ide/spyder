# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the User Module Reloader."""

# Stdlib imports
import os
import sys

# Third party imports
import pytest

# Local imports
from spyder_kernels.py3compat import to_text_string
from spyder_kernels.customize.umr import UserModuleReloader


@pytest.fixture
def user_module(tmpdir):
    """Create a simple module in tmpdir as an example of a user module."""
    if to_text_string(tmpdir) not in sys.path:
        sys.path.append(to_text_string(tmpdir))

    def create_module(modname):
        modfile = tmpdir.mkdir(modname).join('bar.py')
        code = """
def square(x):
    return x**2
        """
        modfile.write(code)

        init_file = tmpdir.join(modname).join('__init__.py')
        init_file.write('#')

    return create_module


def test_umr_skip_cython(user_module):
    """
    Test that the UMR doesn't try to reload modules when Cython
    support is active.
    """
    # Create user module
    user_module('foo')

    # Activate Cython support
    os.environ['SPY_RUN_CYTHON'] = 'True'

    # Create UMR
    umr = UserModuleReloader()

    import foo
    assert umr.is_module_reloadable(foo, 'foo') == False

    # Deactivate Cython support
    os.environ['SPY_RUN_CYTHON'] = 'False'


def test_umr_run(user_module):
    """Test that UMR's run method is working correctly."""
    # Create user module
    user_module('foo1')

    # Activate verbose mode in the UMR
    os.environ['SPY_UMR_VERBOSE'] = 'True'

    # Create UMR
    umr = UserModuleReloader()

    from foo1.bar import square
    umr.run()
    umr.modnames_to_reload == ['foo', 'foo.bar']


def test_umr_previous_modules(user_module):
    """Test that UMR's previos_modules is working as expected."""
    # Create user module
    user_module('foo2')

    # Create UMR
    umr = UserModuleReloader()

    import foo2
    assert 'IPython' in umr.previous_modules
    assert 'foo2' not in umr.previous_modules


def test_umr_namelist():
    """Test that the UMR skips modules according to its name."""
    umr = UserModuleReloader()

    assert umr.is_module_in_namelist('tensorflow')
    assert umr.is_module_in_namelist('pytorch')
    assert umr.is_module_in_namelist('spyder_kernels')
    assert not umr.is_module_in_namelist('foo')


def test_umr_reload_modules(user_module):
    """Test that the UMR only tries to reload user modules."""
    # Create user module
    user_module('foo3')

    # Create UMR
    umr = UserModuleReloader()

    # Don't reload stdlib modules
    import xml
    assert not umr.is_module_reloadable(xml, 'xml')

    # Don't reload third-party modules
    import numpy
    assert not umr.is_module_reloadable(numpy, 'numpy')

    # Reload user modules
    import foo3
    assert umr.is_module_reloadable(foo3, 'foo3')
