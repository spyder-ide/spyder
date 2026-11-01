# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Plots Plugin.
"""

# Standard library imports
from typing import Optional

# Local imports
from spyder.api.plugins import (
    ExposedCallError,
    Image,
    Plugins,
    SpyderDockablePlugin,
    expose,
)
from spyder.api.shellconnect.mixins import ShellConnectPluginMixin
from spyder.api.translations import _
from spyder.plugins.plots.widgets.main_widget import PlotsWidget


class Plots(SpyderDockablePlugin, ShellConnectPluginMixin):
    """
    Plots plugin.
    """
    NAME = 'plots'
    REQUIRES = [Plugins.IPythonConsole]
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = PlotsWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    def __init__(self, parent, configuration=None):
        SpyderDockablePlugin.__init__(self, parent, configuration)

        # Combined with ShellConnectPluginMixin via multiple inheritance;
        # set up its state here since SpyderDockablePlugin.__init__ doesn't
        # reach it.
        ShellConnectPluginMixin.__init__(self)

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _('Plots')

    @staticmethod
    def get_description():
        return _('View, browse and save generated figures.')

    @classmethod
    def get_icon(cls):
        return cls.create_icon('plot')

    def on_initialize(self):
        # If a figure is loaded, raise the dockwidget the first time
        # a plot is generated.
        self.get_widget().sig_figure_loaded.connect(self._on_first_plot)

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_plot(self, fig, fmt, shellwidget):
        """
        Add a plot to the specified figure browser.

        Add the plot to the figure browser with the given shellwidget. Also,
        bring the plugin to the front and raise the window that it is in so
        that the plot is shown.

        If no figure browser with the given shellwidget exists, then nothing
        happens.
        """
        self.switch_to_plugin(force_focus=False)
        self.get_widget().window().raise_()
        self.get_widget().add_plot(fig, fmt, shellwidget)

    def get_figures(self, shellwidget) -> list:
        """
        Get the figures shown for a console, oldest first.

        Parameters
        ----------
        shellwidget : ShellWidget
            Shellwidget of the console.

        Returns
        -------
        list[Image]
            The figures, in the format they were generated in (e.g. PNG or
            SVG).
        """
        return [
            self._canvas_to_image(canvas)
            for canvas in self._get_canvases(shellwidget)
        ]

    # ---- For outside callers (e.g. AI agents)
    # ------------------------------------------------------------------------
    @expose(read_only=True)
    def list_figures(self, console_id: Optional[str] = None) -> list:
        """
        List the figures shown in Spyder's Plots pane for a console, oldest
        first, with their index, format and size in pixels.

        Parameters
        ----------
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        canvases = self._get_canvases(self._get_shellwidget(console_id))
        figures = []
        for index, canvas in enumerate(canvases):
            size = canvas._qpix_orig.size()
            figures.append(
                {
                    "index": index,
                    "format": canvas.fmt,
                    "width": size.width(),
                    "height": size.height(),
                }
            )
        return figures

    @expose(read_only=True)
    def get_figure(
        self, index: int = -1, console_id: Optional[str] = None
    ) -> Image:
        """
        Get a figure from Spyder's Plots pane as an image, to look at plots
        generated in a console.

        Parameters
        ----------
        index : int, optional
            Index of the figure, as given by list_figures. Negative values
            count from the end, so -1 is the most recent figure.
        console_id : str, optional
            Id of the console, as returned by list_consoles. By default, the
            console currently selected in Spyder.
        """
        canvases = self._get_canvases(self._get_shellwidget(console_id))
        try:
            canvas = canvases[index]
        except IndexError:
            raise ExposedCallError(
                f"There's no figure with index {index}. There are "
                f"{len(canvases)} figures."
            ) from None
        return self._canvas_to_image(canvas)

    # ---- Private API
    # ------------------------------------------------------------------------
    def _get_shellwidget(self, console_id):
        """Get the shellwidget of a console for outside callers."""
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        shellwidget = ipyconsole.get_console_shellwidget(console_id)
        if shellwidget is None:
            if console_id is None:
                raise ExposedCallError("There are no IPython consoles open.")
            raise ExposedCallError(
                f"No console with id {console_id!r}. Use list_consoles to "
                f"get the available ids."
            )
        return shellwidget

    def _get_canvases(self, shellwidget) -> list:
        """Get the canvases of the figures shown for a console."""
        browser = self.get_widget().get_widget_for_shellwidget(shellwidget)
        if browser is None:
            return []
        return [
            thumbnail.canvas for thumbnail in browser.thumbnails_sb._thumbnails
        ]

    @staticmethod
    def _canvas_to_image(canvas) -> Image:
        data = canvas.fig
        if isinstance(data, str):
            data = data.encode("utf-8")
        return Image(data, canvas.fmt)

    def _on_first_plot(self):
        """Actions to execute after the first plot is generated."""
        # Only switch when inline plotting is muted. This avoids
        # showing the plugin when users want to only see plots in
        # the IPython console.
        # Fixes spyder-ide/spyder#15467
        if self.get_conf('mute_inline_plotting'):
            self.switch_to_plugin(force_focus=False)

        # We only give raise to the plugin once per session, to let users
        # know that plots are displayed in this plugin.
        # Fixes spyder-ide/spyder#15705
        self.get_widget().sig_figure_loaded.disconnect(self._on_first_plot)
