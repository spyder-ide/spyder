# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
General Spyder completion API constants and enumerations.

The constants and enums presented on this file are Spyder-specific 
extensions for the Language Server Protocol.
"""

# Standard library imports
from __future__ import annotations
from typing import Any, Optional, Tuple, TYPE_CHECKING, Union

# Third party imports
from lsprotocol.types import SymbolKind
from qtpy import PYSIDE6
from qtpy.QtCore import Signal, QObject, Slot, Qt

# Local imports
from spyder.api.config.mixins import SpyderConfigurationObserver

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

    from spyder.api.widgets.status import StatusBarWidget

# Supported LSP programming languages
SUPPORTED_LANGUAGES = [
    'Bash', 'C#', 'Cpp', 'CSS/LESS/SASS', 'Go', 'GraphQL', 'Groovy', 'Elixir',
    'Erlang', 'Fortran', 'Haxe', 'HTML', 'Java', 'JavaScript', 'JSON',
    'Julia', 'Kotlin', 'OCaml', 'PHP', 'R', 'Rust', 'Scala', 'Swift',
    'TypeScript'
]

# ---- Spyder-specific symbol kind extensions (not in the LSP spec) -----------

#: Integer sentinel for block comments in the outline explorer.
SYMBOL_KIND_BLOCK_COMMENT = 224
#: Integer sentinel for notebook cells in the outline explorer.
SYMBOL_KIND_CELL = 225

# Mapping between SymbolKind values and icon identifiers used by the UI.
SYMBOL_KIND_ICON = {
    SymbolKind.File: 'file',
    SymbolKind.Module: 'module',
    SymbolKind.Namespace: 'namespace',
    SymbolKind.Package: 'package',
    SymbolKind.Class: 'class',
    SymbolKind.Method: 'method',
    SymbolKind.Property: 'property',
    SymbolKind.Field: 'field',
    SymbolKind.Constructor: 'constructor',
    SymbolKind.Enum: 'enum',
    SymbolKind.Interface: 'interface',
    SymbolKind.Function: 'function',
    SymbolKind.Variable: 'variable',
    SymbolKind.Constant: 'constant',
    SymbolKind.String: 'string',
    SymbolKind.Number: 'number',
    SymbolKind.Boolean: 'boolean',
    SymbolKind.Array: 'array',
    SymbolKind.Object: 'object',
    SymbolKind.Key: 'key',
    SymbolKind.Null: 'null',
    SymbolKind.EnumMember: 'enum_member',
    SymbolKind.Struct: 'struct',
    SymbolKind.Event: 'event',
    SymbolKind.Operator: 'operator',
    SymbolKind.TypeParameter: 'type_parameter',
    SYMBOL_KIND_BLOCK_COMMENT: 'blockcomment',
    SYMBOL_KIND_CELL: 'cell',
}

#: Spyder-specific LSP extension: cursor event notification method name.
#: There is no equivalent constant in ``lsprotocol.types``.
DOCUMENT_CURSOR_EVENT = 'textDocument/cursorEvent'

# ---------------------- INTERNAL CONSTANTS -------------------------


class ClientConstants:
    """Internal LSP Client constants."""
    CANCEL = 'lsp-cancel'


class WorkspaceUpdateKind:
    ADDITION = 'addition'
    DELETION = 'deletion'


# ---------------- OTHER GENERAL PURPOSE CONSTANTS ------------------
COMPLETION_ENTRYPOINT = 'spyder.completions'

# -------------- SPYDER COMPLETION PROVIDER INTERFACE ---------------

class CompletionConfigurationObserver(SpyderConfigurationObserver):
    """
    Extension to the :class:`spyder.api.config.mixins.SpyderConfigurationObserver`
    mixin implementation to consider a nested provider configuration.
    """

    def _gather_observers(self):
        """Gather all the methods decorated with `on_conf_change`."""
        for method_name in dir(self):
            # Avoid crash at startup due to MRO
            if PYSIDE6 and method_name in {
                # Method is debounced
                "interpreter_changed"
            }:
                continue

            method = getattr(self, method_name, None)
            if hasattr(method, '_conf_listen'):
                info = method._conf_listen
                if len(info) > 1:
                    self._multi_option_listeners |= {method_name}

                for section, option in info:
                    if section is None:
                        section = 'completions'
                        if option == '__section':
                            option = (
                                'provider_configuration',
                                self.COMPLETION_PROVIDER_NAME,
                                'values'
                            )
                        else:
                            option = self._wrap_provider_option(option)

                    section_listeners = self._configuration_listeners.get(
                        section, {})
                    option_listeners = section_listeners.get(option, [])
                    option_listeners.append(method_name)
                    section_listeners[option] = option_listeners
                    self._configuration_listeners[section] = section_listeners

    def _wrap_provider_option(self, option):
        if isinstance(option, tuple):
            option = (
                'provider_configuration',
                self.COMPLETION_PROVIDER_NAME,
                'values',
                *option
            )
        else:
            option = (
                'provider_configuration',
                self.COMPLETION_PROVIDER_NAME,
                'values',
                option
            )
        return option


class SpyderCompletionProvider(QObject, CompletionConfigurationObserver):
    """
    Spyder provider API for completion providers.

    All completion providers must implement this interface in order to interact
    with Spyder CodeEditor and Projects manager.
    """

    sig_response_ready = Signal(str, int, object)
    """
    This signal is used to send a response back to the completion manager.

    Parameters
    ----------
    completion_provider_name: str
        Name of the completion provider that produced this response.
    request_seq: int
        Sequence number for the request.
    response: object
        Actual request corpus response.  For completion requests this is a
        ``list[lsprotocol.types.CompletionItem]``; for other requests it is
        the corresponding lsprotocol response object (or ``None``).
    """

    sig_provider_ready = Signal(str)
    """
    This signal is used to indicate that the completion provider is ready
    to handle requests.

    Parameters
    ----------
    completion_provider_name: str
        Name of the completion provider.
    """

    sig_language_completions_available = Signal(object, str)
    """
    This signal is used to indicate that completion capabilities are supported
    for a given programming language.

    Parameters
    ----------
    completion_capabilities: lsprotocol.types.ServerCapabilities
        Server capabilities reported by the language server.
    language: str
        Name of the programming language whose completion capabilities are
        available.
    """

    sig_disable_provider = Signal(str)
    """
    This signal is used to indicate that a completion provider should be
    disabled.

    Parameters
    ----------
    completion_provider_name: str
        Name of the completion provider to disable.
    """

    sig_show_widget = Signal(object)
    """
    This signal is used to display a graphical widget such as a QMessageBox.

    Parameters
    ----------
    widget: Union[QWidget, Callable[[QWidget], QWidget]]
        Widget to display, its constructor should receive parent as its first
        and only argument.
    """

    sig_call_statusbar = Signal(str, str, tuple, dict)
    """
    This signal is used to call a remote method on a statusbar widget
    registered via the `STATUS_BAR_CLASSES` attribute.

    Parameters
    ----------
    statusbar_key: str
        Status bar key identifier that was registered on the
        `STATUS_BAR_CLASSES` attribute.
    method_name: str
        Name of the remote method defined on the statusbar.
    args: tuple
        Tuple with positional arguments to invoke the method.
    kwargs: dict
        Dictionary containing optional arguments to invoke the method.
    """

    sig_open_file = Signal(str)
    """
    This signal is used to open a file in the editor.

    Parameters
    ----------
    path: str
        Path to a file to open with the editor.
    """

    sig_stop_completions = Signal(str)
    """
    This signal is used to stop the completion services on Spyder plugins
    that depend on them.

    Parameters
    ----------
    language: str
        Name of the programming language whose completion services are going
        to be stopped.
    """

    sig_exception_occurred = Signal(dict)
    """
    This signal can be emitted to report an exception from any provider.

    Parameters
    ----------
    error_data: dict
        The dictionary containing error data. The expected keys are:
        >>> error_data= {
            "text": str,
            "is_traceback": bool,
            "repo": str,
            "title": str,
            "label": str,
            "steps": str,
        }

    Notes
    -----
    The `is_traceback` key indicates if `text` contains plain text or a
    Python error traceback.

    The `title` and `repo` keys indicate how the error data should
    customize the report dialog and Github error submission.

    The `label` and `steps` keys allow customizing the content of the
    error dialog.

    This signal is automatically connected to the main Spyder interface.
    """

    # ---------------------------- ATTRIBUTES ---------------------------------

    # Name of the completion provider
    # Status: Required
    COMPLETION_PROVIDER_NAME = None

    # Define the priority of this provider, with 1 being the highest one
    # Status: Required
    DEFAULT_ORDER = -1

    # Define if the provider response time is not constant and may take
    # a long time for some requests.
    SLOW = False

    # Define configuration options for the provider.
    # List of tuples with the first item being the option name and the second
    # one its default value.
    #
    # CONF_DEFAULTS_EXAMPLE = [
    #     ('option-1', 'some-value'),
    #     ('option-2': True)
    # ]
    CONF_DEFAULTS = []

    # IMPORTANT NOTES:
    # 1. If you want to *change* the default value of a current option, you
    #    need to do a MINOR update in config version, e.g. from 0.1.0 to 0.2.0
    # 2. If you want to *remove* options that are no longer needed or if you
    #    want to *rename* options, then you need to do a MAJOR update in
    #    version, e.g. from 0.1.0 to 1.0.0
    # 3. You don't need to touch this value if you're just adding a new option
    CONF_VERSION = "0.1.0"

    # Widget to be added as a tab in the "Completion and linting" entry of
    # Spyder Preferences dialog. This will allow users to graphically configure
    # the options declared by the provider.
    CONF_TABS = []

    # A list of status bars classes that the provider declares to
    # display on Spyder.
    #
    # Each status bar should correspond to a
    # :class:`spyder.api.widgets.status.StatusBarWidget` or
    # a callable that returns a StatusBarWidget.
    #
    #
    # STATUS_BAR_CLASSES = [
    #     StatusBarClass1,
    #     StatusBarClass2,
    #     FunctionThatReturnsAStatusBar
    #     ...
    # ]
    STATUS_BAR_CLASSES: Union[
        StatusBarWidget, Callable[[QWidget], StatusBarWidget]
    ] = []

    def __init__(self, parent, config):
        """
        Main completion provider constructor.

        Parameters
        ----------
        parent: spyder.plugins.completion.plugin.CompletionPlugin
            Instance of the completion plugin that manages this provider
        config: dict
            Current provider configuration values, whose keys correspond to
            the ones defined on `CONF_DEFAULTS` and the values correspond to
            the current values according to the Spyder configuration system.
        """
        self.CONF_SECTION = (parent.CONF_SECTION
                             if parent is not None else 'completions')

        QObject.__init__(self, parent)
        CompletionConfigurationObserver.__init__(self)
        self.main = parent
        self.config = config

    def get_name(self) -> str:
        """Return a human readable name of the completion provider."""
        return ''

    def register_file(self, language: str, filename: str, codeeditor):
        """
        Register file to perform completions.
        If a language provider is not available for a given file, then this
        method should keep a queue, such that files can be initialized once
        a server is available.

        Parameters
        ----------
        language: str
            Programming language of the given file
        filename: str
            Filename to register
        codeeditor: spyder.plugins.editor.widgets.codeeditor.CodeEditor
            Codeeditor to send the provider configurations
        """
        pass

    def send_request(
            self, language: str, req_type: str, req: dict, req_id: int):
        """
        Send completion/introspection request from Spyder.
        The completion request `req_type` needs to have a response.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        req_type: str
            Type of request, one of
            ``lsprotocol.types`` LSP method name constants
        req: dict
            Request body
            {
                'filename': str,
                **kwargs: request-specific parameters
            }
        req_id: int
            Request identifier for response

        Notes
        -----
        A completion client should always reply to the
        `textDocument/completion` request, even if the answer is empty.
        """
        pass

    def send_notification(
            self, language: str, notification_type: str, notification: dict):
        """
        Send notification to completion server based on Spyder changes.
        All notifications sent won't return a response by the provider.

        Parameters
        ----------
        language: str
            Programming language for the incoming request
        notification_type: str
            Type of request, one of
            ``lsprotocol.types`` LSP method name constants
        notification: dict
            Request body
            {
                'filename': str,
                **kwargs: notification-specific parameters
            }
        """
        pass

    def broadcast_notification(
            self, notification_type: str, notification: dict):
        """
        Send a broadcast notification across all programming languages.

        Parameters
        ----------
        notification_type: str
            Type of request, one of
            :class:`spyder.plugins.completion.CompletionTypes`
        notification: dict
            Notification body
            {
                **kwargs: notification-specific parameters
            }
        """
        pass

    def send_response(self, response: object, resp_id: int):
        """
        Send response for server request.

        Parameters
        ----------
        response: object
            Response body for server.
        resp_id: int
            Request identifier for response
        """
        pass

    def project_path_update(self, project_path: str, update_kind: str,
                            instance: Any):
        """
        Handle project path updates on Spyder.

        Parameters
        ----------
        project_path: str
            Path to the project folder being added or removed.
        update_kind: str
            Path update kind, one of
            :class:`spyder.plugins.completion.api.WorkspaceUpdateKind`
        instance: object
            Reference to :class:`spyder.plugins.projects.plugin.Projects`
        """
        pass

    @Slot(object, bool)
    def python_path_update(self, new_path, prioritize):
        """
        Handle Python path updates on Spyder.

        Parameters
        ----------
        new_path: list of str
            Dictionary containing the current Python path values.
        prioritize: bool
            Whether to prioritize Python path values in sys.path
        """
        pass

    @Slot(str)
    def interpreter_changed(self, interpreter):
        """Handle changes to the Python interpreter used for completions."""
        pass

    def file_opened_closed_or_updated(self, filename: str, language: str):
        """
        Handle file modifications and file switching events, including when a
        new file is created.

        Parameters
        ----------
        filename: str
            Path to the file that was changed/opened/updated.
        language: str
            Name of the programming language of the file that was
            changed/opened/updated.
        """
        pass

    def start_completion_services_for_language(self, language: str) -> bool:
        """
        Start completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to start analyzing.

        Returns
        -------
        bool
            True if language provider could be started, otherwise False.
        """
        return False

    def stop_completion_services_for_language(self, language: str):
        """
        Stop completions/introspection services for a given language.

        Parameters
        ----------
        language: str
            Programming language to stop analyzing.
        """
        pass

    def start(self):
        """
        Start completion provider.

        The completion provider startup logic must be invoked on this method.

        Note: Once the completion provider is ready,
        the signal `sig_provider_ready` must be emitted with the completion
        provider name, e.g.,
        `self.sig_provider_ready.emit(self.COMPLETION_PROVIDER_NAME)`
        """
        raise NotImplementedError(
            'A completion provider must implement start()')

    def shutdown(self):
        """Stop completion provider."""
        pass

    def can_close(self) -> bool:
        """Establish if the current completion provider can be stopped."""
        return True

    def on_mainwindow_visible(self):
        """
        Actions to be performed after the main window has been shown.
        """
        pass

    def get_conf(self,
                 option_name: Union[str, Tuple[str, ...]],
                 default: Any = None,
                 section: Optional[str] = None) -> Any:
        """
        Retrieve an option value from the provider settings dictionary or
        the global Spyder configuration.

        Parameters
        ----------
        option_name: str
            Option name to lookup for in the provider settings
            dictionary/global Spyder configuration.
        default: Any
            Default value to return if `option_name` was not found.
        section: Optional[str]
            If None, then the option is retrieved from the local provider
            configuration. Otherwise, lookup on the global Spyder one.

        Returns
        -------
        Any
            Either the default value if `option_name` was not found on the
            settings or the actual stored value.
        """
        if section is None:
            section = 'completions'
            if isinstance(option_name, tuple):
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_PROVIDER_NAME,
                    'values',
                    *option_name
                )
            else:
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_PROVIDER_NAME,
                    'values',
                    option_name
                )
        return self.main.get_conf(
            option_name, default=default, section=section)

    def set_conf(self,
                 option_name: Union[str, Tuple[str, ...]],
                 value: Any,
                 section: Optional[str] = None,
                 recursive_notification: bool = True):
        """
        Set an option in the provider configuration settings dictionary or
        the global Spyder configuration.

        Parameters
        ----------
        option_name: str
            Option name to lookup for in the provider settings
            dictionary/global Spyder configuration.
        value: Any
            Value to set in the configuration system.
        section: Optional[str]
            If None, then the option is retrieved from the local provider
            configuration. Otherwise, lookup on the global Spyder one.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        """
        if section is None:
            section = 'completions'
            if isinstance(option_name, tuple):
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_PROVIDER_NAME,
                    'values',
                    *option_name
                )
            else:
                option_name = (
                    'provider_configuration',
                    self.COMPLETION_PROVIDER_NAME,
                    'values',
                    option_name
                )
        self.main.set_conf(option_name, value, section=section,
                           recursive_notification=recursive_notification)

    def create_action(self, name, text, icon=None, icon_text='', tip=None,
                      toggled=None, triggered=None, shortcut_context=None,
                      context=Qt.WidgetWithChildrenShortcut, initial=None,
                      register_shortcut=False):
        """
        name: str
            unique identifiable name for the action
        text: str
           Localized text for the action
        icon: QIcon,
            Icon for the action when applied to menu or toolbutton.
        icon_text: str
            Icon for text in toolbars. If True, this will also disable
            the tooltip on this toolbutton if part of a toolbar.
        tip: str
            Tooltip to define for action on menu or toolbar.
        toggled: callable
            The callable to use when toggling this action
        triggered: callable
            The callable to use when triggering this action.
        shortcut_context: str
            Set the `str` context of the shortcut.
        context: Qt.ShortcutContext
            Set the context for the shortcut.
        initial: object
            Sets the initial state of a togglable action. This does not emit
            the toggled signal.
        register_shortcut: bool, optional
            If True, main window will expose the shortcut in Preferences.
            The default value is `False`.

        Notes
        -----
        There is no need to set shortcuts right now. We only create actions
        with this (and similar methods) and these are then exposed as possible
        shortcuts on provider registration in the main window with the
        register_shortcut argument.

        If icon_text is True, this will also disable the tooltip.

        If a shortcut is found in the default config then it is assigned,
        otherwise it's left blank for the user to define one for it.
        """
        return self.main.create_action(
            name, text, icon=icon, icon_text=icon_text, tip=tip,
            toggled=toggled, triggered=triggered,
            shortcut_context=shortcut_context, context=context,
            initial=initial, register_shortcut=register_shortcut)

    def get_action(self, name, context=None, plugin=None):
        """
        Return an action by name, context and plugin.

        Parameters
        ----------
        name: str
            Name of the action to retrieve.
        context: Optional[str]
            Widget or context identifier under which the action was stored.
            If None, then `CONTEXT_NAME` is used instead
        plugin: Optional[str]
            Name of the plugin where the action was defined. If None, then
            `PLUGIN_NAME` is used.

        Returns
        -------
        action: SpyderAction
            The corresponding action stored under the given `name`, `context`
            and `plugin`.

        Raises
        ------
        KeyError
            If either of `name`, `context` or `plugin` keys do not exist in
            the toolbar registry.
        """
        return self.main.get_action(name, context=context, plugin=plugin)

    def create_application_menu(self, menu_id, title):
        """
        Create a Spyder application menu.

        Parameters
        ----------
        menu_id: str
            The menu unique identifier string.
        title: str
            The localized menu title to be displayed.
        """
        self.main.create_application_menu(menu_id, title)

    def create_menu(self, name, text=None, icon=None):
        """
        Create a menu.

        Parameters
        ----------
        name: str
            Unique str identifier.
        text: str or None
            Localized text string.
        icon: QIcon or None
            Icon to use for the menu.

        Return: QMenu
            Return the created menu.
        """
        self.main.create_menu(name, text=text, icon=icon)

    def get_menu(self, name, context: Optional[str] = None,
                 plugin: Optional[str] = None):
        """Retrieve a menu by its id."""
        if context is None and plugin is None:
            context = self.COMPLETION_PROVIDER_NAME
        return self.main.get_menu(name, context, plugin)

    def get_application_menu(self, menu_id):
        """
        Return an application menu by menu unique id.

        Parameters
        ----------
        menu_id: ApplicationMenu
            The menu unique identifier string.
        """
        return self.main.get_application_menu(menu_id)

    def add_item_to_menu(self, action_or_menu, menu, section=None,
                         before=None):
        """
        Add a SpyderAction or a QWidget to the menu.
        """
        self.main.add_item_to_menu(
            action_or_menu, menu, section=section, before=before)

    def add_item_to_application_menu(self, item, menu_id=None,
                                     section=None, before=None,
                                     before_section=None):
        """
        Add action or widget `item` to given application menu `section`.

        Parameters
        ----------
        item: SpyderAction or SpyderMenu
            The item to add to the `menu`.
        menu: ApplicationMenu or None
            Instance of a Spyder application menu.
        menu_id: str or None
            The application menu unique string identifier.
        section: str or None
            The section id in which to insert the `item` on the `menu`.
        before: str or None
            Make the item appear before another given item.
        before_section: Section or None
            Make the item section (if provided) appear before another
            given section.

        Notes
        -----
        Must provide a `menu` or a `menu_id`.
        """
        self.main.add_item_to_application_menu(
            item, menu_id=menu_id, section=section,
            before=before, before_section=before_section)

    def remove_item_from_application_menu(self, item_id: str,
                                          menu_id: Optional[str] = None):
        """
        Remove action or widget from given application menu by id.

        Parameters
        ----------
        item_id: str
            The item identifier to remove from the given menu.
        menu_id: str or None
            The application menu unique string identifier.
        """
        self.main.remove_item_from_application_menu(
            item_id, menu_id=menu_id)
