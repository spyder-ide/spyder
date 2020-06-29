# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Configuration options for the Language Server.

Notes:

1. Please preserve the structure of this dictionary. This is what
   we need to send to the PyLS to configure it.
1. Not all these options can be defined through our Preferences
   (e.g. `ropeFolder`).
3. The way we change the values of this dictionary with the options
   saved in our Preferences can be found in editor/lsp/manager.py
"""

# =============================================================================
# Default json config for the lsp
# =============================================================================
PYTHON_CONFIG = {
    'cmd': 'pyls',
    'args': '--host {host} --port {port} --tcp',
    'host': '127.0.0.1',
    'port': 2087,
    'external': False,
    'stdio': False,
    'configurations': {
        'pyls': {
            'configurationSources': [
                "pycodestyle", "pyflakes"],
            'plugins': {
                'pycodestyle': {
                    'enabled': False,
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
                'jedi': {
                    'environment': None,
                    'extra_paths': None,
                },
                'jedi_completion': {
                    'enabled': True,
                    'include_params': False,
                    'include_class_objects': False,
                    'fuzzy': False
                },
                'jedi_definition': {
                    'enabled': True,
                    'follow_imports': True,
                    'follow_builtin_imports': True
                },
                'jedi_hover': {
                    # This option always needs to be `True` so that we can
                    # request information for the Object Inspection Help Pane
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
                },
                'pylint': {
                    'enabled': False,
                    'args': []
                },
                'flake8': {
                     'enabled': False,
                }
            },

        }
    }
}
