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

from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec
from spyder.py3compat import to_text_string


@pytest.mark.parametrize('default_interpreter', [True, False])
@pytest.mark.skipif(not running_in_ci(), reason="Only works in CI")
def test_preserve_pypath(tmpdir, default_interpreter):
    """
    Test that PYTHONPATH is preserved in the env vars passed to the kernel
    when an external interpreter is used or not.

    Regression test for spyder-ide/spyder#8681.
    """
    # Set default interpreter value
    CONF.set('main_interpreter', 'default', default_interpreter)

    # Add a path to PYTHONPATH env var
    pypath = to_text_string(tmpdir.mkdir('test-pypath'))
    os.environ['PYTHONPATH'] = pypath

    # Check that PYTHONPATH is in our kernelspec
    kernel_spec = SpyderKernelSpec()
    assert pypath in kernel_spec.env['PYTHONPATH']

    # Restore default value
    CONF.set('main_interpreter', 'default', True)


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
