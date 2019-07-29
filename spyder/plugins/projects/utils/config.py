# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""Configuration options for projects"""

# Standard library imports
import os

# Local imports
from spyder.config.base import get_project_config_folder
from spyder.config.user import UserConfig

PROJECT_FILENAME = '.spyproj'


# Project configuration defaults
WORKSPACE = 'workspace'
WORKSPACE_DEFAULTS = [
    (WORKSPACE,
     {'restore_data_on_startup': True,
      'save_data_on_exit': True,
      'save_history': True,
      'save_non_project_files': False,
      }
     )]
WORKSPACE_VERSION = '0.1.0'


CODESTYLE = 'codestyle'
CODESTYLE_DEFAULTS = [
    (CODESTYLE,
     {'indentation': True,
      'edge_line': True,
      'edge_line_columns': '79',
      }
     )]
CODESTYLE_VERSION = '0.1.0'


ENCODING = 'encoding'
ENCODING_DEFAULTS = [
    (ENCODING,
     {'text_encoding': 'utf-8',
      }
     )]
ENCODING_VERSION = '0.1.0'


VCS = 'vcs'
VCS_DEFAULTS = [
    (VCS,
     {'use_version_control': False,
      'version_control_system': '',
      }
     )]
VCS_VERSION = '0.1.0'


class ProjectConfig(UserConfig):
    pass
