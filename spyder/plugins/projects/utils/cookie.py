# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Cookiecutter utilities.
"""

import json
import os

from cookiecutter.main import cookiecutter


def generate_cookiecutter_project(cookiecutter_path, output_path,
                                  extra_content=None):
    """
    Generate a cookicutter project programmatically.
    """
    status = True
    try:
        result = cookiecutter(
            cookiecutter_path,
            output_dir=output_path,
            overwrite_if_exists=True,
            extra_context=extra_content,
            no_input=True,
        )
    except Exception as err:
        result = err
        status = False

    return status, result


def load_cookiecutter_project(project_path):
    """
    Load a cookicutter options and pre-hook script.
    """
    options = None
    pre_gen_code = None
    cookiepath = os.path.join(project_path, "cookiecutter.json")
    pre_gen_path = os.path.join(project_path, "hooks", "pre_gen_project.py")

    if os.path.isdir(project_path):
        if os.path.isfile(cookiepath):
            with open(cookiepath, 'r') as fh:
                options = json.loads(fh.read())

        if os.path.isfile(pre_gen_path):
            with open(pre_gen_path, 'r') as fh:
                pre_gen_code = fh.read()

    return options, pre_gen_code
