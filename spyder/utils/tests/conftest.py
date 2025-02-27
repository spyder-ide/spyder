#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Standard library imports
import os

# Third-party imports
import pytest

# Local imports
from spyder.config.base import running_in_ci
from spyder.utils.environ import (
    get_user_env, set_user_env, amend_user_shell_init
)


@pytest.fixture
def restore_user_env():
    """Set user environment variables and restore upon test exit"""
    if not running_in_ci():
        pytest.skip("Skipped because not in CI.")

    if os.name == "nt":
        orig_env = get_user_env()

    yield

    if os.name == "nt":
        set_user_env(orig_env)
    else:
        amend_user_shell_init(restore=True)
