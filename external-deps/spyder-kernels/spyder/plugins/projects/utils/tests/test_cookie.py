# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for qcookiecutter widget.
"""

# Standard library imports
import json
import os
import shutil
import tempfile

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.utils.cookie import (
    generate_cookiecutter_project, load_cookiecutter_project)


def test_load_cookiecutter_project_config():
    settings = {
        "opt_1": "value",
        "opt_2": "{{ cookiecutter.opt_1 }}",
    }
    temp_path = tempfile.mkdtemp(suffix='-some-cookiecutter')
    temp_cookie_path = os.path.join(temp_path, 'cookiecutter.json')

    with open(temp_cookie_path, 'w') as fh:
        fh.write(json.dumps(settings, sort_keys=True))

    sets, pre_gen_code = load_cookiecutter_project(temp_path)
    assert settings == sets
    assert pre_gen_code is None

    shutil.rmtree(temp_path)


def test_load_cookiecutter_project_hooks():
    settings = {
        "opt_1": "value",
        "opt_2": "{{ cookiecutter.opt_1 }}",
    }
    pre_gen_code = "import sys\n\nprint('test!')\nsys.exit(1)\n"
    temp_path = tempfile.mkdtemp(suffix='-some-cookiecutter')
    temp_cookie_path = os.path.join(temp_path, 'cookiecutter.json')
    temp_hooks_path = os.path.join(temp_path, 'hooks')
    temp_hooks_pre_path = os.path.join(temp_hooks_path, 'pre_gen_project.py')
    os.makedirs(temp_hooks_path)

    with open(temp_cookie_path, 'w') as fh:
        fh.write(json.dumps(settings, sort_keys=True))

    with open(temp_hooks_pre_path, 'w') as fh:
        fh.write(pre_gen_code)

    sets, pre_gen_code = load_cookiecutter_project(temp_path)
    assert settings == sets
    assert pre_gen_code == pre_gen_code

    shutil.rmtree(temp_path)


def test_generate_cookiecutter_project_defaults():
    settings = {
        "repo_name": "value",
    }
    temp_path = tempfile.mkdtemp(suffix='-some-cookiecutter')
    temp_path_created = tempfile.mkdtemp(suffix='-created-project')
    temp_cookie_path = os.path.join(temp_path, 'cookiecutter.json')
    temp_project_path = os.path.join(temp_path, '{{cookiecutter.repo_name}}')
    os.makedirs(temp_project_path)

    with open(temp_cookie_path, 'w') as fh:
        fh.write(json.dumps(settings, sort_keys=True))

    status, result = generate_cookiecutter_project(
        temp_path,
        temp_path_created,
    )
    assert "value" in result
    assert status is True
    shutil.rmtree(temp_path)


def test_generate_cookiecutter_project_extra_content():
    settings = {
        "repo_name": "value",
    }
    temp_path = tempfile.mkdtemp(suffix='-some-cookiecutter')
    temp_path_created = tempfile.mkdtemp(suffix='-created-project')
    temp_cookie_path = os.path.join(temp_path, 'cookiecutter.json')
    temp_project_path = os.path.join(temp_path, '{{cookiecutter.repo_name}}')
    os.makedirs(temp_project_path)

    with open(temp_cookie_path, 'w') as fh:
        fh.write(json.dumps(settings, sort_keys=True))

    status, result = generate_cookiecutter_project(
        temp_path,
        temp_path_created,
        {"repo_name": "boom"},
    )
    assert "boom" in result
    assert status is True
    shutil.rmtree(temp_path)


def test_generate_cookiecutter_project_exception():
    settings = {
        "repo_name": "value",
    }
    temp_path = tempfile.mkdtemp(suffix='-some-invalid-cookiecutter')
    temp_path_created = tempfile.mkdtemp(suffix='-created-project')
    temp_cookie_path = os.path.join(temp_path, 'cookiecutter.json')
    temp_project_path = os.path.join(
        temp_path,
        '{{cookiecutter.not_foun_variable}}',
    )
    os.makedirs(temp_project_path)

    with open(temp_cookie_path, 'w') as fh:
        fh.write(json.dumps(settings, sort_keys=True))

    status, __ = generate_cookiecutter_project(
        temp_path,
        temp_path_created,
    )
    assert status is False


if __name__ == "__main__":
    pytest.main()
