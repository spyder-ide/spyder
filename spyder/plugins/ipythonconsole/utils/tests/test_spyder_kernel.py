# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for the Spyder kernel
"""

import sys

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


@pytest.mark.parametrize("from_config", [True, False])
def test_python_interpreter_surrounding_whitespace(from_config):
    """
    Check that whitespace around the python interpreter path is removed
    before using it to start kernels.

    This is a regression test for spyder-ide/spyder#24955
    """
    interpreter = sys.executable + "\n"
    section = "main_interpreter"
    options = ["default", "custom", "executable"]
    previous = {
        opt: CONF.get(section, opt)
        for opt in options
        if CONF.has_option(section, opt)
    }
    CONF.set(section, "default", False)
    CONF.set(section, "custom", True)

    try:
        # Create a kernel spec with an interpreter that comes from the config
        # or from another plugin
        if from_config:
            CONF.set(section, "executable", interpreter)
            kernel_spec = SpyderKernelSpec()
        else:
            CONF.set(section, "executable", sys.executable)
            kernel_spec = SpyderKernelSpec(
                path_to_custom_interpreter=interpreter
            )

        # Assert the interpreter is used without the whitespace
        argv = kernel_spec.argv
        assert sys.executable in argv
        assert interpreter not in argv
        assert CONF.get(section, "custom")
    finally:
        for opt in options:
            if opt in previous:
                CONF.set(section, opt, previous[opt])
            elif CONF.has_option(section, opt):
                CONF.remove_option(section, opt)


if __name__ == "__main__":
    pytest.main()
