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
from qtpy.QtWidgets import QHBoxLayout, QWidget

# Local imports
from spyder.api.translations import get_translation
from spyder.config.manager import CONF
from spyder.config.gui import get_color_scheme
from spyder.plugins.framesexplorer.widgets.framesbrowser import (
    FramesBrowser,
    FramesBrowserFinder,
    VALID_VARIABLE_CHARS)
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


class FramesExplorerContextMenuActions:
    ViewLocalsAction = 'view_locals_action'


class FramesExplorerContextMenuSections:
    Locals = 'locals_section'


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

        # --- Finder
        self.finder = None

    def set_namespace_view(self, view):
        self.current_widget().shellwidget.set_namespace_view(view)

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
            toggled=self.show_finder,
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

    # ---- Stack accesors
    # ------------------------------------------------------------------------

    def update_finder(self, nsb, old_nsb):
        """Initialize or update finder widget."""
        if self.finder is None:
            # Initialize finder/search related widgets
            self.finder = QWidget(self)
            self.text_finder = FramesBrowserFinder(
                nsb.results_browser,
                callback=nsb.results_browser.set_regex,
                main=nsb,
                regex_base=VALID_VARIABLE_CHARS)
            self.finder.text_finder = self.text_finder
            self.finder_close_button = self.create_toolbutton(
                'close_finder',
                triggered=self.hide_finder,
                icon=self.create_icon('DialogCloseButton'),
            )

            finder_layout = QHBoxLayout()
            finder_layout.addWidget(self.finder_close_button)
            finder_layout.addWidget(self.text_finder)
            finder_layout.setContentsMargins(0, 0, 0, 0)
            self.finder.setLayout(finder_layout)

            layout = self.layout()
            layout.addSpacing(1)
            layout.addWidget(self.finder)
        else:
            # Just update references to the same text_finder (Custom QLineEdit)
            # widget to the new current FramesBrowser and save current
            # finder state in the previous FramesBrowser
            if old_nsb is not None:
                self.save_finder_state(old_nsb)
            self.text_finder.update_parent(
                nsb.results_browser,
                callback=nsb.results_browser.set_regex,
                main=nsb,
            )

    # ---- Public API
    # ------------------------------------------------------------------------

    def create_new_widget(self, shellwidget):
        color_scheme = get_color_scheme(
            CONF.get('appearance', 'selected'))
        nsb = FramesBrowser(self, color_scheme=color_scheme)
        nsb.edit_goto.connect(self.edit_goto)
        nsb.sig_show_namespace.connect(self.set_namespace_view)
        nsb.sig_hide_finder_requested.connect(self.hide_finder)
        nsb.sig_update_postmortem_requested.connect(self.update_postmortem)
        nsb.set_shellwidget(shellwidget)
        nsb.setup()
        self._set_actions_and_menus(nsb)
        return nsb

    def switch_widget(self, nsb, old_nsb):
        """
        Set the current FramesBrowser.

        This also setup the finder widget to work with the current
        FramesBrowser.
        """
        self.update_finder(nsb, old_nsb)
        finder_visible = nsb.set_text_finder(self.text_finder)
        self.finder.setVisible(finder_visible)
        search_action = self.get_action(FramesExplorerWidgetActions.Search)
        search_action.setChecked(finder_visible)
        old_nsb.sig_update_postmortem_requested.disconnect(
            self.update_postmortem)
        nsb.sig_update_postmortem_requested.connect(
            self.update_postmortem)
        self.update_postmortem()

    def close_widget(self, nsb):
        nsb.edit_goto.disconnect(self.edit_goto)
        nsb.sig_show_namespace.disconnect(self.set_namespace_view)
        nsb.sig_hide_finder_requested.disconnect(self.hide_finder)
        nsb.sig_update_postmortem_requested.disconnect(self.update_postmortem)
        nsb.close()

    @Slot(bool)
    def show_finder(self, checked):
        if self.count():
            nsb = self.current_widget()
            if checked:
                self.finder.text_finder.setText(nsb.last_find)
            else:
                self.save_finder_state(nsb)
                self.finder.text_finder.setText('')
            self.finder.setVisible(checked)
            if self.finder.isVisible():
                self.finder.text_finder.setFocus()
            else:
                nsb.results_browser.setFocus()

    @Slot()
    def update_postmortem(self):
        """Enable and disable post mortem action."""
        self.postmortem_debug_action.setEnabled(
            self.current_widget().post_mortem)

    @Slot()
    def hide_finder(self):
        action = self.get_action(FramesExplorerWidgetActions.Search)
        action.setChecked(False)
        nsb = self.current_widget()
        self.save_finder_state(nsb)
        self.finder.text_finder.setText('')

    def save_finder_state(self, nsb):
        """
        Save finder state (last input text and visibility).

        The values are saved in the given FramesBrowser.
        """
        last_find = self.text_finder.text()
        finder_visibility = self.finder.isVisible()
        nsb.save_finder_state(last_find, finder_visibility)

    def view_item_locals(self):
        self.current_widget().results_browser.view_item_locals()

    def _set_actions_and_menus(self, nsb):
        """
        Set actions and menus created here and used by the frames
        browser.

        Although this is not ideal, it's necessary to be able to use
        the CollectionsEditor widget separately from this plugin.
        """
        results_browser = nsb.results_browser

        # Actions
        results_browser.view_locals_action = self.view_locals_action

        # Menus
        results_browser.menu = self.context_menu
        results_browser.empty_ws_menu = self.empty_context_menu
