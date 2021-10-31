# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Frames Explorer Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.config.gui import get_color_scheme
from spyder.plugins.framesexplorer.widgets.framesbrowser import (
    FramesBrowser)
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget

# Localization
_ = get_translation('spyder')


# =============================================================================
# ---- Constants
# =============================================================================
class FramesExplorerWidgetActions:
    # Triggers
    Search = 'search'
    Refresh = 'refresh'
    PostMortemDebug = 'pmdebug'

    # Toggles
    ToggleExcludeInternal = 'toggle_exclude_internal_action'
    ToggleCaptureLocals = 'toggle_capture_locals_action'
    ToggleLocalsOnClick = 'toggle_show_locals_on_click_action'


class FramesExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class FramesExplorerWidgetMainToolBarSections:
    Main = 'main_section'


class FramesExplorerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class FramesExplorerContextMenuSections:
    Locals = 'locals_section'


class FramesExplorerContextMenuActions:
    ViewLocalsAction = 'view_locals_action'


# =============================================================================
# ---- Widgets
# =============================================================================


class FramesExplorerWidget(ShellConnectMainWidget):

    # PluginMainWidget class constants
    ENABLE_SPINNER = True

    # Signals
    edit_goto = Signal((str, int, str), (str, int, str, bool))

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self.context_menu = None
        self.empty_context_menu = None

    def postmortem(self):
        """Ask for post mortem debug."""
        self.current_widget().shellwidget.execute("%debug")

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Frames Explorer')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self):
        """Setup the widget."""
        # ---- Options menu actions
        exclude_internal_action = self.create_action(
            FramesExplorerWidgetActions.ToggleExcludeInternal,
            text=_("Exclude internal frames"),
            tip=_("Exclude frames that are not part of the user code"),
            toggled=True,
            option='exclude_internal',
        )

        capture_locals_action = self.create_action(
            FramesExplorerWidgetActions.ToggleCaptureLocals,
            text=_("Capture locals"),
            tip=_("Capture the variables in the Variable Explorer"),
            toggled=True,
            option='capture_locals',
        )

        show_locals_on_click_action = self.create_action(
            FramesExplorerWidgetActions.ToggleLocalsOnClick,
            text=_("Show locals on click"),
            tip=_("Show frame locals in the Variable explorer when selected."),
            toggled=True,
            option='show_locals_on_click',
        )

        # ---- Toolbar actions
        search_action = self.create_action(
            FramesExplorerWidgetActions.Search,
            text=_("Search frames"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )

        self.refresh_action = self.create_action(
            FramesExplorerWidgetActions.Refresh,
            text=_("Refresh frames"),
            icon=self.create_icon('refresh'),
            triggered=self.refresh,
            register_shortcut=True,
        )

        self.postmortem_debug_action = self.create_action(
            FramesExplorerWidgetActions.PostMortemDebug,
            text=_("Post-mortem debug"),
            icon=self.create_icon('debug'),
            triggered=self.postmortem,
            register_shortcut=True,
        )

        # ---- Context menu actions
        self.view_locals_action = self.create_action(
            FramesExplorerContextMenuActions.ViewLocalsAction,
            _("View variables with the Variable Explorer"),
            icon=self.create_icon('outline_explorer'),
            triggered=self.view_item_locals
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [
                exclude_internal_action,
                capture_locals_action,
                show_locals_on_click_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=FramesExplorerWidgetOptionsMenuSections.Display,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [search_action, self.refresh_action,
                     self.postmortem_debug_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=FramesExplorerWidgetMainToolBarSections.Main,
            )

        # ---- Context menu to show when there are frames present
        self.context_menu = self.create_menu(
            FramesExplorerWidgetMenus.PopulatedContextMenu)
        for item in [self.view_locals_action, self.refresh_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=FramesExplorerContextMenuSections.Locals,
            )

        # ---- Context menu when the frames explorer is empty
        self.empty_context_menu = self.create_menu(
            FramesExplorerWidgetMenus.EmptyContextMenu)
        for item in [self.refresh_action]:
            self.add_item_to_menu(
                item,
                menu=self.empty_context_menu,
                section=FramesExplorerContextMenuSections.Locals,
            )

    # ---- Public API
    # ------------------------------------------------------------------------

    def create_new_widget(self, shellwidget):
        """Create a new widget."""
        color_scheme = get_color_scheme(
            CONF.get('appearance', 'selected'))
        widget = FramesBrowser(
            self, shellwidget=shellwidget, color_scheme=color_scheme)

        widget.edit_goto.connect(self.edit_goto)
        widget.sig_show_namespace.connect(shellwidget.set_namespace_view)
        widget.sig_hide_finder_requested.connect(self.hide_finder)
        widget.sig_update_actions_requested.connect(self.update_actions)

        widget.setup()
        widget.set_context_menu(
            self.context_menu,
            self.empty_context_menu)

        widget.results_browser.view_locals_action = self.view_locals_action
        return widget

    def switch_widget(self, widget, old_widget):
        """
        Set the current FramesBrowser.

        This also setup the finder widget to work with the current
        FramesBrowser.
        """
        pass

    def close_widget(self, widget):
        """Close widget."""
        widget.edit_goto.disconnect(self.edit_goto)
        widget.sig_show_namespace.disconnect(
            widget.shellwidget.set_namespace_view)
        widget.sig_hide_finder_requested.disconnect(self.hide_finder)
        widget.sig_update_actions_requested.disconnect(self.update_actions)

        widget.close()

    @Slot(bool)
    def toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.toggle_finder(checked)

    @Slot()
    def hide_finder(self):
        """Hide finder."""
        action = self.get_action(FramesExplorerWidgetActions.Search)
        action.setChecked(False)

    def view_item_locals(self):
        """Request to view item locals."""
        self.current_widget().results_browser.view_item_locals()

    def update_actions(self):
        """Update actions."""
        widget = self.current_widget()
        search_action = self.get_action(FramesExplorerWidgetActions.Search)
        postmortem_debug_action = self.get_action(
            FramesExplorerWidgetActions.PostMortemDebug)
        if widget is None:
            checked = False
            post_mortem = False
        else:
            checked = widget.finder_is_visible()
            post_mortem = widget.post_mortem
        search_action.setChecked(checked)
        postmortem_debug_action.setEnabled(post_mortem)
