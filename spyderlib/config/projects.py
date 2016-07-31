# -*- coding: utf-8 -*-
"""
IMPORTANT NOTES:
1. If you want to *change* the default value of a current option, you need to
   do a MINOR update in config version, e.g. from 3.0.0 to 3.1.0
2. If you want to *remove* options that are no longer needed in our codebase,
   you need to do a MAJOR update in version, e.g. from 3.0.0 to 4.0.0
3. You don't need to touch this value if you're just adding a new option
"""
import os
import os.path as osp

from spyderlib.config.user import UserConfig


# Project file defaults
PROJECT_FOLDER = '.spyderproject'
PROJECT_FILE_EXT = '.spyproj'
PROJECT_DEFAULTS = [
    ('main',
     {'spyder_project': True,
      }
     )]
PROJECT_VERSION = '0.1.0'


class ProjectConfig(UserConfig):
    """ProjectConfig class, based on UserConfig.

    Parameters
    ----------
    name : 

    root_path : 

    filename :

    defaults : 

    load : 
    
    version : 

    """
    DEFAULT_SECTION_NAME = 'main'

    def __init__(self, name, root_path, filename, defaults=None, load=True,
                 version=None):

        self.set_filename(filename)
        self.set_root_path(root_path)

        UserConfig.__init__(self, name, defaults=defaults, load=load,
                            version=version, subfolder=None, backup=False,
                            raw_mode=True, remove_obsolete=True)

    def set_filename(self, filename):
        """ """
        self._filename = filename

    def set_root_path(self, root_path):
        """ """
        self._root_path = root_path
        if osp.isdir(root_path):
            return True
        else:
            os.makedirs(root_path)
            return False
