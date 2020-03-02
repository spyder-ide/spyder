# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""Tests for the execution of pylint."""

# Third party imports
import pytest
import os.path as osp

# Local imports
from spyder.plugins.pylint.widgets.pylintgui import get_pylintrc_path

PYLINT_TEST_SCRIPT = """#%%

# pylint: enable=C0111
# pylint: enable=C0103
# pylint: enable=C0413

a = 10


#%%
li = [1, 2, 3]

#%%
import numpy as np
arr = np.array(li)
"""
PYLINT_TEST_RC = "[BASIC]\ngood-names=%s"
PYLINT_TEST_MSG = "Constant name \"%s\" doesn't conform to UPPER_CASE naming style"


@pytest.fixture(params=["proj", "cwd", "both"])
def pylint_test_setup(tmp_path_factory, request):
    pylintrc_location = request.param
    cwd_path = tmp_path_factory.mktemp("work_dir")
    proj_path = tmp_path_factory.mktemp("proj_dir")
    script_file = tmp_path_factory.mktemp("script_dir") / "script.py"
    script_file.write_text(PYLINT_TEST_SCRIPT)

    if pylintrc_location == "both":
        # the .pylintrc in the project directory is superseded
        # by the .pylintrc in the current working directory
        pylintrc_file = proj_path / ".pylintrc"
        pylintrc_file.write_text(PYLINT_TEST_RC % "li")
        pylintrc_location = "cwd"

    if pylintrc_location == "cwd":
        pylintrc_file = cwd_path / ".pylintrc"
    else:
        pylintrc_file = proj_path / ".pylintrc"
    pylintrc_file.write_text(PYLINT_TEST_RC % "a")

    paths = [str(p) for p in [script_file, pylintrc_file, proj_path, cwd_path]]
    messages = [PYLINT_TEST_MSG % const_name for const_name in ["a", "li"]]
    return paths + messages


def test_pylintrc_path(pylint_test_setup):
    script_file, pylintrc_file, proj_path, cwd_path, _, _ = pylint_test_setup
    search_paths = [
        osp.dirname(script_file),  # File's directory
        cwd_path,  # Working directory
        proj_path,  # Project directory
    ]
    auto_path = get_pylintrc_path(search_paths)
    assert auto_path == pylintrc_file
