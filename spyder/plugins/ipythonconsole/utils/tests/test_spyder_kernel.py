# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Spyder kernel
"""

import pytest

from spyder.config.manager import CONF
from spyder.plugins.ipythonconsole.utils.kernelspec import SpyderKernelSpec


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
