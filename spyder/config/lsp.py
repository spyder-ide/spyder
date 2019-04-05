# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder lsp variables
"""

# =============================================================================
# Default json config for the lsp
# =============================================================================
PYTHON_LSP_CONFIG = {
    'index': 0,
    'cmd': 'pyls',
    'args': '--host {host} --port {port} --tcp',
    'host': '127.0.0.1',
    'port': 2087,
    'external': False,
    'configurations': {
        'pyls': {
            'configurationSources': [
                "pycodestyle", "pyflakes"],
            'plugins': {
                'pycodestyle': {
                    'enabled': True,
                    'exclude': [],
                    'filename': [],
                    'select': [],
                    'ignore': [],
                    'hangClosing': False,
                    'maxLineLength': 79
                },
                'pyflakes': {
                    'enabled': True
                },
                'yapf': {
                    'enabled': False
                },
                'pydocstyle': {
                    'enabled': False,
                    'convention': 'pep257',
                    'addIgnore': [],
                    'addSelect': [],
                    'ignore': [],
                    'select': [],
                    'match': "(?!test_).*\\.py",
                    'matchDir': '[^\\.].*',
                },
                'rope': {
                    'extensionModules': None,
                    'ropeFolder': None,
                },
                'rope_completion': {
                    'enabled': False
                },
                'jedi_completion': {
                    'enabled': True,
                    'include_params': False
                },
                'jedi_hover': {
                    'enabled': True
                },
                'jedi_references': {
                    'enabled': True
                },
                'jedi_signature_help': {
                    'enabled': True
                },
                'jedi_symbols': {
                    'enabled': True,
                    'all_scopes': True
                },
                'mccabe': {
                    'enabled': False,
                    'threshold': 15
                },
                'preload': {
                    'enabled': True,
                    'modules': []
                }
            },

        }
    }
}
