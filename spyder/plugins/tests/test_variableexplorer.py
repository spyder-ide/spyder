# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""
Tests for variableexplorer.py
"""

import pytest

from spyder.plugins.variableexplorer import VariableExplorer

def test_get_settings(monkeypatch):
    def mock_get(section, option):
        assert section == 'sect'
        if option == 'remote1': return 'remote1val'
        if option == 'remote2': return 'remote2val'
        if option == 'dataframe_format': return '3d'
        
    monkeypatch.setattr(VariableExplorer, 'CONF_SECTION', 'sect')
    monkeypatch.setattr('spyder.plugins.variableexplorer.REMOTE_SETTINGS', 
                        ['remote1', 'remote2'])
    monkeypatch.setattr('spyder.plugins.variableexplorer.CONF.get', mock_get)
    
    settings = VariableExplorer.get_settings()
    expected = {'remote1': 'remote1val', 'remote2': 'remote2val',
                'dataframe_format': '%3d'}
    assert settings == expected


if __name__ == "__main__":
    pytest.main()
    