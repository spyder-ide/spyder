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
from urllib.parse import urlparse

from cookiecutter.main import cookiecutter
from github import Github, GithubRetry


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


def load_cookiecutter_project(project_path, token=None):
    """
    Load a cookicutter options and pre-hook script.
    """
    options = None
    pre_gen_code = None
    if urlparse(project_path).scheme in ("http", "https", "git", "ssh"):
        parsed_url = urlparse(project_path)
        parts = parsed_url.path.strip("/").split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL")

        user, repo_name = parts[0], parts[1].replace(".git", "")
        gh = (
            Github(token, retry=GithubRetry(total=0))
            if token
            else Github(retry=GithubRetry(total=0))
        )
        repo = gh.get_repo(f"{user}/{repo_name}")
        repo.raw_data

        try:
            cookie_file = repo.get_contents("cookiecutter.json")
            cookie_json = cookie_file.decoded_content.decode("utf-8")
            options = json.loads(cookie_json)
        except Exception:
            options = None

        # Leer hooks/pre_gen_project.py (si existe)
        try:
            pre_gen_file = repo.get_contents("hooks/pre_gen_project.py")
            pre_gen_code = pre_gen_file.decoded_content.decode("utf-8")
        except Exception:
            pre_gen_code = None
    elif os.path.isdir(project_path):
        cookiepath = os.path.join(project_path, "cookiecutter.json")
        pre_gen_path = os.path.join(
            project_path, "hooks", "pre_gen_project.py"
        )
        if os.path.isfile(cookiepath):
            with open(cookiepath, 'r') as fh:
                options = json.loads(fh.read())

        if os.path.isfile(pre_gen_path):
            with open(pre_gen_path, 'r') as fh:
                pre_gen_code = fh.read()

    return options, pre_gen_code
