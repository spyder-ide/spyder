# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Plots Main Widget.
"""

# Third party imports
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QSpinBox

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidgetMenus
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.plugins.plots.widgets.figurebrowser import FigureBrowser
from spyder.utils.misc import getcwd_or_home
from spyder.utils.palette import QStylePalette
from spyder.widgets.helperwidgets import PaneEmptyWidget


MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1


# --- Constants
# ----------------------------------------------------------------------------
class PlotsWidgetActions:
    # Triggers
    Save = 'save'
    SaveAll = 'save all'
    Copy = 'copy'
    Close = 'close'
    CloseAll = 'close all'
    MoveToPreviousFigure = 'previous figure'
    MoveToNextFigure = 'next figure'
    ZoomIn = 'zoom in'
    ZoomOut = 'zoom out'

    # Toggles
    ToggleMuteInlinePlotting = 'toggle_mute_inline_plotting_action'
    ToggleShowPlotOutline = 'toggle_show_plot_outline_action'
    ToggleAutoFitPlotting = 'toggle_auto_fit_plotting_action'


class PlotsWidgetMainToolbarSections:
    Edit = 'edit_section'
    Move = 'move_section'
    Zoom = 'zoom_section'


class PlotsWidgetToolbarItems:
    ZoomSpinBox = 'zoom_spin'


# --- Widgets
# ----------------------------------------------------------------------------
class PlotsWidget(ShellConnectMainWidget):
    sig_figure_loaded = Signal()
    """This signal is emitted when a figure is loaded succesfully"""

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self.zoom_disp = QSpinBox(self)
        self.zoom_disp.ID = PlotsWidgetToolbarItems.ZoomSpinBox
        self._right_clicked_thumbnail = None

        # Widget setup
        self.zoom_disp.setAlignment(Qt.AlignCenter)
        self.zoom_disp.setButtonSymbols(QSpinBox.NoButtons)
        self.zoom_disp.setReadOnly(True)
        self.zoom_disp.setSuffix(' %')
        self.zoom_disp.setRange(0, 9999)
        self.zoom_disp.setValue(100)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Plots')

    def get_focus_widget(self):
        widget = self.current_widget()
        if widget and widget.thumbnails_sb.current_thumbnail is not None:
            if widget.figviewer.figcanvas.fig:
                widget = widget.thumbnails_sb.scrollarea

        return widget

    def setup(self):
        # Menu actions
        self.mute_action = self.create_action(
            name=PlotsWidgetActions.ToggleMuteInlinePlotting,
            text=_("Mute inline plotting"),
            tip=_("Mute inline plotting in the ipython console."),
            toggled=True,
            initial=self.get_conf('mute_inline_plotting'),
            option='mute_inline_plotting'
        )
        self.outline_action = self.create_action(
            name=PlotsWidgetActions.ToggleShowPlotOutline,
            text=_("Show plot outline"),
            tip=_("Show the plot outline."),
            toggled=True,
            initial=self.get_conf('show_plot_outline'),
            option='show_plot_outline'
        )
        self.fit_action = self.create_action(
            name=PlotsWidgetActions.ToggleAutoFitPlotting,
            text=_("Fit plots to window"),
            tip=_("Automatically fit plots to Plot pane size."),
            toggled=True,
            initial=self.get_conf('auto_fit_plotting'),
            option='auto_fit_plotting'
        )

        # Toolbar actions
        save_action = self.create_action(
            name=PlotsWidgetActions.Save,
            text=_("Save plot as..."),
            tip=_("Save plot as..."),
            icon=self.create_icon('filesave'),
            triggered=self.save_plot,
            register_shortcut=True,
        )
        save_all_action = self.create_action(
            name=PlotsWidgetActions.SaveAll,
            text=_("Save all plots..."),
            tip=_("Save all plots..."),
            icon=self.create_icon('save_all'),
            triggered=self.save_all_plots,
            register_shortcut=True,
        )
        copy_action = self.create_action(
            name=PlotsWidgetActions.Copy,
            text=_("Copy image"),
            tip=_("Copy plot to clipboard as image"),
            icon=self.create_icon('editcopy'),
            triggered=self.copy_image,
            register_shortcut=True,
        )
        remove_action = self.create_action(
            name=PlotsWidgetActions.Close,
            text=_("Remove plot"),
            icon=self.create_icon('editclear'),
            triggered=self.remove_plot,
            register_shortcut=True,
        )
        remove_all_action = self.create_action(
            name=PlotsWidgetActions.CloseAll,
            text=_("Remove all plots"),
            tip=_("Remove all plots"),
            icon=self.create_icon('filecloseall'),
            triggered=self.remove_all_plots,
            register_shortcut=True,
        )
        previous_action = self.create_action(
            name=PlotsWidgetActions.MoveToPreviousFigure,
            text=_("Previous plot"),
            tip=_("Previous plot"),
            icon=self.create_icon('previous'),
            triggered=self.previous_plot,
            register_shortcut=True,
        )
        next_action = self.create_action(
            name=PlotsWidgetActions.MoveToNextFigure,
            text=_("Next plot"),
            tip=_("Next plot"),
            icon=self.create_icon('next'),
            triggered=self.next_plot,
            register_shortcut=True,
        )
        zoom_in_action = self.create_action(
            name=PlotsWidgetActions.ZoomIn,
            text=_("Zoom in"),
            tip=_("Zoom in"),
            icon=self.create_icon('zoom_in'),
            triggered=self.zoom_in,
            register_shortcut=True,
        )
        zoom_out_action = self.create_action(
            name=PlotsWidgetActions.ZoomOut,
            text=_("Zoom out"),
            tip=_("Zoom out"),
            icon=self.create_icon('zoom_out'),
            triggered=self.zoom_out,
            register_shortcut=True,
        )

        # Options menu
        options_menu = self.get_options_menu()
        self.add_item_to_menu(self.mute_action, menu=options_menu)
        self.add_item_to_menu(self.outline_action, menu=options_menu)
        self.add_item_to_menu(self.fit_action, menu=options_menu)

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [save_action, save_all_action, copy_action, remove_action,
                     remove_all_action, previous_action, next_action,
                     zoom_in_action, zoom_out_action, self.zoom_disp]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=PlotsWidgetMainToolbarSections.Edit,
            )

        # Context menu
        context_menu = self.create_menu(PluginMainWidgetMenus.Context)
        for item in [save_action, copy_action, remove_action]:
            self.add_item_to_menu(item, menu=context_menu)

    def update_actions(self):
        value = False
        widget = self.current_widget()
        figviewer = None
        if widget and not self.is_current_widget_empty():
            figviewer = widget.figviewer
            thumbnails_sb = widget.thumbnails_sb
            value = figviewer.figcanvas.fig is not None

            widget.set_pane_empty(not value)
        for __, action in self.get_actions().items():
            try:
                if action and action not in [self.mute_action,
                                             self.outline_action,
                                             self.fit_action,
                                             self.undock_action,
                                             self.close_action,
                                             self.dock_action,
                                             self.toggle_view_action,
                                             self.lock_unlock_action]:
                    action.setEnabled(value)

                    # IMPORTANT: Since we are defining the main actions in here
                    # and the context is WidgetWithChildrenShortcut we need to
                    # assign the same actions to the children widgets in order
                    # for shortcuts to work
                    if figviewer:
                        figviewer_actions = figviewer.actions()
                        thumbnails_sb_actions = thumbnails_sb.actions()

                        if action not in figviewer_actions:
                            figviewer.addAction(action)

                        if action not in thumbnails_sb_actions:
                            thumbnails_sb.addAction(action)
            except (RuntimeError, AttributeError):
                pass

        self.zoom_disp.setEnabled(value)

        # Disable zoom buttons if autofit
        if value:
            value = not self.get_conf('auto_fit_plotting')
            self.get_action(PlotsWidgetActions.ZoomIn).setEnabled(value)
            self.get_action(PlotsWidgetActions.ZoomOut).setEnabled(value)
            self.zoom_disp.setEnabled(value)

    @on_conf_change(option=['auto_fit_plotting', 'mute_inline_plotting',
                            'show_plot_outline', 'save_dir'])
    def on_section_conf_change(self, option, value):
        for index in range(self.count()):
            widget = self._stack.widget(index)
            if widget:
                widget.setup({option: value})
                self.update_actions()

    # ---- Public API
    # ------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        fig_browser = FigureBrowser(parent=self,
                                    background_color=MAIN_BG_COLOR)
        fig_browser.set_shellwidget(shellwidget)
        fig_browser.sig_redirect_stdio_requested.connect(
            self.sig_redirect_stdio_requested)

        fig_browser.sig_figure_menu_requested.connect(
            self.show_figure_menu)
        fig_browser.sig_thumbnail_menu_requested.connect(
            self.show_thumbnail_menu)
        fig_browser.sig_figure_loaded.connect(self.update_actions)
        fig_browser.sig_save_dir_changed.connect(
            lambda val: self.set_conf('save_dir', val))
        fig_browser.sig_zoom_changed.connect(self.zoom_disp.setValue)
        return fig_browser

    def close_widget(self, fig_browser):
        fig_browser.sig_redirect_stdio_requested.disconnect(
            self.sig_redirect_stdio_requested)

        fig_browser.sig_figure_menu_requested.disconnect(
            self.show_figure_menu)
        fig_browser.sig_thumbnail_menu_requested.disconnect(
            self.show_thumbnail_menu)
        fig_browser.sig_figure_loaded.disconnect(self.update_actions)
        fig_browser.sig_save_dir_changed.disconnect()
        fig_browser.sig_zoom_changed.disconnect(self.zoom_disp.setValue)
        fig_browser.close()
        fig_browser.setParent(None)

    def switch_widget(self, fig_browser, old_fig_browser):
        option_keys = [('auto_fit_plotting', True),
                       ('mute_inline_plotting', True),
                       ('show_plot_outline', True),
                       ('save_dir', getcwd_or_home())]

        conf_values = {k: self.get_conf(k, d) for k, d in option_keys}
        fig_browser.setup(conf_values)

    def show_figure_menu(self, qpoint):
        """
        Show main figure menu and display on given `qpoint`.

        Parameters
        ----------
        qpoint: QPoint
            The point to display the menu in global coordinated.
        """
        self._right_clicked_thumbnail = None
        widget = self.current_widget()
        if widget:
            self.get_menu(PluginMainWidgetMenus.Context).popup(qpoint)

    def show_thumbnail_menu(self, qpoint, thumbnail):
        """
        Show menu on a given `thumbnail` and display on given `qpoint`.

        Parameters
        ----------
        qpoint: QPoint
            The point to display the menu in global coordinated.
        """
        self._right_clicked_thumbnail = thumbnail
        widget = self.current_widget()
        if widget:
            self.get_menu(PluginMainWidgetMenus.Context).popup(qpoint)

    def save_plot(self):
        """
        Save currently active plot or plot selected to be saved with
        context menu in the thumbnails scrollbar.
        """
        widget = self.current_widget()
        if widget:
            if self._right_clicked_thumbnail is None:
                widget.thumbnails_sb.save_current_figure_as()
            else:
                widget.thumbnails_sb.save_thumbnail_figure_as(
                    self._right_clicked_thumbnail)
                # Reset the toolbar buttons to use the figviewer and not the thumbnail
                # selection
                self._right_clicked_thumbnail = None

    def save_all_plots(self):
        """Save all available plots."""
        widget = self.current_widget()
        if widget:
            widget.thumbnails_sb.save_all_figures_as()

    def copy_image(self):
        """
        Copy currently active plot or plot selected to be copied with
        context menu in the thumbnails scrollbar into the clipboard.
        """
        widget = self.current_widget()
        if widget and widget.figviewer and widget.figviewer.figcanvas.fig:
            if self._right_clicked_thumbnail is None:
                widget.figviewer.figcanvas.copy_figure()
            else:
                self._right_clicked_thumbnail.canvas.copy_figure()
                # Reset the toolbar buttons to use the figviewer and not the thumbnail
                # selection
                self._right_clicked_thumbnail = None

    def add_plot(self, fig, fmt, shellwidget):
        """
        Add a plot to the figure browser with the given shellwidget, if any.
        """
        fig_browser = self.get_widget_for_shellwidget(shellwidget)
        if fig_browser and not isinstance(fig_browser, PaneEmptyWidget):
            fig_browser.add_figure(fig, fmt)

    def remove_plot(self):
        """
        Remove currently active plot or plot selected to be removed with
        context menu in the thumbnails scrollbar.
        """
        widget = self.current_widget()
        if widget:
            if self._right_clicked_thumbnail is None:
                widget.thumbnails_sb.remove_current_thumbnail()
            else:
                widget.thumbnails_sb.remove_thumbnail(
                    self._right_clicked_thumbnail)
                # Reset the toolbar buttons to use the figviewer and not the thumbnail
                # selection
                self._right_clicked_thumbnail = None

        self.update_actions()

    def remove_all_plots(self):
        """Remove all available plots.."""
        widget = self.current_widget()
        if widget:
            widget.thumbnails_sb.remove_all_thumbnails()

        self.update_actions()

    def previous_plot(self):
        """Select the previous plot in the thumbnails scrollbar."""
        widget = self.current_widget()
        if widget:
            widget.thumbnails_sb.go_previous_thumbnail()

    def next_plot(self):
        """Select the next plot in the thumbnails scrollbar."""
        widget = self.current_widget()
        if widget:
            widget.thumbnails_sb.go_next_thumbnail()

    def zoom_in(self):
        """Perform a zoom in on the main figure."""
        widget = self.current_widget()
        if widget:
            widget.zoom_in()

    def zoom_out(self):
        """Perform a zoom out on the main figure."""
        widget = self.current_widget()
        if widget:
            widget.zoom_out()
