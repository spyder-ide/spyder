# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Spyder kernel
"""

import os
import pytest

from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.py3compat import to_text_string


@pytest.mark.parametrize('default_interpreter', [True, False])
def test_kernel_pypath(tmpdir, default_interpreter):
    """
    Test that PYTHONPATH and spyder_pythonpath option are properly handled
    when an external interpreter is used or not.

    Regression test for spyder-ide/spyder#8681.
    Regression test for spyder-ide/spyder#17511.
    """
    # Set default interpreter value
    CONF.set('main_interpreter', 'default', default_interpreter)

    # Add a path to PYTHONPATH and spyder_pythonpath config option
    pypath = to_text_string(tmpdir.mkdir('test-pypath'))
    os.environ['PYTHONPATH'] = pypath
    CONF.set('pythonpath_manager', 'spyder_pythonpath', [pypath])

    kernel_spec = SpyderKernelSpec()

    # Check that PYTHONPATH is not in our kernelspec
    # and pypath is in SPY_PYTHONPATH
    assert 'PYTHONPATH' not in kernel_spec.env
    assert pypath in kernel_spec.env['SPY_PYTHONPATH']

    # Restore default values
    CONF.set('main_interpreter', 'default', True)
    CONF.set('pythonpath_manager', 'spyder_pythonpath', [])
    del os.environ['PYTHONPATH']


def test_python_interpreter(tmpdir):
    """Test the validation of the python interpreter."""
    # Set a non existing python interpreter
    interpreter = str(tmpdir.mkdir('interpreter').join('python'))
    CONF.set('main_interpreter', 'default', False)
    CONF.set('main_interpreter', 'custom', True)
    CONF.set('main_interpreter', 'executable', interpreter)

    # Create a kernel spec
    kernel_spec = SpyderKernelSpec()

    # Assert that the python interprerter is the default one
    assert interpreter not in kernel_spec.argv
    assert CONF.get('main_interpreter', 'default')
    assert not CONF.get('main_interpreter', 'custom')


if __name__ == "__main__":
    pytest.main()
