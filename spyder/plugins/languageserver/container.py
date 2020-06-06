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

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import PluginMainContainer
from spyder.config.lsp import PYTHON_CONFIG
from spyder.plugins.languageserver.api import LSP_LANGUAGES
from spyder.plugins.languageserver.client import LSPClient
from spyder.plugins.languageserver.provider import LanguageServerProvider
from spyder.plugins.languageserver.widgets.status import LSPStatusWidget
from spyder.widgets.helperwidgets import MessageCheckBox

# Logging
logger = logging.getLogger(__name__)

# Localization
_ = get_translation("spyder")

# Constants
_LANGUAGE_OPTIONS = {key.lower(): {} for key in LSP_LANGUAGES}


class LanguageServerContainer(PluginMainContainer):
    """
    Main container for the language server plugin.

    This class keeps references to the provider and the status widget
    and handles GUI operations.
    """

    DEFAULT_OPTIONS = {
        'localhost': ['127.0.0.1', 'localhost'],
        'max_restart_attempts': 5,
        'time_between_restarts_ms': 10000,
        'time_heartbeat_ms': 3000,
        'show_lsp_down_warning': True,
        # Python
        'pycodestyle': True,
        'pycodestyle/exclude': [],
        'pycodestyle/filename': [],
        'pycodestyle/select': [],
        'pycodestyle/ignore': [],
        'pycodestyle/max_line_length': [],
        'pyflakes': True,
        'pydocstyle': True,
        'pydocstyle/convention': '',
        'pydocstyle/ignore': [],
        'pydocstyle/select': [],
        'pydocstyle/match': [],
        'pydocstyle/match_dir': '',
        'default_interpreter': None,
        'custom_interpreter': None,
        'spyder_pythonpath': [],
        'code_completion': True,
        'code_snippets': True,
        'jedi_signature_help': True,
        'jedi_definition': True,
        'jedi_definition/follow_imports': True,
        'advanced/external': '',
        'advanced/stdio': '',
        'advanced/module': '',
        'advanced/host': '',
        'advanced/port': '',
        'preload_modules': '',
        # FIXME: Need to move python options to a dictionary as well
        # There is no reason to special case python
    }
    DEFAULT_OPTIONS.update(_LANGUAGE_OPTIONS)

    # --- Signals
    sig_register_client_instance_requested = Signal(LSPClient)
    """
    Request the registration of a client instance.

    Parameters
    ----------
    client_instance: spyder.plugins.languageserver.client.LSPClient
        Language server protocol client instante.
    """

    sig_stop_completion_services_requested = Signal(str)
    """
    Request to stop the completion sevices for `language`.

    Parameters
    ----------
    language: str
        Unique language identifier string. Should be lowercased.
    """

    sig_restart_requested = Signal()
    """Request a restart to the main application."""

    sig_exception_occurred = Signal(dict)
    """
    Report server errors in our error report dialog.

    Parameters
    ----------
    error_data: dict
        Example content
        `{"error": str, "is_traceback": bool, "is_pyls_error": bool}`.
    """

    def __init__(self, name, plugin, parent=None, options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent=parent, options=options)

        # Attributes
        self.show_no_external_server_warning = True

        # Widgets or Objects
        self.provider = LanguageServerProvider(self)
        self.status_widget = LSPStatusWidget(
            parent=self, statusbar=None, container=self)

        # Signals
        self.provider.sig_update_status_requested.connect(self.set_status)
        self.provider.sig_lsp_down_reported.connect(self.report_lsp_down)
        self.provider.sig_no_external_server_reported.connect(
            self.report_no_external_server)
        self.provider.sig_stop_completion_services_requested.connect(
            self.sig_stop_completion_services_requested)
        self.provider.sig_register_client_instance_requested.connect(
            self.sig_register_client_instance_requested)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def setup(self, options=DEFAULT_OPTIONS):
        pass
        # Restart Action?

    def update_actions(self):
        pass

    def on_option_update(self, option, value):
        if option in _LANGUAGE_OPTIONS:
            if value:
                self.provider.set_language_config(option, value)
        else:
            # FIXME: This is why it makes sense to have options in a dict
            # and not exposed on the first level
            self.provider.set_language_config(
                'python', self.generate_python_config())

    # --- Public API
    # ------------------------------------------------------------------------
    def set_status(self, language, status):
        """
        Show lsp client status for the current file.

        Parameters
        ----------
        language: str
            Language unique name identifier.
        status: str
            Status message to update on status widget.
        """
        self.status_widget.update_status(language, status)

    @Slot(str)
    def report_server_error(self, error):
        """
        Report server errors in our error report dialog.

        Parameters
        ----------
        error: str
            Error traceback.
        """
        error_data = {
            "error": error,
            "is_traceback": True,
            "is_pyls_error": True,
        }
        self.sig_exception_occurred.emit(error_data)

    def report_no_external_server(self, host, port, language):
        """
        Report that connection could not be established with an
        external server.

        Parameters
        ----------
        host: str
            Host of client.
        port: int
            Port number used by client.
        language: str
            Unique language identifier string. Should be lowercased.
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
            self,
            _("Warning"),
            warn_str
        )

        self.show_no_external_server_warning = False

    @Slot(str)
    def report_lsp_down(self, language):
        """
        Report that either the transport layer or the LSP server are down.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        self.set_status(language, _('down'))

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

        box = MessageCheckBox(icon=QMessageBox.Warning, parent=self)
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
            self.sig_restart_requested.emit()

    def update_root_path(self, language, root_path):
        """
        Set the current root path for the given language.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        root_path: str
            Current root path string for given `language`.
        """
        self.provider.set_root_path(language, root_path)

    def update_configuration(self):
        """
        Update configuration on all clients.
        """
        self.provider.update_configuration()

    def update_current_editor_language(self, language):
        """
        Update the current editor language string on the status widget.

        Parameters
        ----------
        language: str
            Unique language identifier string. Should be lowercased.
        """
        self.status_widget.update_current_editor_language(language)

    # --- Python specific methods
    # ------------------------------------------------------------------------
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
            'enabled': self.get_option('pyflakes'),
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

        # Jedi configuration
        if self.get_option('default_interpreter'):
            environment = None
        else:
            environment = self.get_option('custom_interpreter')

        jedi = {
            'environment': environment,
            'extra_paths': self.get_option('spyder_pythonpath')
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
        if host in self.get_option('localhost') and not stdio:
            python_config['args'] = ('--host {host} --port {port} --tcp '
                                     '--check-parent-process')
        else:
            python_config['args'] = '--check-parent-process'

        python_config['external'] = external_server
        python_config['stdio'] = stdio
        python_config['host'] = host
        python_config['port'] = port

        plugins = python_config['configurations']['pyls']['plugins']
        plugins['pycodestyle'] = pycodestyle
        plugins['pyflakes'] = pyflakes
        plugins['pydocstyle'] = pydocstyle
        plugins['jedi'] = jedi
        plugins['jedi_completion'] = jedi_completion
        plugins['jedi_signature_help'] = jedi_signature_help
        plugins['jedi_definition'] = jedi_definition
        plugins['preload']['modules'] = self.get_option('preload_modules')

        return python_config
