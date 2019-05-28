# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Terminal emulation tools"""

import os

class ANSIEscapeCodeHandler(object):
    """ANSI Escape sequences handler"""
    if os.name == 'nt':
        # Windows terminal colors:
        ANSI_COLORS = ( # Normal, Bright/Light
                       ('#000000', '#808080'), # 0: black
                       ('#800000', '#ff0000'), # 1: red
                       ('#008000', '#00ff00'), # 2: green
                       ('#808000', '#ffff00'), # 3: yellow
                       ('#000080', '#0000ff'), # 4: blue
                       ('#800080', '#ff00ff'), # 5: magenta
                       ('#008080', '#00ffff'), # 6: cyan
                       ('#c0c0c0', '#ffffff'), # 7: white
                       )
    elif os.name == 'mac':
        # Terminal.app colors:
        ANSI_COLORS = ( # Normal, Bright/Light
                       ('#000000', '#818383'), # 0: black
                       ('#C23621', '#FC391F'), # 1: red
                       ('#25BC24', '#25BC24'), # 2: green
                       ('#ADAD27', '#EAEC23'), # 3: yellow
                       ('#492EE1', '#5833FF'), # 4: blue
                       ('#D338D3', '#F935F8'), # 5: magenta
                       ('#33BBC8', '#14F0F0'), # 6: cyan
                       ('#CBCCCD', '#E9EBEB'), # 7: white
                       )
    else:
        # xterm colors:
        ANSI_COLORS = ( # Normal, Bright/Light
                       ('#000000', '#7F7F7F'), # 0: black
                       ('#CD0000', '#ff0000'), # 1: red
                       ('#00CD00', '#00ff00'), # 2: green
                       ('#CDCD00', '#ffff00'), # 3: yellow
                       ('#0000EE', '#5C5CFF'), # 4: blue
                       ('#CD00CD', '#ff00ff'), # 5: magenta
                       ('#00CDCD', '#00ffff'), # 6: cyan
                       ('#E5E5E5', '#ffffff'), # 7: white
                       )
    def __init__(self):
        self.intensity = 0
        self.italic = None
        self.bold = None
        self.underline = None
        self.foreground_color = None
        self.background_color = None
        self.default_foreground_color = 30
        self.default_background_color = 47

    def set_code(self, code):
        assert isinstance(code, int)
        if code == 0:
            # Reset all settings
            self.reset()
        elif code == 1:
            # Text color intensity
            self.intensity = 1
            # The following line is commented because most terminals won't
            # change the font weight, against ANSI standard recommendation:
#            self.bold = True
        elif code == 3:
            # Italic on
            self.italic = True
        elif code == 4:
            # Underline simple
            self.underline = True
        elif code == 22:
            # Normal text color intensity
            self.intensity = 0
            self.bold = False
        elif code == 23:
            # No italic
            self.italic = False
        elif code == 24:
            # No underline
            self.underline = False
        elif code >= 30 and code <= 37:
            # Text color
            self.foreground_color = code
        elif code == 39:
            # Default text color
            self.foreground_color = self.default_foreground_color
        elif code >= 40 and code <= 47:
            # Background color
            self.background_color = code
        elif code == 49:
            # Default background color
            self.background_color = self.default_background_color
        self.set_style()

    def set_style(self):
        """
        Set font style with the following attributes:
        'foreground_color', 'background_color', 'italic',
        'bold' and 'underline'
        """
        raise NotImplementedError

    def reset(self):
        self.current_format = None
        self.intensity = 0
        self.italic = False
        self.bold = False
        self.underline = False
        self.foreground_color = None
        self.background_color = None
