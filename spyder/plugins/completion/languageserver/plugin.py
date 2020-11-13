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
import functools
import logging
import os
import os.path as osp

# Third-party imports
from qtpy.QtCore import Slot, QTimer
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.config.base import (_, get_conf_path, running_under_pytest,
                                running_in_mac_app)
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.manager import CONF
from spyder.api.completion import SpyderCompletionPlugin
from spyder.utils.misc import check_connection_port
from spyder.plugins.completion.languageserver import LSP_LANGUAGES
from spyder.plugins.completion.languageserver.client import LSPClient
from spyder.plugins.completion.languageserver.confpage import (
    LanguageServerConfigPage)
from spyder.plugins.completion.languageserver.widgets.status import (
    ClientStatus, LSPStatusWidget)
from spyder.widgets.helperwidgets import MessageCheckBox


logger = logging.getLogger(__name__)


class LanguageServerPlugin(SpyderCompletionPlugin):
    """Language Server Protocol manager."""
    CONF_SECTION = 'lsp-server'
    CONF_FILE = False

    COMPLETION_CLIENT_NAME = 'lsp'
    STOPPED = 'stopped'
    RUNNING = 'running'
    LOCALHOST = ['127.0.0.1', 'localhost']
    CONFIGWIDGET_CLASS = LanguageServerConfigPage
    MAX_RESTART_ATTEMPTS = 5
    TIME_BETWEEN_RESTARTS = 10000  # ms
    TIME_HEARTBEAT = 3000  # ms

    def __init__(self, parent):
        SpyderCompletionPlugin.__init__(self, parent)

        self.clients = {}
        self.clients_restart_count = {}
        self.clients_restart_timers = {}
        self.clients_restarting = {}
        self.clients_hearbeat = {}
        self.clients_statusbar = {}
        self.requests = set({})
        self.register_queue = {}
        self.update_configuration()
        self.show_no_external_server_warning = True

        # Status bar widget
        if parent is not None:
            statusbar = parent.statusBar()
            self.status_widget = LSPStatusWidget(
                None, statusbar, plugin=self)

    def __del__(self):
        """Stop all heartbeats"""
        for language in self.clients_hearbeat:
            try:
                self.clients_hearbeat[language].stop()
            except (TypeError, KeyError, RuntimeError):
                pass

    # --- Status bar widget handling
    def restart_lsp(self, language, force=False):
        """Restart language server on failure."""
        client_config = {
            'status': self.STOPPED,
            'config': self.get_language_config(language),
            'instance': None,
        }

        if force:
            logger.info("Manual restart for {}...".format(language))
            self.update_status(language, ClientStatus.RESTARTING)
            self.restart_client(language, client_config)

        elif self.clients_restarting[language]:
            attempt = (self.MAX_RESTART_ATTEMPTS
                       - self.clients_restart_count[language] + 1)
            logger.info("Automatic restart attempt {} for {}...".format(
                attempt, language))
            self.update_status(language, ClientStatus.RESTARTING)

            self.clients_restart_count[language] -= 1
            self.restart_client(language, client_config)
            client = self.clients[language]

            # Restarted the maximum amount of times without
            if self.clients_restart_count[language] <= 0:
                logger.info("Restart failed!")
                self.clients_restarting[language] = False
                self.clients_restart_timers[language].stop()
                self.clients_restart_timers[language] = None
                try:
                    self.clients_hearbeat[language].stop()
                    client['instance'].disconnect()
                    client['instance'].stop()
                except (TypeError, KeyError, RuntimeError):
                    pass
                self.clients_hearbeat[language] = None
                self.report_lsp_down(language)

    def check_restart(self, client, language):
        """
        Check if a server restart was successful in order to stop
        further attempts.
        """
        status = client['status']
        instance = client['instance']

        # This check is only necessary for stdio servers
        check = True
        if instance.stdio_pid:
            check = instance.is_stdio_alive()

        if status == self.RUNNING and check:
            logger.info("Restart successful!")
            self.clients_restarting[language] = False
            self.clients_restart_timers[language].stop()
            self.clients_restart_timers[language] = None
            self.clients_restart_count[language] = 0
            self.update_status(language, ClientStatus.READY)

    def check_heartbeat(self, language):
        """
        Check if client or server for a given language are down.
        """
        client = self.clients[language]
        status = client['status']
        instance = client.get('instance', None)
        if instance is not None:
            if instance.is_down() or status != self.RUNNING:
                instance.sig_went_down.emit(language)

    def update_status(self, language, status):
        """
        Update status for the current file.
        """
        self.clients_statusbar[language] = status
        self.status_widget.update_status(language, status)

    def on_initialize(self, options, language):
        """
        Update the status bar widget on client initilization.
        """
        # Set status after the server was started correctly.
        if not self.clients_restarting.get(language, False):
            self.update_status(language, ClientStatus.READY)

        # Set status after a restart.
        if self.clients_restarting.get(language):
            client = self.clients[language]
            self.check_restart(client, language)

    def handle_lsp_down(self, language):
        """
        Handle automatic restart of client/server on failure.
        """
        if (not self.clients_restarting.get(language, False)
                and not running_under_pytest()):
            try:
                self.clients_hearbeat[language].stop()
            except KeyError:
                pass
            logger.info("Automatic restart for {}...".format(language))

            timer = QTimer(self)
            timer.setSingleShot(False)
            timer.setInterval(self.TIME_BETWEEN_RESTARTS)
            timer.timeout.connect(lambda: self.restart_lsp(language))

            self.update_status(language, ClientStatus.RESTARTING)
            self.clients_restarting[language] = True
            self.clients_restart_count[language] = self.MAX_RESTART_ATTEMPTS
            self.clients_restart_timers[language] = timer
            timer.start()

    # --- Other methods
    def register_file(self, language, filename, codeeditor):
        if language in self.clients:
            language_client = self.clients[language]['instance']
            if language_client is None:
                self.register_queue[language].append((filename, codeeditor))
            else:
                language_client.register_file(filename, codeeditor)

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

        if not path:
            # We can't use getcwd_or_home for LSP servers because if it
            # returns home and you have a lot of files on it
            # then computing completions takes a long time
            # and blocks the server.
            # Instead we use an empty directory inside our config one,
            # just like we did for Rope in Spyder 3.
            path = osp.join(get_conf_path(), 'lsp_paths', 'root_path')
            if not osp.exists(path):
                os.makedirs(path)

        return path

    @Slot()
    def project_path_update(self, project_path, update_kind):
        """
        Send a didChangeWorkspaceFolders request to each LSP server
        when the project path changes so they can update their
        respective root paths.

        If the server doesn't support workspace updates, restart the
        client with the new root path.
        """
        for language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                instance = language_client['instance']
                if (instance.support_multiple_workspaces and
                        instance.support_workspace_update):
                    instance.send_workspace_folders_change({
                        'folder': project_path,
                        'instance': self.main.projects,
                        'kind': update_kind
                    })
                else:
                    logger.debug(
                        "{0}: LSP does not support multiple workspaces, "
                        "restarting client!".format(instance.language)
                    )
                    self.main.projects.stop_workspace_services()
                    self.main.editor.stop_completion_services(language)
                    self.main.outlineexplorer.stop_symbol_services(language)
                    folder = self.get_root_path(language)
                    instance.folder = folder
                    self.close_client(language)
                    self.start_client(language)

    @Slot(str)
    def report_server_error(self, error):
        """Report server errors in our error report dialog."""
        self.main.console.exception_occurred(error, is_traceback=True,
                                             is_pyls_error=True)

    def report_no_external_server(self, host, port, language):
        """
        Report that connection couldn't be established with
        an external server.
        """
        if os.name == 'nt':
            os_message = (
                "<br><br>"
                "To fix this, please verify that your firewall or antivirus "
                "allows Python processes to open ports in your system, or the "
                "settings you introduced in our Preferences to connect to "
                "external LSP servers."
            )
        else:
            os_message = (
                "<br><br>"
                "To fix this, please verify the settings you introduced in "
                "our Preferences to connect to external LSP servers."
            )

        warn_str = (
            _("It appears there is no {language} language server listening "
              "at address:"
              "<br><br>"
              "<tt>{host}:{port}</tt>"
              "<br><br>"
              "Therefore, completion and linting for {language} will not "
              "work during this session.").format(
                host=host, port=port, language=language.capitalize())
            + os_message
        )

        QMessageBox.warning(
            self.main,
            _("Warning"),
            warn_str
        )

        self.show_no_external_server_warning = False

    @Slot(str)
    def report_lsp_down(self, language):
        """
        Report that either the transport layer or the LSP server are
        down.
        """
        self.update_status(language, ClientStatus.DOWN)

        if not self.get_option('show_lsp_down_warning'):
            return

        if os.name == 'nt':
            os_message = (
                "To try to fix this, please verify that your firewall or "
                "antivirus allows Python processes to open ports in your "
                "system, or restart Spyder.<br><br>"
            )
        else:
            os_message = (
                "This problem could be fixed by restarting Spyder. "
            )

        warn_str = (
            _("Completion and linting in the editor for {language} files "
              "will not work during the current session, or stopped working."
              "<br><br>").format(language=language.capitalize())
            + os_message +
            _("Do you want to restart Spyder now?")
        )

        box = MessageCheckBox(icon=QMessageBox.Warning, parent=self.main)
        box.setWindowTitle(_("Warning"))
        box.set_checkbox_text(_("Don't show again"))
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.set_checked(False)
        box.set_check_visible(True)
        box.setText(warn_str)
        answer = box.exec_()

        self.set_option('show_lsp_down_warning', not box.is_checked())

        if answer == QMessageBox.Yes:
            self.main.restart()

    def start_client(self, language):
        """Start an LSP client for a given language."""
        # To keep track if the client was started.
        started = False

        if language in self.clients:
            language_client = self.clients[language]

            queue = self.register_queue[language]

            # Don't start LSP services when testing unless we demand
            # them.
            if running_under_pytest():
                if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                    return started

            started = language_client['status'] == self.RUNNING

            # Start client heartbeat
            timer = QTimer(self)
            self.clients_hearbeat[language] = timer
            timer.setInterval(self.TIME_HEARTBEAT)
            timer.timeout.connect(lambda: self.check_heartbeat(language))
            timer.start()

            if language_client['status'] == self.STOPPED:
                config = language_client['config']

                # If we're trying to connect to an external server,
                # verify that it's listening before creating a
                # client for it.
                if config['external']:
                    host = config['host']
                    port = config['port']
                    response = check_connection_port(host, port)
                    if not response:
                        if self.show_no_external_server_warning:
                            self.report_no_external_server(
                                host, port, language)
                        self.update_status(language, ClientStatus.DOWN)
                        return False

                language_client['instance'] = LSPClient(
                    parent=self,
                    server_settings=config,
                    folder=self.get_root_path(language),
                    language=language
                )

                self.register_client_instance(language_client['instance'])

                # Register that a client was started.
                logger.info("Starting LSP client for {}...".format(language))
                language_client['instance'].start()
                language_client['status'] = self.RUNNING
                started = True
                for entry in queue:
                    language_client['instance'].register_file(*entry)
                self.register_queue[language] = []

        return started

    def register_client_instance(self, instance):
        """Register signals emmited by a client instance."""
        if self.main:
            self.main.sig_pythonpath_changed.connect(self.update_syspath)
            self.main.sig_main_interpreter_changed.connect(
                functools.partial(self.update_configuration, python_only=True))
            instance.sig_went_down.connect(self.handle_lsp_down)
            instance.sig_initialize.connect(self.on_initialize)

            if self.main.projects:
                instance.sig_initialize.connect(
                    lambda settings, language:
                    self.main.projects.start_workspace_services())
            if self.main.editor:
                instance.sig_initialize.connect(
                    self.main.editor.register_completion_capabilities)
                self.main.editor.sig_editor_focus_changed.connect(
                    self.status_widget.update_status)
            if self.main.outlineexplorer:
                instance.sig_initialize.connect(
                    self.main.outlineexplorer.start_symbol_services)
            if self.main.console:
                instance.sig_server_error.connect(self.report_server_error)

    def shutdown(self):
        logger.info("Shutting down LSP manager...")
        for language in self.clients:
            self.close_client(language)

    @Slot(object, object)
    def update_syspath(self, path_dict, new_path_dict):
        """
        Update server configuration after a change in Spyder's Python
        path.

        `path_dict` corresponds to the previous state of the Python path.
        `new_path_dict` corresponds to the new state of the Python path.
        """
        # If path_dict and new_path_dict are the same, it means the change
        # was generated by opening or closing a project. In that case, we
        # don't need to request an update because that's done through the
        # addition/deletion of workspaces.
        update = True
        if path_dict == new_path_dict:
            update = False

        if update:
            logger.debug("Update server's sys.path")
            self.update_configuration(python_only=True)

    def update_configuration(self, python_only=False):
        """
        Update server configuration after changes done by the user
        through Spyder's Preferences.

        python_only: bool
            Perform an update only for the Python language server.
        """
        for language in self.get_languages():
            if python_only and language != 'python':
                continue

            client_config = {'status': self.STOPPED,
                             'config': self.get_language_config(language),
                             'instance': None}
            if language not in self.clients:
                self.clients[language] = client_config
                self.register_queue[language] = []
            else:
                current_lang_config = self.clients[language]['config']
                new_lang_config = client_config['config']
                restart_diff = ['cmd', 'args', 'host',
                                'port', 'external', 'stdio']
                restart = any([current_lang_config[x] != new_lang_config[x]
                               for x in restart_diff])
                if restart:
                    logger.debug("Restart required for {} client!".format(
                        language))
                    if self.clients[language]['status'] == self.STOPPED:
                        # If we move from an external non-working server to
                        # an internal one, we need to start a new client.
                        if (current_lang_config['external'] and
                                not new_lang_config['external']):
                            self.restart_client(language, client_config)
                        else:
                            self.clients[language] = client_config
                    elif self.clients[language]['status'] == self.RUNNING:
                        self.restart_client(language, client_config)
                else:
                    if self.clients[language]['status'] == self.RUNNING:
                        client = self.clients[language]['instance']
                        client.send_configurations(
                            new_lang_config['configurations'])

    def restart_client(self, language, config):
        """Restart a client."""
        self.main.editor.stop_completion_services(language)
        self.main.projects.stop_workspace_services()
        self.main.outlineexplorer.stop_symbol_services(language)
        self.close_client(language)
        self.clients[language] = config
        self.start_client(language)

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

    def receive_response(self, response_type, response, language, req_id):
        if req_id in self.requests:
            self.requests.discard(req_id)
            self.sig_response_ready.emit(
                self.COMPLETION_CLIENT_NAME, req_id, response)

    def send_request(self, language, request, params, req_id):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                self.requests.add(req_id)
                client = self.clients[language]['instance']
                params['response_callback'] = functools.partial(
                    self.receive_response, language=language, req_id=req_id)
                client.perform_request(request, params)
                return
        self.sig_response_ready.emit(self.COMPLETION_CLIENT_NAME,
                                     req_id, {})

    def send_notification(self, language, request, params):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                client = self.clients[language]['instance']
                client.perform_request(request, params)

    def broadcast_notification(self, request, params):
        """Send notification/request to all available LSP servers."""
        language = params.pop('language', None)
        if language:
            self.send_notification(language, request, params)
        else:
            for language in self.clients:
                self.send_notification(language, request, params)

    def generate_python_config(self):
        """
        Update Python server configuration with the options saved in our
        config system.
        """
        python_config = PYTHON_CONFIG.copy()

        # Server options
        cmd = self.get_option('advanced/module')
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

        # Autoformatting configuration
        formatter = self.get_option('formatting')
        formatter = 'pyls_black' if formatter == 'black' else formatter
        formatters = ['autopep8', 'yapf', 'pyls_black']
        formatter_options = {
            fmt: {
                'enabled': fmt == formatter
            }
            for fmt in formatters
        }

        if formatter == 'pyls_black':
            formatter_options['pyls_black']['line_length'] = cs_max_line_length

        # PyLS-Spyder configuration
        group_cells = self.get_option(
            'group_cells',
            section='outline_explorer'
        )
        display_block_comments = self.get_option(
            'show_comments',
            section='outline_explorer'
        )
        pyls_spyder_options = {
            'enable_block_comments': display_block_comments,
            'group_cells': group_cells
        }

        # Jedi configuration
        if self.get_option('default', section='main_interpreter'):
            environment = None
            env_vars = None
        else:
            environment = self.get_option('custom_interpreter',
                                          section='main_interpreter')
            env_vars = os.environ.copy()
            # external interpreter should not use internal PYTHONPATH
            env_vars.pop('PYTHONPATH', None)
            if running_in_mac_app():
                env_vars.pop('PYTHONHOME', None)

        jedi = {
            'environment': environment,
            'extra_paths': self.get_option('spyder_pythonpath',
                                           section='main', default=[]),
            'env_vars': env_vars,
        }
        jedi_completion = {
            'enabled': self.get_option('code_completion'),
            'include_params':  self.get_option('code_snippets')
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
            python_config['args'] = ('--host {host} --port {port} --tcp '
                                     '--check-parent-process')
        else:
            python_config['args'] = '--check-parent-process'
        python_config['external'] = external_server
        python_config['stdio'] = stdio
        python_config['host'] = host
        python_config['port'] = port

        plugins = python_config['configurations']['pyls']['plugins']
        plugins['pycodestyle'].update(pycodestyle)
        plugins['pyflakes'].update(pyflakes)
        plugins['pydocstyle'].update(pydocstyle)
        plugins['pyls_spyder'].update(pyls_spyder_options)
        plugins['jedi'].update(jedi)
        plugins['jedi_completion'].update(jedi_completion)
        plugins['jedi_signature_help'].update(jedi_signature_help)
        plugins['jedi_definition'].update(jedi_definition)
        plugins['preload']['modules'] = self.get_option('preload_modules')

        for formatter in formatters:
            plugins[formatter] = formatter_options[formatter]

        return python_config
