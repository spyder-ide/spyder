# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handles communications between the IPython Console and
the Figure Explorer
"""

# ---- Standard library imports

from base64 import decodestring

# ---- Third party library imports

from qtconsole.rich_jupyter_widget import RichJupyterWidget
# from qtconsole.svg import save_svg, svg_to_clipboard, svg_to_image


class FigureBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to intercept the figures
    sent by the kernel to the Ipython Console and send it to the Figure
    Explorer plugin. This widget can also block the plotting of inline
    figure in the Ipython Console so that figures are only plotted in the
    explorer plugin.
    """

    # Reference to the figurebrowser widget connected to this client
    figurebrowser = None

    # TODO: Implement this as an option of the figure explorer plugin instead.
    mute_inline_plotting = True

    # ---- Public API

    def set_figurebrowser(self, figurebrowser):
        """Sets the namespace for the figurebrowser widget."""
        self.figurebrowser = figurebrowser

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
            # TODO: Support for svg is not implemented in the figure browser
            #       widget yet.
            if fmt in ['image/png', 'image/jpeg']:
                self.sig_new_inline_figure.emit(img, fmt)
            if self.mute_inline_plotting:
                del msg['content']['data'][fmt]

        return super(FigureBrowserWidget, self)._handle_display_data(msg)
