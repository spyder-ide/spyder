# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Tests for Spyder's Variable Explorer.
"""


# Standard library imports
import pytest

# Third party imports
from spyder.utils.qthelpers import qapplication
from spyder.plugins.variableexplorer.plugin import VariableExplorer


def test_get_settings(monkeypatch):
    def mock_get_option(self, option):
        if option == 'remote1': return 'remote1val'
        if option == 'remote2': return 'remote2val'
        if option == 'dataframe_format': return '3d'

    monkeypatch.setattr(VariableExplorer, 'CONF_SECTION', 'sect')
    monkeypatch.setattr('spyder.plugins.variableexplorer.plugin.REMOTE_SETTINGS',
                        ['remote1', 'remote2'])
    monkeypatch.setattr(VariableExplorer, 'get_option', mock_get_option)

    app = qapplication()
    settings = VariableExplorer(None).get_settings()
    expected = {'remote1': 'remote1val', 'remote2': 'remote2val',
                'dataframe_format': '%3d'}
    assert settings == expected


if __name__ == "__main__":
    pytest.main()
