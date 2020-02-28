# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Configuration options for projects."""

# Local imports
from spyder.config.user import MultiUserConfig, UserConfig


# Constants
PROJECT_FILENAME = '.spyproj'
WORKSPACE = 'workspace'
CODESTYLE = 'codestyle'
ENCODING = 'encoding'
VCS = 'vcs'


# Project configuration defaults
PROJECT_DEFAULTS = [
    (WORKSPACE,
     {'restore_data_on_startup': True,
      'save_data_on_exit': True,
      'save_history': True,
      'save_non_project_files': False,
      }
     ),
    (CODESTYLE,
     {'indentation': True,
      'edge_line': True,
      'edge_line_columns': '79',
      }
     ),
    (VCS,
     {'use_version_control': False,
      'version_control_system': '',
      }
     ),
    (ENCODING,
     {'text_encoding': 'utf-8',
      }
     )
]


PROJECT_NAME_MAP = {
    # Empty container object means use the rest of defaults
    WORKSPACE: [],
    # Splitting these files makes sense for projects, we might as well
    # apply the same split for the app global config
    # These options change on spyder startup or are tied to a specific OS,
    # not good for version control
    WORKSPACE: [
        (WORKSPACE, [
            'restore_data_on_startup',
            'save_data_on_exit',
            'save_history',
            'save_non_project_files',
            ],
         ),
    ],
    CODESTYLE: [
        (CODESTYLE, [
            'indentation',
            'edge_line',
            'edge_line_columns',
            ],
         ),
    ],
    VCS: [
        (VCS, [
            'use_version_control',
            'version_control_system',
            ],
         ),
    ],
    ENCODING: [
        (ENCODING, [
            'text_encoding',
            ]
         ),
    ],
}


# =============================================================================
# Config instance
# =============================================================================
# IMPORTANT NOTES:
# 1. If you want to *change* the default value of a current option, you need to
#    do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
# 2. If you want to *remove* options that are no longer needed in our codebase,
#    or if you want to *rename* options, then you need to do a MAJOR update in
#    version, e.g. from 3.0.0 to 4.0.0
# 3. You don't need to touch this value if you're just adding a new option
PROJECT_CONF_VERSION = '0.2.0'


class ProjectConfig(UserConfig):
    """Plugin configuration handler."""


class ProjectMultiConfig(MultiUserConfig):
    """Plugin configuration handler with multifile support."""
    DEFAULT_FILE_NAME = WORKSPACE

    def get_config_class(self):
        return ProjectConfig
