# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Variable Explorer Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import Qt, QTimer, Signal, Slot
from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets import (PluginMainWidget, PluginMainWidgetMenus,
                                SpyderWidgetMixin)
from spyder.config.base import CHECK_ALL, EXCLUDED_NAMES
from spyder.plugins.variableexplorer.widgets.namespacebrowser import \
    NamespaceBrowser
from spyder.utils.programs import is_module_installed
from spyder_kernels.utils.nsview import REMOTE_SETTINGS

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class VariableExplorerWidgetActions:
    # Triggers
    ImportData = 'import_data_action'
    SaveData = 'save_data_action'
    SaveDataAs = 'save_data_as_action'
    ResetNamespace = 'reset_namespaces_action'
    Search = 'search_action'
    Refresh = 'refresh_action'
    CloseFinder = 'close_finder_action'

    # Toggles
    ToggleExcludePrivate = 'toggle_exclude_private_action_action'
    ToggleExcludeUpperCase = 'toggle_exclude_uppercase_action'
    ToggleExcludeCapitalized = 'toggle_exclude_capitalized_action'
    ToggleExcludeUnsupported = 'toggle_exclude_unsupported_action'
    ToggleExcludeCallablesAndModules = ('toggle_exclude_callables_'
                                        'and_modules_action')
    ToggleMinMax = 'toggle_minmax_action'


class VariableExplorerWidgetMenus:
    Context = 'context_menu'


class VariableExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class VariableExplorerWidgetMainToolBarSections:
    Main = 'main_section'


# --- Widgets
# ----------------------------------------------------------------------------
class NamespaceStackedWidget(QStackedWidget, SpyderWidgetMixin):
    # Signals
    sig_option_changed = Signal(str, object)
    sig_collapse = Signal()
    sig_free_memory_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

    def addWidget(self, widget):
        """
        Override Qt method.
        """
        if isinstance(widget, NamespaceBrowser):
            widget.sig_option_changed.connect(self.sig_option_changed)
            widget.sig_collapse.connect(self.sig_collapse)
            widget.sig_free_memory_requested.connect(
                self.sig_free_memory_requested)

        super().addWidget(widget)


class VariableExplorerWidget(PluginMainWidget):

    DEFAULT_OPTIONS = {
        'check_all': CHECK_ALL,
        'dataframe_format': '%.6g',
        'exclude_callables_and_modules': True,
        'exclude_capitalized': False,
        'exclude_private': True,
        'exclude_unsupported': False,
        'exclude_uppercase': True,
        'excluded_names': EXCLUDED_NAMES,
        'minmax': False,
        'show_callable_attributes': True,
        'show_special_attributes': False,
        'truncate': True,
        # IPythonConsole option
        'show_reset_namespace_warning': True,
        # Editor option
        'blank_spaces': True,
        'scroll_past_end': True,
        # Appearance option
        'color_theme': 'spyder/dark',
    }

    # Signals
    sig_collapse = Signal()
    sig_free_memory_requested = Signal()
    sig_option_changed = Signal(str, object)

    def __init__(self, name=None, plugin=None, parent=None,
                 options=DEFAULT_OPTIONS):
        super().__init__(name, plugin, parent, options)

        # Widgets
        self._stack = NamespaceStackedWidget(self)
        self._shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self._stack)
        self.setLayout(layout)

        # Signals
        self._stack.sig_collapse.connect(self.sig_collapse)
        self._stack.sig_free_memory_requested.connect(
            self.sig_free_memory_requested)
        self._stack.sig_option_changed.connect(self.sig_option_changed)

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Variable Explorer')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self, options):
        # Main menu actions
        exclude_private_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludePrivate,
            text=_("Exclude private references"),
            tip=_("Exclude references which name starts with an underscore"),
            toggled=lambda val: self.set_option('exclude_private', val),
            initial=self.get_option('minmax'),
        )
        exclude_uppercase_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUpperCase,
            text=_("Exclude all-uppercase references"),
            tip=_("Exclude references which name is uppercase"),
            toggled=lambda val: self.set_option('exclude_uppercase', val),
            initial=self.get_option('minmax'),
        )
        exclude_capitalized_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCapitalized,
            text=_("Exclude capitalized references"),
            tip=_("Exclude references which name starts with an "
                  "uppercase character"),
            toggled=lambda val: self.set_option('exclude_capitalized', val),
            initial=self.get_option('minmax'),
        )
        exclude_unsupported_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUnsupported,
            text=_("Exclude unsupported data types"),
            tip=_("Exclude references to data types that don't have "
                  "an specialized viewer or can't be edited."),
            toggled=lambda val: self.set_option('exclude_unsupported', val),
            initial=self.get_option('minmax'),
        )
        exclude_callables_and_modules_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCallablesAndModules,
            text=_("Exclude callables and modules"),
            tip=_("Exclude references to functions, modules and "
                  "any other callable."),
            toggled=lambda val:
                self.set_option('exclude_callables_and_modules', val),
            initial=self.get_option('minmax'),
        )
        show_minmax_action = self.create_action(
            VariableExplorerWidgetActions.ToggleMinMax,
            text=_("Show arrays min/max"),
            tip=_("TODO: "),
            toggled=lambda val: self.set_option('minmax', val),
            initial=self.get_option('minmax'),
        )

        # Toolbar actions
        import_data_action = self.create_action(
            VariableExplorerWidgetActions.ImportData,
            text=_('Import data'),
            icon=self.create_icon('fileimport'),
            triggered=lambda x: self.import_data(),
        )
        save_action = self.create_action(
            VariableExplorerWidgetActions.SaveData,
            text=_("Save data"),
            icon=self.create_icon('filesave'),
            triggered=lambda x: self.save_data(),
        )
        save_as_action = self.create_action(
            VariableExplorerWidgetActions.SaveDataAs,
            text=_("Save data as..."),
            icon=self.create_icon('filesaveas'),
            triggered=lambda x: self.save_data(),
        )
        reset_namespace_action = self.create_action(
            VariableExplorerWidgetActions.ResetNamespace,
            text=_("Remove all variables"),
            icon=self.create_icon('editdelete'),
            triggered=lambda x: self.reset_namespace(),
        )
        search_action = self.create_action(
            VariableExplorerWidgetActions.Search,
            text=_("Search variable names and types"),
            icon=self.create_icon('find'),
            toggled=lambda x: self.show_finder(),
        )
        refresh_action = self.create_action(
            VariableExplorerWidgetActions.Refresh,
            text=_("Refresh variables"),
            icon=self.create_icon('refresh'),
            triggered=lambda val: self.refresh_table(),
        )

        # Other actions
        self.create_action(
            VariableExplorerWidgetActions.CloseFinder,
            text=_('Close finder'),
            icon=self.create_icon('DialogCloseButton'),
            triggered=self.show_finder,
        )

        # Options menu
        options_menu = self.get_options_menu()
        self.add_item_to_menu(
            exclude_private_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Display,
        )
        self.add_item_to_menu(
            exclude_uppercase_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Display,
        )
        self.add_item_to_menu(
            exclude_capitalized_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Display,
        )
        self.add_item_to_menu(
            exclude_unsupported_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Display,
        )
        self.add_item_to_menu(
            exclude_callables_and_modules_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Display,
        )
        self.add_item_to_menu(
            show_minmax_action,
            menu=options_menu,
            section=VariableExplorerWidgetOptionsMenuSections.Highlight,
        )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        self.add_item_to_toolbar(
            import_data_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )
        self.add_item_to_toolbar(
            save_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )
        self.add_item_to_toolbar(
            save_as_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )
        self.add_item_to_toolbar(
            reset_namespace_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )
        self.add_item_to_toolbar(
            search_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )
        self.add_item_to_toolbar(
            refresh_action,
            toolbar=main_toolbar,
            section=VariableExplorerWidgetMainToolBarSections.Main,
        )

        save_action.setEnabled(False)

    def show_context_menu(self, qpoint):
        """
        Show context menu.
        """
        menu = self.get_menu(VariableExplorerWidgetMenus.Context)
        menu.popup(qpoint)

    def update_style(self):
        self._stack.setStyleSheet(
            "NamespaceStackedWidget {padding: 0px; border: 0px}")

    def update_actions(self):
        action = self.get_action(VariableExplorerWidgetActions.ToggleMinMax)
        action.setEnabled(is_module_installed('numpy'))
        nsb = self.current_widget()

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                if nsb:
                    action = self.get_action(
                        VariableExplorerWidgetActions.SaveData)
                    action.setEnabled(nsb.filename is not None)
                    nsb_actions = nsb.actions()

                    if action not in nsb_actions:
                        nsb.addAction(action)

    def on_option_update(self, option, value):
        for index in range(self.count()):
            widget = self._stack.widget(index)
            if widget:
                widget.setup({option: value})

    # @Slot(str, object)
    # def change_option(self, option_name, new_value):
    #     """
    #     Change a config option.

    #     This function is called if sig_option_changed is received. If the
    #     option changed is the dataframe format, then the leading '%'
    #     character
    #     is stripped (because it can't be stored in the user config). Then,
    #     the signal is emitted again, so that the new value is saved in the
    #     user config.
    #     """
    #     if option_name == 'dataframe_format':
    #         assert new_value.startswith('%')
    #         new_value = new_value[1:]

    #     self.sig_option_changed.emit(option_name, new_value)

    @Slot()
    def free_memory(self):
        """
        Free memory signal.
        """
        self.sig_free_memory.emit()
        QTimer.singleShot(self.INITIAL_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory.emit)
        QTimer.singleShot(self.SECONDARY_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory.emit)

    # --- Stack accesors
    # ------------------------------------------------------------------------
    def add_widget(self, nsb):
        self._stack.addWidget(nsb)

    def count(self):
        return self._stack.count()

    def current_widget(self):
        return self._stack.currentWidget()

    def remove_widget(self, nsb):
        self._stack.removeWidget(nsb)

    def set_current_widget(self, nsb):
        self._stack.setCurrentWidget(nsb)

    # --- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell with variable explorer.

        This function opens a new NamespaceBrowser for browsing the variables
        in the shell.
        """
        options = self.get_options()
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            NamespaceBrowser.DEFAULT_OPTIONS = self.DEFAULT_OPTIONS
            nsb = NamespaceBrowser(self, options=options)
            nsb.set_shellwidget(shellwidget)
            nsb.setup(options)
            # nsb.sig_option_changed.connect(self.change_option)
            # nsb.sig_free_memory.connect(self.free_memory)
            self.add_widget(nsb)
            self._shellwidgets[shellwidget_id] = nsb
            self.set_shellwidget(shellwidget_id)
            return nsb

    def remove_shellwidget(self, shellwidget):
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python-based console (it was a terminal)
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets.pop(shellwidget_id)
            self.remove_widget(nsb)
            nsb.close()

    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets[shellwidget_id]
            self.set_current_widget(nsb)

    # API: Actions
    def import_data(self, filenames=None):
        """
        Import data in current namespace.
        """
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table()
            nsb.import_data(filenames=filenames)

    def save_data(self):
        if self.count():
            nsb = self.current_widget()
            nsb.save_data()
            self.update_actions()

    def reset_namespace(self):
        if self.count():
            nsb = self.current_widget()
            nsb.reset_namespace()

    def show_finder(self):
        if self.count():
            nsb = self.current_widget()
            nsb.show_finder(True)

    def refresh_table(self, interrupt=True):
        if self.count():
            nsb = self.current_widget()
            nsb.refresh_table(interrupt)
