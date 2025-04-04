# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Variable Explorer Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import QTimer, Slot, Signal
from qtpy.QtWidgets import QAction

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.plugins.variableexplorer.widgets.namespacebrowser import (
    NamespaceBrowser)
from spyder.utils.icon_manager import ima
from spyder.utils.programs import is_module_installed


# =============================================================================
# ---- Constants
# =============================================================================
class VariableExplorerWidgetActions:
    # Triggers
    ImportData = 'import_data_action'
    SaveData = 'save_data_action'
    SaveDataAs = 'save_data_as_action'
    ResetNamespace = 'reset_namespaces_action'
    Search = 'search'
    Refresh = 'refresh'

    # Toggles
    ToggleExcludePrivate = 'toggle_exclude_private_action'
    ToggleExcludeUpperCase = 'toggle_exclude_uppercase_action'
    ToggleExcludeCapitalized = 'toggle_exclude_capitalized_action'
    ToggleExcludeUnsupported = 'toggle_exclude_unsupported_action'
    ToggleExcludeCallablesAndModules = (
        'toggle_exclude_callables_and_modules_action')
    ToggleMinMax = 'toggle_minmax_action'
    ToggleFilter = 'toggle_filter_variable_action'

    # Resize
    ResizeRowsAction = 'resize_rows_action'
    ResizeColumnsAction = 'resize_columns_action'


class VariableExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'
    Resize = 'resize_section'


class VariableExplorerWidgetMainToolBarSections:
    Main = 'main_section'


class VariableExplorerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class VariableExplorerContextMenuActions:
    PasteAction = 'paste_action'
    CopyAction = 'copy'
    EditAction = 'edit_action'
    PlotAction = 'plot_action'
    HistogramAction = 'histogram_action'
    ImshowAction = 'imshow_action'
    SaveArrayAction = 'save_array_action'
    InsertAction = 'insert_action'
    RemoveAction = 'remove_action'
    RenameAction = 'rename_action'
    DuplicateAction = 'duplicate_action'
    ViewAction = 'view_action'
    EditFiltersAction = 'edit_filters_action'


class VariableExplorerContextMenuSections:
    Edit = 'edit_section'
    Insert = 'insert_section'
    View = 'view_section'
    Filter = 'Filter_section'


# =============================================================================
# ---- Widgets
# =============================================================================

class VariableExplorerWidget(ShellConnectMainWidget):

    # PluginMainWidget class constants
    ENABLE_SPINNER = True

    # Other class constants
    INITIAL_FREE_MEMORY_TIME_TRIGGER = 60 * 1000  # ms
    SECONDARY_FREE_MEMORY_TIME_TRIGGER = 180 * 1000  # ms

    sig_open_preferences_requested = Signal()
    """
    Signal to open the variable explorer preferences.
    """

    sig_show_figure_requested = Signal(bytes, str, object)
    """
    This is emitted to request that a figure be shown in the Plots plugin.

    Parameters
    ----------
    image: bytes
        The image to show.
    mime_type: str
        The image's mime type.
    shellwidget: ShellWidget
        The shellwidget associated with the figure.
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self.context_menu = None
        self.empty_context_menu = None
        self.filter_button = None

        # Attributes
        self._is_filter_button_checked = True
        self.plots_plugin_enabled = False

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Variable Explorer')

    def setup(self):
        # ---- Options menu actions
        self.show_minmax_action = self.create_action(
            VariableExplorerWidgetActions.ToggleMinMax,
            text=_("Show arrays min/max"),
            tip=_("Show minimum and maximum of arrays"),
            toggled=True,
            option='minmax'
        )

        # ---- Toolbar actions
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

        # ---- Context menu actions
        resize_rows_action = self.create_action(
            VariableExplorerWidgetActions.ResizeRowsAction,
            text=_("Resize rows to contents"),
            icon=self.create_icon('collapse_row'),
            triggered=self.resize_rows
        )

        resize_columns_action = self.create_action(
            VariableExplorerWidgetActions.ResizeColumnsAction,
            _("Resize columns to contents"),
            icon=self.create_icon('collapse_column'),
            triggered=self.resize_columns
        )

        self.paste_action = self.create_action(
            VariableExplorerContextMenuActions.PasteAction,
            _("Paste"),
            icon=self.create_icon('editpaste'),
            triggered=self.paste
        )

        self.copy_action = self.create_action(
            VariableExplorerContextMenuActions.CopyAction,
            _("Copy"),
            icon=self.create_icon('editcopy'),
            triggered=self.copy
        )

        self.edit_action = self.create_action(
            VariableExplorerContextMenuActions.EditAction,
            _("Edit"),
            icon=self.create_icon('edit'),
            triggered=self.edit_item
        )

        self.plot_action = self.create_action(
            VariableExplorerContextMenuActions.PlotAction,
            _("Plot"),
            icon=self.create_icon('plot'),
            triggered=self.plot_item
        )
        self.plot_action.setVisible(False)

        self.hist_action = self.create_action(
            VariableExplorerContextMenuActions.HistogramAction,
            _("Histogram"),
            icon=self.create_icon('hist'),
            triggered=self.histogram_item
        )
        self.hist_action.setVisible(False)

        self.imshow_action = self.create_action(
            VariableExplorerContextMenuActions.ImshowAction,
            _("Show image"),
            icon=self.create_icon('imshow'),
            triggered=self.imshow_item
        )
        self.imshow_action.setVisible(False)

        self.save_array_action = self.create_action(
            VariableExplorerContextMenuActions.SaveArrayAction,
            _("Save array"),
            icon=self.create_icon('filesave'),
            triggered=self.save_array
        )
        self.save_array_action.setVisible(False)

        self.insert_action = self.create_action(
            VariableExplorerContextMenuActions.InsertAction,
            _("Insert"),
            icon=self.create_icon('insert'),
            triggered=self.insert_item
        )

        self.edit_filters = self.create_action(
            VariableExplorerContextMenuActions.EditFiltersAction,
            _("Edit filters"),
            icon=self.create_icon('filter'),
            triggered=self.sig_open_preferences_requested
        )

        self.remove_action = self.create_action(
            VariableExplorerContextMenuActions.RemoveAction,
            _("Remove"),
            icon=self.create_icon('editdelete'),
            triggered=self.remove_item
        )

        self.rename_action = self.create_action(
            VariableExplorerContextMenuActions.RenameAction,
            _("Rename"),
            icon=self.create_icon('rename'),
            triggered=self.rename_item
        )

        self.duplicate_action = self.create_action(
            VariableExplorerContextMenuActions.DuplicateAction,
            _("Duplicate"),
            icon=self.create_icon('edit_add'),
            triggered=self.duplicate_item
        )

        self.view_action = self.create_action(
            VariableExplorerContextMenuActions.ViewAction,
            _("View with the Object Explorer"),
            icon=self.create_icon('outline_explorer'),
            triggered=self.view_item
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [self.exclude_private_action,
                     self.exclude_uppercase_action,
                     self.exclude_capitalized_action,
                     self.exclude_unsupported_action,
                     self.exclude_callables_and_modules_action,
                     self.show_minmax_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=VariableExplorerWidgetOptionsMenuSections.Display,
            )

        self._enable_filter_actions(self.get_conf('filter_on'))

        # Resize
        for item in [resize_rows_action, resize_columns_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=VariableExplorerWidgetOptionsMenuSections.Resize,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [import_data_action, save_action, save_as_action,
                     reset_namespace_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=VariableExplorerWidgetMainToolBarSections.Main,
            )
        save_action.setEnabled(False)

        # Search, Filter and Refresh buttons are added in _setup()

        # ---- Context menu to show when there are variables present
        self.context_menu = self.create_menu(
            VariableExplorerWidgetMenus.PopulatedContextMenu)
        for item in [self.edit_action, self.copy_action, self.paste_action,
                     self.rename_action, self.remove_action,
                     self.save_array_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Edit,
            )

        for item in [self.insert_action, self.duplicate_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Insert,
            )

        for item in [self.edit_filters]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.Filter,
            )

        for item in [self.view_action, self.plot_action, self.hist_action,
                     self.imshow_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=VariableExplorerContextMenuSections.View,
            )

        # ---- Context menu when the variable explorer is empty
        self.empty_context_menu = self.create_menu(
            VariableExplorerWidgetMenus.EmptyContextMenu)
        for item in [self.insert_action, self.paste_action]:
            self.add_item_to_menu(
                item,
                menu=self.empty_context_menu,
                section=VariableExplorerContextMenuSections.Edit,
            )

    def _setup(self):
        """
        Create options menu and adjacent toolbar buttons, etc.

        This creates base actions related with Search, Filter and Refresh.

        This calls the parent's method to setup default actions, create the
        spinner and the options menu, and connect signals. After that, it adds
        the Search, Filter and Refresh buttons between the spinner and the
        options menu.
        """
        super()._setup()

        # ---- Base Options menu actions
        self.exclude_private_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludePrivate,
            text=_("Exclude private variables"),
            tip=_("Exclude variables that start with an underscore"),
            toggled=True,
            option='exclude_private',
        )

        self.exclude_uppercase_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUpperCase,
            text=_("Exclude all-uppercase variables"),
            tip=_("Exclude variables whose name is uppercase"),
            toggled=True,
            option='exclude_uppercase',
        )

        self.exclude_capitalized_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCapitalized,
            text=_("Exclude capitalized variables"),
            tip=_("Exclude variables whose name starts with a capital "
                  "letter"),
            toggled=True,
            option='exclude_capitalized',
        )

        self.exclude_unsupported_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeUnsupported,
            text=_("Exclude unsupported data types"),
            tip=_("Exclude references to data types that don't have "
                  "an specialized viewer or can't be edited."),
            toggled=True,
            option='exclude_unsupported',
        )

        self.exclude_callables_and_modules_action = self.create_action(
            VariableExplorerWidgetActions.ToggleExcludeCallablesAndModules,
            text=_("Exclude callables and modules"),
            tip=_("Exclude references to functions, modules and "
                  "any other callable."),
            toggled=True,
            option='exclude_callables_and_modules'
        )

        # ---- Base Toolbar actions
        self.search_action = self.create_action(
            VariableExplorerWidgetActions.Search,
            text=_("Search variable names and types"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )

        self.refresh_action = self.create_action(
            VariableExplorerWidgetActions.Refresh,
            text=_("Refresh variables"),
            icon=self.create_icon('refresh'),
            triggered=self.refresh_table,
            register_shortcut=True,
        )

        self.filter_button = self.create_action(
            VariableExplorerWidgetActions.ToggleFilter,
            text="",
            icon=ima.icon('filter'),
            toggled=self._enable_filter_actions,
            option='filter_on',
            tip=_("Filter variables")
        )
        self.filter_button.setCheckable(True)
        self.filter_button.toggled.connect(self._set_filter_button_state)

        for action in [
            self.search_action,
            self.filter_button,
            self.refresh_action,
        ]:
            self.add_corner_widget(action, before=self._options_button)

    def update_actions(self):
        """Update the actions."""
        if self.is_current_widget_empty():
            self._set_main_toolbar_state(False)
            return
        else:
            self._set_main_toolbar_state(True)

        action = self.get_action(VariableExplorerWidgetActions.ToggleMinMax)
        action.setEnabled(is_module_installed('numpy'))

        nsb = self.current_widget()
        if nsb:
            save_data_action = self.get_action(
                VariableExplorerWidgetActions.SaveData)
            save_data_action.setEnabled(nsb.filename is not None)

        search_action = self.get_action(VariableExplorerWidgetActions.Search)
        if nsb is None:
            checked = False
        else:
            checked = nsb.finder_is_visible()
        search_action.setChecked(checked)

    @on_conf_change
    def on_section_conf_change(self, section):
        for index in range(self.count()):
            widget = self._stack.widget(index)
            if widget:
                widget.setup()

    def set_plots_plugin_enabled(self, value: bool):
        """
        Change whether the Plots plugin is enabled.

        This stores the information in this widget and propagates it to every
        NamespaceBrowser.
        """
        self.plots_plugin_enabled = value
        for index in range(self.count()):
            nsb = self._stack.widget(index)
            if nsb:
                nsb.plots_plugin_enabled = value

    # ---- Stack accesors
    # ------------------------------------------------------------------------
    def switch_widget(self, nsb, old_nsb):
        """Set the current NamespaceBrowser."""
        pass

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        """Create new NamespaceBrowser."""
        nsb = NamespaceBrowser(self)
        nsb.sig_hide_finder_requested.connect(self.hide_finder)
        nsb.sig_free_memory_requested.connect(self.free_memory)
        nsb.sig_start_spinner_requested.connect(self.start_spinner)
        nsb.sig_stop_spinner_requested.connect(self.stop_spinner)
        nsb.sig_show_figure_requested.connect(self.sig_show_figure_requested)
        nsb.set_shellwidget(shellwidget)
        nsb.plots_plugin_enabled = self.plots_plugin_enabled
        nsb.setup()
        self._set_actions_and_menus(nsb)

        # To update the Variable Explorer after execution
        shellwidget.sig_kernel_state_arrived.connect(nsb.update_view)
        shellwidget.sig_config_spyder_kernel.connect(
            nsb.set_namespace_view_settings
        )
        return nsb

    def close_widget(self, nsb):
        """Close NamespaceBrowser."""
        nsb.sig_hide_finder_requested.disconnect(self.hide_finder)
        nsb.sig_free_memory_requested.disconnect(self.free_memory)
        nsb.sig_start_spinner_requested.disconnect(self.start_spinner)
        nsb.sig_stop_spinner_requested.disconnect(self.stop_spinner)
        nsb.sig_show_figure_requested.disconnect(
            self.sig_show_figure_requested)
        nsb.shellwidget.sig_kernel_state_arrived.disconnect(nsb.update_view)
        nsb.shellwidget.sig_config_spyder_kernel.disconnect(
            nsb.set_namespace_view_settings
        )

        nsb.close()
        nsb.setParent(None)

    def import_data(self, filenames=None):
        """
        Import data in current namespace.
        """
        if not self.is_current_widget_empty():
            nsb = self.current_widget()
            nsb.refresh_table()
            nsb.import_data(filenames=filenames)

    def save_data(self):
        if not self.is_current_widget_empty():
            nsb = self.current_widget()
            nsb.save_data()
            self.update_actions()

    def reset_namespace(self):
        if not self.is_current_widget_empty():
            nsb = self.current_widget()
            nsb.reset_namespace()

    @Slot(bool)
    def toggle_finder(self, checked):
        """Hide or show the finder."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return
        widget.toggle_finder(checked)

    @Slot()
    def hide_finder(self):
        """Hide the finder."""
        action = self.get_action(VariableExplorerWidgetActions.Search)
        action.setChecked(False)

    def refresh_table(self):
        if not self.is_current_widget_empty():
            nsb = self.current_widget()
            nsb.refresh_table()

    @Slot()
    def free_memory(self):
        """
        Free memory signal.
        """
        self.sig_free_memory_requested.emit()
        QTimer.singleShot(self.INITIAL_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory_requested)
        QTimer.singleShot(self.SECONDARY_FREE_MEMORY_TIME_TRIGGER,
                          self.sig_free_memory_requested)

    def resize_rows(self):
        if self._current_editor is not None:
            self._current_editor.resizeRowsToContents()

    def resize_columns(self):
        if self._current_editor is not None:
            self._current_editor.resize_column_contents()

    def paste(self):
        self._current_editor.paste()

    def copy(self):
        self._current_editor.copy()

    def edit_item(self):
        self._current_editor.edit_item()

    def plot_item(self):
        self._current_editor.plot_item('plot')

    def histogram_item(self):
        self._current_editor.plot_item('hist')

    def imshow_item(self):
        self._current_editor.imshow_item()

    def save_array(self):
        self._current_editor.save_array()

    def insert_item(self):
        self._current_editor.insert_item(below=False)

    def remove_item(self):
        self._current_editor.remove_item()

    def rename_item(self):
        self._current_editor.rename_item()

    def duplicate_item(self):
        self._current_editor.duplicate_item()

    def view_item(self):
        self._current_editor.view_item()

    # ---- Private API
    # ------------------------------------------------------------------------
    @property
    def _current_editor(self):
        editor = None
        if not self.is_current_widget_empty():
            nsb = self.current_widget()
            editor = nsb.editor
        return editor

    def _set_actions_and_menus(self, nsb):
        """
        Set actions and menus created here and used by the namespace
        browser editor.

        Although this is not ideal, it's necessary to be able to use
        the CollectionsEditor widget separately from this plugin.
        """
        editor = nsb.editor

        # Actions
        editor.paste_action = self.paste_action
        editor.copy_action = self.copy_action
        editor.edit_action = self.edit_action
        editor.plot_action = self.plot_action
        editor.hist_action = self.hist_action
        editor.imshow_action = self.imshow_action
        editor.save_array_action = self.save_array_action
        editor.insert_action = self.insert_action
        editor.remove_action = self.remove_action
        editor.rename_action = self.rename_action
        editor.duplicate_action = self.duplicate_action
        editor.view_action = self.view_action

        # Menus
        editor.menu = self.context_menu
        editor.empty_ws_menu = self.empty_context_menu

        # These actions are not used for dictionaries (so we don't need them
        # for namespaces) but we have to create them so they can be used in
        # several places in CollectionsEditor.
        editor.insert_action_above = QAction()
        editor.insert_action_below = QAction()

    def _enable_filter_actions(self, value):
        """Handle the change of the filter state."""
        self.exclude_private_action.setEnabled(value)
        self.exclude_uppercase_action.setEnabled(value)
        self.exclude_capitalized_action.setEnabled(value)
        self.exclude_unsupported_action.setEnabled(value)
        self.exclude_callables_and_modules_action.setEnabled(value)

    def _set_main_toolbar_state(self, enabled):
        """Set main toolbar enabled state."""
        main_toolbar = self.get_main_toolbar()
        for action in main_toolbar.actions():
            action.setEnabled(enabled)

        # Adjustments for the filter button
        if enabled:
            # Restore state for active consoles
            self.filter_button.setChecked(self._is_filter_button_checked)
        else:
            # Uncheck button for dead consoles if it's checked so that the
            # toolbar looks good
            if self.filter_button.isChecked():
                self.filter_button.setChecked(False)
                self._is_filter_button_checked = True

    def _set_filter_button_state(self, checked):
        """Keep track of the filter button checked state."""
        self._is_filter_button_checked = checked
