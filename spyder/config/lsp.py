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
    'cmd': 'pylsp',
    'args': '--host {host} --port {port} --tcp',
    'host': '127.0.0.1',
    'port': 2087,
    'external': False,
    'stdio': False,
    'configurations': {
        'pylsp': {
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
                'autopep8': {
                    'enabled': True
                },
                'pylsp_black': {
                    # This is necessary for python-lsp-black less than 2.0.
                    # See python-lsp/python-lsp-black#41
                    'enabled': False
                },
                'black': {
                    'enabled': False,
                    'line_length': 79,
                    'preview': False,
                    'cache_config': False,
                    'skip_magic_trailing_comma': False,
                    'skip_string_normalization': False,
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
                    'extra_paths': [],
                    'env_vars': None,
                    # Until we have a graphical way for users to add modules to
                    # this option
                    'auto_import_modules': [
                        'numpy', 'matplotlib', 'pandas', 'scipy'
                    ]
                },
                'jedi_completion': {
                    'enabled': True,
                    'include_params': False,
                    'include_class_objects': False,
                    'include_function_objects': False,
                    'fuzzy': False,
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
                    'all_scopes': True,
                    'include_import_symbols': False
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
                },
                'pyls_spyder': {
                    'enable_block_comments': True,
                    'group_cells': True
                },
                'pyls_flake8': {
                    # This third-party plugin is deprecated now.
                    'enabled': False,
                },
                'ruff': {
                    # Disable it until we have a graphical option for users to
                    # enable it.
                    'enabled': False,
                }
            },

        }
    }
}
