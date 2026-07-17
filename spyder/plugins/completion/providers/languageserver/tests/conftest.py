# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from unittest.mock import Mock, MagicMock

from qtpy.QtCore import QObject, Signal, Slot
from qtpy.QtWidgets import QWidget
import pytest
from pytestqt.qtbot import QtBot

from lsprotocol import types as lsp

from spyder.config.manager import CONF
from spyder.plugins.completion.tests.conftest import qtbot_module
from spyder.plugins.completion.providers.languageserver.provider import (
    LanguageServerProvider)


class CompletionPluginMock(QObject):
    """
    Mock for the completion plugin.

    This is a genuine QObject subclass (rather than a MagicMock/QObject
    multiple-inheritance mix) because unittest.mock's __new__ reassigns
    each instance's __class__ to a freshly-created dynamic subclass, which
    breaks Shiboken's ability to associate the Python wrapper with its C++
    QObject counterpart under PySide6. Arbitrary attribute access still
    behaves like a mock via delegation to an internal MagicMock.
    """
    CONF_SECTION = 'completions'

    def __init__(self, conf):
        QObject.__init__(self)
        self.conf = conf
        self._mock = MagicMock()

    def __getattr__(self, name):
        return getattr(self._mock, name)

    def get_conf(self, option, default=None, section=None):
        if section == 'completions':
            option = option[-1]
            return self.conf.get(option, default)
        else:
            return CONF.get(section, option, default)


def lsp_context(is_stdio):
    @pytest.fixture(scope='module')
    def wrapper(qtbot_module, request):
        # Activate flake8 and pydocstyle
        conf = dict(LanguageServerProvider.CONF_DEFAULTS)
        conf['flake8'] = True
        conf['pydocstyle'] = True
        conf['stdio'] = is_stdio

        # Create the manager
        provider = LanguageServerProvider(CompletionPluginMock(conf), conf)

        # Wait for the client to be started
        with qtbot_module.waitSignal(
                provider.sig_language_completions_available,
                timeout=30000) as block:
            provider.start_completion_services_for_language('python')

        capabilities, _ = block.args
        assert isinstance(capabilities, lsp.ServerCapabilities)

        def teardown():
            provider.shutdown()

        request.addfinalizer(teardown)
        return provider
    return wrapper


lsp_provider = lsp_context(is_stdio=False)
lsp_stdio_provider = lsp_context(is_stdio=True)
