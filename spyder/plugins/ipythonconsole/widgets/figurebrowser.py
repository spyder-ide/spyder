# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between the IPython Console and
the Plots plugin
"""

# ---- Third party library imports
from qtconsole.rich_jupyter_widget import RichJupyterWidget

# ---- Local library imports
from spyder.config.base import _
from spyder.py3compat import decodebytes


class FigureBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to intercept the figures
    sent by the kernel to the IPython Console and send it to the plots plugin.
    This widget can also block the plotting of inline figures in the IPython
    Console so that figures are only plotted in the plots plugin.
    """

    # Reference to the figurebrowser widget connected to this client
    figurebrowser = None

    # ---- Public API
    def set_figurebrowser(self, figurebrowser):
        """Set the namespace for the figurebrowser widget."""
        self.figurebrowser = figurebrowser
        self.sended_render_message = False

    def display_data(self, fig_data):
        """Display data in figure browser."""
        if 'image/png' in fig_data:
            self.sig_new_inline_figure.emit(fig_data)

    # ---- Private API (overrode by us)
    def _handle_display_data(self, msg):
        """
        Reimplemented to handle communications between the figure explorer
        and the kernel.
        """
        if 'image/png' in msg['content']['data']:
            if (self.figurebrowser is not None and
                    self.figurebrowser.mute_inline_plotting):
                if not self.sended_render_message:
                    self._append_html(
                        _('<br><hr>'
                          '\nFigures now render in the Plots pane by default. '
                          'To make them also appear inline in the Console, '
                          'uncheck "Mute Inline Plotting" under the Plots '
                          'pane options menu. \n'
                          '<hr><br>'), before_prompt=True)
                    self.sended_render_message = True
                return
        return super(FigureBrowserWidget, self)._handle_display_data(msg)
