# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between the IPython Console and
the Plots plugin
"""

# ---- Standard library imports
from base64 import decodestring

# ---- Third party library imports
from qtconsole.rich_jupyter_widget import RichJupyterWidget

# ---- Local library imports
from spyder.config.base import _


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

    # ---- Private API (overrode by us)
    def _handle_display_data(self, msg):
        """
        Reimplemented to handle communications between the figure explorer
        and the kernel.
        """
        img = None
        data = msg['content']['data']
        if 'image/svg+xml' in data:
            fmt = 'image/svg+xml'
            img = data['image/svg+xml']
        elif 'image/png' in data:
            # PNG data is base64 encoded as it passes over the network
            # in a JSON structure so we decode it.
            fmt = 'image/png'
            img = decodestring(data['image/png'].encode('ascii'))
        elif 'image/jpeg' in data and self._jpg_supported:
            fmt = 'image/jpeg'
            img = decodestring(data['image/jpeg'].encode('ascii'))
        if img is not None:
            self.sig_new_inline_figure.emit(img, fmt)
            if (self.figurebrowser is not None and
                    self.figurebrowser.mute_inline_plotting):
                if not self.sended_render_message:
                    msg['content']['data']['text/plain'] = ''
                    self._append_html(
                        _('<br><hr>'
                          '\nFigures now render in the Plots pane by default. '
                          'To make them also appear inline in the Console, '
                          'uncheck "Mute Inline Plotting" under the Plots '
                          'pane options menu. \n'
                          '<hr><br>'), before_prompt=True)
                    self.sended_render_message = True
                else:
                    msg['content']['data']['text/plain'] = ''
                del msg['content']['data'][fmt]

        return super(FigureBrowserWidget, self)._handle_display_data(msg)
