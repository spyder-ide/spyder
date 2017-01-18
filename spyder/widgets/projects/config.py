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
from spyder.config.user import UserConfig

PROJECT_FILENAME = '.spyproj'
PROJECT_FOLDER = '.spyproject'


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
    """ProjectConfig class, based on UserConfig.

    Parameters
    ----------
    name: str
        name of the config
    defaults: tuple
        dictionnary containing options *or* list of tuples
        (section_name, options)
    version: str
        version of the configuration file (X.Y.Z format)
    filename: str
        configuration file will be saved in %home%/subfolder/%name%.ini
    """
    DEFAULT_SECTION_NAME = 'main'

    def __init__(self, name, root_path, filename, defaults=None, load=True,
                 version=None):
        self.project_root_path = root_path

        # Config rootpath
        self._root_path = os.path.join(root_path, PROJECT_FOLDER)
        self._filename = filename

        # Create folder if non existent
        if not os.path.isdir(self._root_path):
            os.makedirs(self._root_path)

        # Add file
        # NOTE: We have to think better about the uses of this file
        # with open(os.path.join(root_path, PROJECT_FILENAME), 'w') as f:
        #    f.write('spyder-ide project\n')

        UserConfig.__init__(self, name, defaults=defaults, load=load,
                            version=version, subfolder=None, backup=False,
                            raw_mode=True, remove_obsolete=True)

