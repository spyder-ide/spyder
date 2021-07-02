# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import os
from pylsp._utils import find_parents
from .source import ConfigSource

log = logging.getLogger(__name__)

CONFIG_KEY = 'flake8'
PROJECT_CONFIGS = ['.flake8', 'setup.cfg', 'tox.ini']

OPTIONS = [
    # mccabe
    ('max-complexity', 'plugins.mccabe.threshold', int),
    # pycodestyle
    ('exclude', 'plugins.pycodestyle.exclude', list),
    ('filename', 'plugins.pycodestyle.filename', list),
    ('hang-closing', 'plugins.pycodestyle.hangClosing', bool),
    ('ignore', 'plugins.pycodestyle.ignore', list),
    ('max-line-length', 'plugins.pycodestyle.maxLineLength', int),
    ('select', 'plugins.pycodestyle.select', list),
    # flake8
    ('exclude', 'plugins.flake8.exclude', list),
    ('filename', 'plugins.flake8.filename', list),
    ('hang-closing', 'plugins.flake8.hangClosing', bool),
    ('ignore', 'plugins.flake8.ignore', list),
    ('max-line-length', 'plugins.flake8.maxLineLength', int),
    ('select', 'plugins.flake8.select', list),
]


class Flake8Config(ConfigSource):
    """Parse flake8 configurations."""

    def user_config(self):
        config_file = self._user_config_file()
        config = self.read_config_from_files([config_file])
        return self.parse_config(config, CONFIG_KEY, OPTIONS)

    def _user_config_file(self):
        if self.is_windows:
            return os.path.expanduser('~\\.flake8')
        return os.path.join(self.xdg_home, 'flake8')

    def project_config(self, document_path):
        files = find_parents(self.root_path, document_path, PROJECT_CONFIGS)
        config = self.read_config_from_files(files)
        return self.parse_config(config, CONFIG_KEY, OPTIONS)
