# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Manager for all LSP clients connected to the servers defined
in our Preferences.
"""

# Standard library imports
import logging
import os
import os.path as osp

# Third-party imports
from qtpy.QtCore import QObject, Slot

# Local imports
from spyder.config.base import get_conf_path, running_under_pytest
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.main import CONF
from spyder.utils.misc import select_port, getcwd_or_home
from spyder.plugins.editor.lsp import LSP_LANGUAGES
from spyder.plugins.editor.lsp.client import LSPClient


logger = logging.getLogger(__name__)


class LSPManager(QObject):
    """Language Server Protocol manager."""
    STOPPED = 'stopped'
    RUNNING = 'running'
    CONF_SECTION = 'lsp-server'
    LOCALHOST = ['127.0.0.1', 'localhost']

    def __init__(self, parent):
        QObject.__init__(self)
        self.main = parent

        self.clients = {}
        self.requests = {}
        self.register_queue = {}

        # Register languages to create clients for
        for language in self.get_languages():
            self.clients[language] = {
                'status': self.STOPPED,
                'config': self.get_language_config(language),
                'instance': None
            }
            self.register_queue[language] = []

    def register_file(self, language, filename, codeeditor):
        if language in self.clients:
            language_client = self.clients[language]['instance']
            if language_client is None:
                self.register_queue[language].append((filename, codeeditor))
            else:
                language_client.register_file(filename, codeeditor)

    def get_option(self, option):
        """Get an option from our config system."""
        return CONF.get(self.CONF_SECTION, option)

    def get_languages(self):
        """
        Get the list of languages we need to start servers and create
        clients for.
        """
        languages = ['python']
        all_options = CONF.options(self.CONF_SECTION)
        for option in all_options:
            if option in [l.lower() for l in LSP_LANGUAGES]:
                languages.append(option)
        return languages

    def get_language_config(self, language):
        """Get language configuration options from our config system."""
        if language == 'python':
            return self.generate_python_config()
        else:
            return self.get_option(language)

    def get_root_path(self, language):
        """
        Get root path to pass to the LSP servers.

        This can be the current project path or the output of
        getcwd_or_home (except for Python, see below).
        """
        path = None

        # Get path of the current project
        if self.main and self.main.projects:
            path = self.main.projects.get_active_project_path()

        # If there's no project, use the output of getcwd_or_home.
        if not path:
            # We can't use getcwd_or_home for Python because if it
            # returns home and you have a lot of Python files on it
            # then computing Rope completions takes a long time
            # and blocks the PyLS server.
            # Instead we use an empty directory inside our config one,
            # just like we did for Rope in Spyder 3.
            if language == 'python':
                path = get_conf_path('lsp_root_path')
                if not osp.exists(path):
                    os.mkdir(path)
            else:
                path = getcwd_or_home()

        return path

    @Slot()
    def reinitialize_all_clients(self):
        """
        Send a new initialize message to each LSP server when the project
        path has changed so they can update the respective server root paths.
        """
        for language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                folder = self.get_root_path(language)
                instance = language_client['instance']
                instance.folder = folder
                instance.initialize()

    @Slot(str)
    def report_server_error(self, error):
        """Report server errors in our error report dialog."""
        self.main.console.exception_occurred(error, is_traceback=True,
                                             is_pyls_error=True)

    def start_client(self, language):
        """Start an LSP client for a given language."""
        started = False
        if language in self.clients:
            language_client = self.clients[language]
            queue = self.register_queue[language]

            # Don't start LSP services when testing unless we demand
            # them.
            if running_under_pytest():
                if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                    return started

            # Start client
            started = language_client['status'] == self.RUNNING
            if language_client['status'] == self.STOPPED:
                config = language_client['config']

                if not config['external']:
                    port = select_port(default_port=config['port'])
                    config['port'] = port

                language_client['instance'] = LSPClient(
                    parent=self,
                    server_settings=config,
                    folder=self.get_root_path(language),
                    language=language
                )

                self.register_client_instance(language_client['instance'])

                logger.info("Starting LSP client for {}...".format(language))
                language_client['instance'].start()
                language_client['status'] = self.RUNNING
                for entry in queue:
                    language_client.register_file(*entry)
                self.register_queue[language] = []
        return started

    def register_client_instance(self, instance):
        """Register signals emmited by a client instance."""
        if self.main:
            if self.main.editor:
                instance.sig_initialize.connect(
                    self.main.editor.register_lsp_server_settings)
            if self.main.console:
                instance.sig_server_error.connect(self.report_server_error)

    def shutdown(self):
        logger.info("Shutting down LSP manager...")
        for language in self.clients:
            self.close_client(language)

    def update_server_list(self):
        for language in self.get_languages():
            config = {'status': self.STOPPED,
                      'config': self.get_language_config(language),
                      'instance': None}
            if language not in self.clients:
                self.clients[language] = config
                self.register_queue[language] = []
            else:
                logger.debug(
                    self.clients[language]['config'] != config['config'])
                current_config = self.clients[language]['config']
                new_config = config['config']
                restart_diff = ['cmd', 'args', 'host',
                                'port', 'external', 'stdio']
                restart = any([current_config[x] != new_config[x]
                               for x in restart_diff])
                if restart:
                    if self.clients[language]['status'] == self.STOPPED:
                        self.clients[language] = config
                    elif self.clients[language]['status'] == self.RUNNING:
                        self.main.editor.stop_lsp_services(language)
                        self.close_client(language)
                        self.clients[language] = config
                        self.start_client(language)
                else:
                    if self.clients[language]['status'] == self.RUNNING:
                        client = self.clients[language]['instance']
                        client.send_plugin_configurations(
                            new_config['configurations'])

    def update_client_status(self, active_set):
        for language in self.clients:
            if language not in active_set:
                self.close_client(language)

    def close_client(self, language):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                logger.info("Stopping LSP client for {}...".format(language))
                # language_client['instance'].shutdown()
                # language_client['instance'].exit()
                language_client['instance'].stop()
            language_client['status'] = self.STOPPED

    def send_request(self, language, request, params):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                client = self.clients[language]['instance']
                client.perform_request(request, params)

    def generate_python_config(self):
        """
        Update Python server configuration with the options saved in our
        config system.
        """
        python_config = PYTHON_CONFIG.copy()

        # Server options
        cmd = self.get_option('advanced/command_launch')
        host = self.get_option('advanced/host')
        port = self.get_option('advanced/port')

        # Pycodestyle
        cs_exclude = self.get_option('pycodestyle/exclude').split(',')
        cs_filename = self.get_option('pycodestyle/filename').split(',')
        cs_select = self.get_option('pycodestyle/select').split(',')
        cs_ignore = self.get_option('pycodestyle/ignore').split(',')
        cs_max_line_length = self.get_option('pycodestyle/max_line_length')

        pycodestyle = {
            'enabled': self.get_option('pycodestyle'),
            'exclude': [exclude.strip() for exclude in cs_exclude if exclude],
            'filename': [filename.strip()
                         for filename in cs_filename if filename],
            'select': [select.strip() for select in cs_select if select],
            'ignore': [ignore.strip() for ignore in cs_ignore if ignore],
            'hangClosing': False,
            'maxLineLength': cs_max_line_length
        }

        # Linting - Pyflakes
        pyflakes = {
            'enabled': self.get_option('pyflakes')
        }

        # Pydocstyle
        convention = self.get_option('pydocstyle/convention')

        if convention == 'Custom':
            ds_ignore = self.get_option('pydocstyle/ignore').split(',')
            ds_select = self.get_option('pydocstyle/select').split(',')
            ds_add_ignore = []
            ds_add_select = []
        else:
            ds_ignore = []
            ds_select = []
            ds_add_ignore = self.get_option('pydocstyle/ignore').split(',')
            ds_add_select = self.get_option('pydocstyle/select').split(',')

        pydocstyle = {
            'enabled': self.get_option('pydocstyle'),
            'convention': convention,
            'addIgnore': [ignore.strip()
                          for ignore in ds_add_ignore if ignore],
            'addSelect': [select.strip()
                          for select in ds_add_select if select],
            'ignore': [ignore.strip() for ignore in ds_ignore if ignore],
            'select': [select.strip() for select in ds_select if select],
            'match': self.get_option('pydocstyle/match'),
            'matchDir': self.get_option('pydocstyle/match_dir')
        }

        # Code completion
        jedi_completion = {
            'enabled': self.get_option('code_completion'),
            'include_params': False
        }

        jedi_signature_help = {
            'enabled': self.get_option('jedi_signature_help')
        }

        jedi_definition = {
            'enabled': self.get_option('jedi_definition'),
            'follow_imports': self.get_option('jedi_definition/follow_imports')
        }

        # Advanced
        external_server = self.get_option('advanced/external')
        stdio = self.get_option('advanced/stdio')

        # Setup options in json
        python_config['cmd'] = cmd
        if host in self.LOCALHOST and not stdio:
            python_config['args'] = '--host {host} --port {port} --tcp'
        else:
            python_config['args'] = ''
        python_config['external'] = external_server
        python_config['stdio'] = stdio
        python_config['host'] = host
        python_config['port'] = port

        plugins = python_config['configurations']['pyls']['plugins']
        plugins['pycodestyle'] = pycodestyle
        plugins['pyflakes'] = pyflakes
        plugins['pydocstyle'] = pydocstyle
        plugins['jedi_completion'] = jedi_completion
        plugins['jedi_signature_help'] = jedi_signature_help
        plugins['preload']['modules'] = self.get_option('preload_modules')
        plugins['jedi_definition'] = jedi_definition

        return python_config
