# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Shell helpers"""


def get_error_match(text):
    """Return error match"""
    import re
    return re.match(r'  File "(.*)", line (\d*)', text)


class ANSIEscapeCodeHandler(object):
    """ANSI Escape sequences handler"""
    ANSI_COLORS = ( # Normal, Bright/Light
                   ('#000000', '#808080'), # 0: black
                   ('#ff0000', '#ff0000'), # 1: red
                   ('#00ff00', '#4e8975'), # 2: green
                   ('#800000', '#ffff00'), # 3: yellow
                   ('#0000ff', '#0000FF'), # 4: blue
                   ('#800080', '#ca226b'), # 5: magenta
                   ('#00ffff', '#8f8fbd'), # 6: cyan
                   ('#c0c0c0', '#ffff00'), # 7: white
                   )
    def __init__(self):
        self.intensity = 0
        self.italic = None
        self.bold = None
        self.underline = None
        self.foreground_color = None
        self.background_color = None
        
    def set_code(self, code):
        assert isinstance(code, int)
        if code == 0:
            # Reset all settings
            self.reset()
        elif code == 1:
            # Text color intensity
            self.intensity = 1
            self.bold = True
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
            self.foreground_color = None
        elif code >= 40 and code <= 47:
            # Background color
            self.background_color = code
        elif code == 49:
            # Default background color
            self.background_color = None
        self.set_style()
        
    def reset(self):
        self.current_format = None
        self.intensity = 0
        self.italic = False
        self.bold = False
        self.underline = False
        self.foreground_color = None
        self.background_color = None
