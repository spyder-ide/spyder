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
from qtpy.QtCore import Signal, Slot, QTimer
from qtpy.QtCore import Slot, QTimer
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.config.base import (_, get_conf_path, running_under_pytest,
                                running_in_mac_app)
from spyder.config.lsp import PYTHON_CONFIG
from spyder.config.manager import CONF
from spyder.utils.misc import check_connection_port
from spyder.plugins.completion.api import (SUPPORTED_LANGUAGES,
                                           SpyderCompletionProvider,
                                           WorkspaceUpdateKind)
from spyder.plugins.completion.providers.languageserver.client import LSPClient
from spyder.plugins.completion.providers.languageserver.conftabs import TABS
from spyder.plugins.completion.providers.languageserver.widgets import (
    ClientStatus, LSPStatusWidget, ServerDisabledMessageBox)
from spyder.utils.introspection.module_completion import PREFERRED_MODULES

# Modules to be preloaded for Rope and Jedi
PRELOAD_MDOULES = ', '.join(PREFERRED_MODULES)

logger = logging.getLogger(__name__)


class LanguageServerProvider(SpyderCompletionProvider):
    """Language Server Protocol manager."""
    COMPLETION_PROVIDER_NAME = 'lsp'
    DEFAULT_ORDER = 1
    SLOW = True
    CONF_DEFAULTS = [
        ('enable_hover_hints', True),
        ('show_lsp_down_warning', True),
        ('code_completion', True),
        # ('code_snippets', True),
        ('jedi_definition', True),
        ('jedi_definition/follow_imports', True),
        ('jedi_signature_help', True),
        ('preload_modules', PRELOAD_MDOULES),
        ('pyflakes', True),
        ('mccabe', False),
        ('formatting', 'autopep8'),
        ('format_on_save', False),
        ('pycodestyle', False),
        ('pycodestyle/filename', ''),
        ('pycodestyle/exclude', ''),
        ('pycodestyle/select', ''),
        ('pycodestyle/ignore', ''),
        ('pycodestyle/max_line_length', 79),
        ('pydocstyle', False),
        ('pydocstyle/convention', 'numpy'),
        ('pydocstyle/select', ''),
        ('pydocstyle/ignore', ''),
        ('pydocstyle/match', '(?!test_).*\\.py'),
        ('pydocstyle/match_dir', '[^\\.].*'),
        ('advanced/enabled', False),
        ('advanced/module', 'pyls'),
        ('advanced/host', '127.0.0.1'),
        ('advanced/port', 2087),
        ('advanced/external', False),
        ('advanced/stdio', False)
    ]

    # IMPORTANT NOTES:
    # 1. If you want to *change* the default value of a current option, you
    #    need to do a MINOR update in config version, e.g. from 0.1.0 to 0.2.0
    # 2. If you want to *remove* options that are no longer needed or if you
    #    want to *rename* options, then you need to do a MAJOR update in
    #    version, e.g. from 0.1.0 to 1.0.0
    # 3. You don't need to touch this value if you're just adding a new option
    CONF_VERSION = "0.1.0"
    CONF_TABS = TABS

    STOPPED = 'stopped'
    RUNNING = 'running'
    LOCALHOST = ['127.0.0.1', 'localhost']

    MAX_RESTART_ATTEMPTS = 5
    TIME_BETWEEN_RESTARTS = 10000  # ms
    TIME_HEARTBEAT = 3000  # ms

    # --- Signals
    # ------------------------------------------------------------------------
    sig_exception_occurred = Signal(dict)
    """
    This Signal is emitted to report that an exception has occurred.

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The expected keys are:
        >>> error_data = {
            "text": str,
            "is_traceback": bool,
            "title": str,
        }

    Notes
    -----
    The `is_traceback` key indicates if `text` contains plain text or a Python
    error traceback.

    `title` indicates how the error data should customize the report dialog.
    """

    def __init__(self, parent, config):
        SpyderCompletionProvider.__init__(self, parent, config)

        self.clients = {}
        self.clients_restart_count = {}
        self.clients_restart_timers = {}
        self.clients_restarting = {}
        self.clients_hearbeat = {}
        self.clients_statusbar = {}
        self.requests = set({})
        self.register_queue = {}
        self.update_lsp_configuration()
        self.show_no_external_server_warning = True
        self.current_project_path = None

        # Status bar widget
        self.STATUS_BAR_CLASSES = [
            self.create_statusbar
        ]

    def __del__(self):
        """Stop all heartbeats"""
        for language in self.clients_hearbeat:
            try:
                self.clients_hearbeat[language].stop()
            except (TypeError, KeyError, RuntimeError):
                pass

    # --- Status bar widget handling
    def restart_lsp(self, language: str, force=False):
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

    def create_statusbar(self, parent):
        return LSPStatusWidget(parent, self)

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
        self.sig_call_statusbar.emit(
            LSPStatusWidget.ID, 'update_status', (language, status), {})

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

    # ------------------ SpyderCompletionProvider methods ---------------------
    def get_name(self):
        return _('Language Server Protocol (LSP)')

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
        all_options = self.config
        for option in all_options:
            if option in [l.lower() for l in SUPPORTED_LANGUAGES]:
                languages.append(option)
        return languages

    def get_language_config(self, language):
        """Get language configuration options from our config system."""
        if language == 'python':
            return self.generate_python_config()
        else:
            return self.get_conf(language)

    def get_root_path(self, language):
        """
        Get root path to pass to the LSP servers.

        This can be the current project path or the output of
        getcwd_or_home (except for Python, see below).
        """
        path = self.current_project_path

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
    def project_path_update(self, project_path, update_kind, projects):
        """
        Send a didChangeWorkspaceFolders request to each LSP server
        when the project path changes so they can update their
        respective root paths.

        If the server doesn't support workspace updates, restart the
        client with the new root path.
        """
        if update_kind == WorkspaceUpdateKind.ADDITION:
            self.current_project_path = project_path

        for language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                instance = language_client['instance']
                if (instance.support_multiple_workspaces and
                        instance.support_workspace_update):
                    instance.send_workspace_folders_change({
                        'folder': project_path,
                        'instance': projects,
                        'kind': update_kind
                    })
                else:
                    logger.debug(
                        "{0}: LSP does not support multiple workspaces, "
                        "restarting client!".format(instance.language)
                    )
                    folder = self.get_root_path(language)
                    instance.folder = folder
                    self.sig_stop_completions.emit(language)
                    self.stop_completion_services_for_language(language)
                    self.start_completion_services_for_language(language)


    @Slot(str)
    def report_server_error(self, error):
        """Report server errors in our error report dialog."""
        error_data = dict(
            text=error,
            is_traceback=True,
            title="Internal Python Language Server error",
        )
        self.sig_exception_occurred.emit(error_data)

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

        def wrap_message_box(parent):
            return QMessageBox.warning(parent, _("Warning"), warn_str)

        self.sig_show_widget.emit(wrap_message_box)
        self.show_no_external_server_warning = False

    @Slot(str)
    def report_lsp_down(self, language):
        """
        Report that either the transport layer or the LSP server are
        down.
        """
        self.update_status(language, ClientStatus.DOWN)

        if not self.get_conf('show_lsp_down_warning'):
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

        wrapper = ServerDisabledMessageBox.instance(warn_str, self.set_conf)
        self.sig_show_widget.emit(wrapper)

    def start_completion_services_for_language(self, language):
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
            timer.timeout.connect(functools.partial(self.check_heartbeat, language))
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
        """Register signals emitted by a client instance."""
        instance.sig_went_down.connect(self.handle_lsp_down)
        instance.sig_initialize.connect(self.on_initialize)
        instance.sig_server_error.connect(self.report_server_error)
        instance.sig_initialize.connect(
            self.sig_language_completions_available)

    def start(self):
        self.sig_provider_ready.emit(self.COMPLETION_PROVIDER_NAME)

    def shutdown(self):
        logger.info("Shutting down LSP manager...")
        for language in self.clients:
            self.stop_completion_services_for_language(language)

    @Slot(object, object)
    def python_path_update(self, path_dict, new_path_dict):
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
            self.update_lsp_configuration(python_only=True)

    @Slot()
    def main_interpreter_changed(self):
        self.update_lsp_configuration(python_only=True)

    def file_opened_closed_or_updated(self, filename: str, language: str):
        self.sig_call_statusbar.emit(
            LSPStatusWidget.ID, 'set_current_language', (language,), {})

    @on_conf_change
    def update_configuration(self, config):
        self.config = config
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return
        self.update_lsp_configuration()

    @on_conf_change(section='outline_explorer',
                    option=['group_cells', 'show_comments'])
    def on_pyls_spyder_configuration_change(self, option, value):
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return
        self.update_lsp_configuration()

    @on_conf_change(section='completions', option='enable_code_snippets')
    def on_code_snippets_enabled_disabled(self, value):
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return
        self.update_lsp_configuration()

    @on_conf_change(section='main', option='spyder_pythonpath')
    def on_pythonpath_option_update(self, value):
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return
        self.update_lsp_configuration(python_only=True)

    @on_conf_change(section='main_interpreter',
                    option=['default', 'custom_interpreter'])
    def on_main_interpreter_change(self, option, value):
        if running_under_pytest():
            if not os.environ.get('SPY_TEST_USE_INTROSPECTION'):
                return
        self.update_lsp_configuration()

    def update_lsp_configuration(self, python_only=False):
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
        self.sig_stop_completions.emit(language)
        self.stop_completion_services_for_language(language)
        self.clients[language] = config
        self.start_completion_services_for_language(language)

    def update_client_status(self, active_set):
        for language in self.clients:
            if language not in active_set:
                self.stop_completion_services_for_language(language)

    def stop_completion_services_for_language(self, language):
        if language in self.clients:
            language_client = self.clients[language]
            if language_client['status'] == self.RUNNING:
                logger.info("Stopping LSP client for {}...".format(language))
                try:
                    language_client['instance'].disconnect()
                except TypeError:
                    pass
                language_client['instance'].stop()
            language_client['status'] = self.STOPPED

    def receive_response(self, response_type, response, language, req_id):
        if req_id in self.requests:
            self.requests.discard(req_id)
            self.sig_response_ready.emit(
                self.COMPLETION_PROVIDER_NAME, req_id, response)

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
        self.sig_response_ready.emit(self.COMPLETION_PROVIDER_NAME,
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
        cmd = self.get_conf('advanced/module', 'pyls')
        host = self.get_conf('advanced/host', '127.0.0.1')
        port = self.get_conf('advanced/port', 2087)

        # Pycodestyle
        cs_exclude = self.get_conf('pycodestyle/exclude', '').split(',')
        cs_filename = self.get_conf('pycodestyle/filename', '').split(',')
        cs_select = self.get_conf('pycodestyle/select', '').split(',')
        cs_ignore = self.get_conf('pycodestyle/ignore', '').split(',')
        cs_max_line_length = self.get_conf('pycodestyle/max_line_length', 79)

        pycodestyle = {
            'enabled': self.get_conf('pycodestyle'),
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
            'enabled': self.get_conf('pyflakes')
        }

        # Pydocstyle
        convention = self.get_conf('pydocstyle/convention')

        if convention == 'Custom':
            ds_ignore = self.get_conf('pydocstyle/ignore', '').split(',')
            ds_select = self.get_conf('pydocstyle/select', '').split(',')
            ds_add_ignore = []
            ds_add_select = []
        else:
            ds_ignore = []
            ds_select = []
            ds_add_ignore = self.get_conf('pydocstyle/ignore', '').split(',')
            ds_add_select = self.get_conf('pydocstyle/select', '').split(',')

        pydocstyle = {
            'enabled': self.get_conf('pydocstyle'),
            'convention': convention,
            'addIgnore': [ignore.strip()
                          for ignore in ds_add_ignore if ignore],
            'addSelect': [select.strip()
                          for select in ds_add_select if select],
            'ignore': [ignore.strip() for ignore in ds_ignore if ignore],
            'select': [select.strip() for select in ds_select if select],
            'match': self.get_conf('pydocstyle/match'),
            'matchDir': self.get_conf('pydocstyle/match_dir')
        }

        # Autoformatting configuration
        formatter = self.get_conf('formatting')
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
        group_cells = self.get_conf(
            'group_cells',
            section='outline_explorer'
        )
        display_block_comments = self.get_conf(
            'show_comments',
            section='outline_explorer'
        )
        pyls_spyder_options = {
            'enable_block_comments': display_block_comments,
            'group_cells': group_cells
        }

        # Jedi configuration
        if self.get_conf('default', section='main_interpreter'):
            environment = None
            env_vars = None
        else:
            environment = self.get_conf('custom_interpreter',
                                        section='main_interpreter')
            env_vars = os.environ.copy()
            # external interpreter should not use internal PYTHONPATH
            env_vars.pop('PYTHONPATH', None)
            if running_in_mac_app():
                env_vars.pop('PYTHONHOME', None)

        jedi = {
            'environment': environment,
            'extra_paths': self.get_conf('spyder_pythonpath',
                                         section='main', default=[]),
            'env_vars': env_vars,
        }
        jedi_completion = {
            'enabled': self.get_conf('code_completion'),
            'include_params': self.get_conf('enable_code_snippets',
                                            section='completions')
        }
        jedi_signature_help = {
            'enabled': self.get_conf('jedi_signature_help')
        }
        jedi_definition = {
            'enabled': self.get_conf('jedi_definition'),
            'follow_imports': self.get_conf('jedi_definition/follow_imports')
        }

        # Advanced
        external_server = self.get_conf('advanced/external')
        stdio = self.get_conf('advanced/stdio')

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
        plugins['preload']['modules'] = self.get_conf('preload_modules')

        for formatter in formatters:
            plugins[formatter] = formatter_options[formatter]

        return python_config
