# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Colin Duquesnoy (QCrash project)
# Copyright (c) 2018- Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/widgets/github/LICENSE.txt for details)
# -----------------------------------------------------------------------------

"""
Tests for the Github backend.

Adapted from tests/test_backends/test_github.py of the
`QCrash Project <https://github.com/ColinDuquesnoy/QCrash>`_.
"""

import os
import sys

import pytest

from spyder.config.base import running_in_ci
from spyder.config.manager import CONF
from spyder.widgets.github import backend


TOKEN = 'token1234'
GH_OWNER = 'ccordoba12'
GH_REPO = 'spyder'


def get_backend():
    b = backend.GithubBackend(GH_OWNER, GH_REPO)
    b._show_msgbox = False
    return b


def get_backend_bad_repo():
    b = backend.GithubBackend(GH_OWNER, GH_REPO + '1234')
    b._show_msgbox = False
    return b


def get_wrong_user_credentials():
    """
    Monkeypatch GithubBackend.get_user_credentials to force the case where
    invalid credentias were provided
    """
    return dict(token='invalid',
                remember_token=False)


def get_empty_user_credentials():
    """
    Monkeypatch GithubBackend.get_user_credentials to force the case where
    invalid credentias were provided
    """
    return dict(token='',
                remember_token=False)


def get_fake_user_credentials():
    """
    Monkeypatch GithubBackend.get_user_credentials to force the case where
    invalid credentias were provided
    """
    return dict(token=TOKEN,
                remember_token=False)


def test_invalid_credentials():
    b = get_backend()
    b.get_user_credentials = get_wrong_user_credentials
    ret_value = b.send_report('Wrong credentials', 'Wrong credentials')
    assert ret_value is False


def test_empty_credentials():
    b = get_backend()
    b.get_user_credentials = get_empty_user_credentials
    ret_value = b.send_report('Empty credentials', 'Wrong credentials')
    assert ret_value is False


def test_fake_credentials_bad_repo():
    b = get_backend_bad_repo()
    b.get_user_credentials = get_fake_user_credentials
    ret_value = b.send_report('Test suite', 'Test fake credentials')
    assert ret_value is False


def test_get_credentials_from_settings():
    b = get_backend()
    remember_token = b._get_credentials_from_settings()
    assert remember_token is False

    CONF.set('main', 'report_error/remember_token', True)

    remember_token = b._get_credentials_from_settings()
    assert remember_token is True


@pytest.mark.skipif(running_in_ci(), reason="Only works locally")
def test_store_user_credentials():
    b = get_backend()
    b._store_token('token', True)
    credentials = b.get_user_credentials()

    assert credentials['token'] == 'token'
    assert credentials['remember_token'] is True
