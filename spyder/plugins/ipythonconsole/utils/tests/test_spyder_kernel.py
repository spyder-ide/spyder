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

from spyder.config.main import CONF
from spyder.py3compat import PY2, is_binary_string, to_text_string
from spyder.utils.encoding import to_fs_from_unicode
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec


@pytest.mark.parametrize('default_interpreter', [True, False])
def test_preserve_pypath(tmpdir, default_interpreter):
    """
    Test that we preserve PYTHONPATH in the env vars passed to the kernel
    when an external interpreter is used or not.

    Regression test for issue 8681.
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


@pytest.mark.skipif(os.name != 'nt' or not PY2,
                    reason="It only makes sense on Windows and Python 2")
def test_env_vars():
    """Test that we are correctly encoding env vars in our kernel spec"""
    # Create a variable with the file system encoding and save it
    # in our PYTHONPATH
    env_var = to_fs_from_unicode(u'ñññ')
    CONF.set('main', 'spyder_pythonpath', [env_var])

    # Create a kernel spec
    kernel_spec = SpyderKernelSpec()

    # Assert PYTHONPATH is in env vars and it's not empty
    assert kernel_spec.env['PYTHONPATH'] != ''

    # Assert all env vars are binary strings
    assert all([is_binary_string(v) for v in kernel_spec.env.values()])

    # Remove our entry from PYTHONPATH
    CONF.set('main', 'spyder_pythonpath', [])


if __name__ == "__main__":
    pytest.main()
