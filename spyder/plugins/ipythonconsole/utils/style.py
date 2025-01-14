# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Style for IPython Console
"""

# Third party imports
from qtconsole.styles import dark_color

# Local imports
from spyder.config.gui import get_color_scheme


def create_qss_style(color_scheme):
    """Returns a QSS stylesheet with Spyder color scheme settings.

    The stylesheet can contain classes for:
        Qt: QPlainTextEdit, QFrame, QWidget, etc
       Pygments: .c, .k, .o, etc. (see PygmentsHighlighter)
        IPython: .error, .in-prompt, .out-prompt, etc
    """

    def give_font_weight(is_bold):
        if is_bold:
            return 'bold'
        else:
            return 'normal'

    def give_font_style(is_italic):
        if is_italic:
            return 'italic'
        else:
            return 'normal'

    color_scheme = get_color_scheme(color_scheme)
    fon_c, fon_fw, fon_fs = color_scheme['normal']
    font_color =  fon_c
    if dark_color(font_color):
        in_prompt_color = 'navy'
        out_prompt_color = 'darkred'
    else:
        in_prompt_color = 'lime'
        out_prompt_color = 'red'
    background_color = color_scheme['background']
    error_color = 'red'
    in_prompt_number_font_weight = 'bold'
    out_prompt_number_font_weight = 'bold'
    inverted_background_color = font_color
    inverted_font_color = background_color

    sheet = """QPlainTextEdit, QTextEdit, ControlWidget {{
                                          color: {} ;
                                          background-color: {};
                                         }}
              .error {{ color: {}; }}
              .in-prompt {{ color: {}; }}
              .in-prompt-number {{ color: {}; font-weight: {}; }}
              .out-prompt {{ color: {}; }}
              .out-prompt-number {{ color: {}; font-weight: {}; }}
              .inverted {{ color: {}; background-color: {}; }}
              """

    sheet_formatted = sheet.format(font_color, background_color,
                                   error_color,
                                   in_prompt_color, in_prompt_color,
                                   in_prompt_number_font_weight,
                                   out_prompt_color, out_prompt_color,
                                   out_prompt_number_font_weight,
                                   inverted_font_color,
                                   inverted_background_color)

    return (sheet_formatted, dark_color(font_color))
