# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for utilities in the pythonenv module
"""

# Standard library imports
import os
from pathlib import Path
import shutil

# Third-party imports
import pytest

# Local imports
from spyder_kernels.utils.pythonenv import (
    add_quotes,
    get_conda_env_path,
    get_env_dir,
    get_pixi_manifest_path_and_env_name,
)


if os.name == 'nt':
    TEST_PYEXEC = 'c:/miniconda/envs/foobar/python.exe'
else:
    TEST_PYEXEC = '/miniconda/envs/foobar/bin/python'


def test_add_quotes():
    output = add_quotes('/some path/with spaces')
    assert output == '"/some path/with spaces"'

    output = add_quotes('/some-path/with-no-spaces')
    assert output == '/some-path/with-no-spaces'


def test_get_conda_env_path():
    output = get_conda_env_path(TEST_PYEXEC)
    if os.name == 'nt':
        assert output == 'c:/miniconda/envs/foobar'
    else:
        assert output == '/miniconda/envs/foobar'


def test_get_env_dir():
    output_dir = get_env_dir(TEST_PYEXEC, only_dir=False)
    if os.name == "nt":
        assert output_dir == 'c:\\miniconda\\envs\\foobar'
    else:
        assert output_dir == '/miniconda/envs/foobar'

    output = get_env_dir(TEST_PYEXEC, only_dir=True)
    assert output == "foobar"

    if os.name == "nt":
        venv_pyexec = 'C:\\Miniconda3\\envs\\foobar\\Scripts\\python.exe'
        output = get_env_dir(venv_pyexec, only_dir=True)
        assert output == "foobar"


@pytest.mark.skipif(
    not (
        shutil.which("pixi.exe" if os.name == "nt" else "pixi")
        and os.environ.get("CI")
    ),
    reason="Only works with Pixi on CIs",
)
def test_get_pixi_info():
    home_path = Path(os.environ["HOME"])
    pixi_env_dir = home_path / "pixi-test" / ".pixi" / "envs" / "default"
    pixi_env_info = get_pixi_manifest_path_and_env_name(
        str(pixi_env_dir / "python.exe")
        if os.name == "nt"
        else str(pixi_env_dir / "bin" / "python")
    )

    assert pixi_env_info == (
        str(home_path / "pixi-test" / "pixi.toml"), "default"
    )


if __name__ == "__main__":
    pytest.main()
