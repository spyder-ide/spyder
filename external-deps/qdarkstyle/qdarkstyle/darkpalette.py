#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""QDarkStyle default dark palette."""

# Standard library imports
from collections import OrderedDict

# Local imports
from qdarkstyle.colorsystem import Blue, Gray


class DarkPalette(object):
    """Theme variables."""

    # Color
    COLOR_BACKGROUND_1 = Gray.B10
    COLOR_BACKGROUND_2 = Gray.B20
    COLOR_BACKGROUND_3 = Gray.B30
    COLOR_BACKGROUND_4 = Gray.B40
    COLOR_BACKGROUND_5 = Gray.B50
    COLOR_BACKGROUND_6 = Gray.B60

    COLOR_TEXT_1 = Gray.B130
    COLOR_TEXT_2 = Gray.B110
    COLOR_TEXT_3 = Gray.B90
    COLOR_TEXT_4 = Gray.B80

    COLOR_ACCENT_1 = Blue.B20
    COLOR_ACCENT_2 = Blue.B40
    COLOR_ACCENT_3 = Blue.B50
    COLOR_ACCENT_4 = Blue.B70
    COLOR_ACCENT_5 = Blue.B80

    OPACITY_TOOLTIP = 230

    # Size
    SIZE_BORDER_RADIUS = '4px'

    # Borders
    BORDER_1 = '1px solid $COLOR_BACKGROUND_1'
    BORDER_2 = '1px solid $COLOR_BACKGROUND_4'
    BORDER_3 = '1px solid $COLOR_BACKGROUND_6'

    BORDER_SELECTION_3 = '1px solid $COLOR_ACCENT_3'
    BORDER_SELECTION_2 = '1px solid $COLOR_ACCENT_2'
    BORDER_SELECTION_1 = '1px solid $COLOR_ACCENT_1'


    # Example of additional widget specific variables
    W_STATUS_BAR_BACKGROUND_COLOR = COLOR_ACCENT_1

    # Paths
    PATH_RESOURCES = "':/qss_icons'"

    @classmethod
    def to_dict(cls, colors_only=False):
        """Convert variables to dictionary."""
        order = [
            'COLOR_BACKGROUND_6',
            'COLOR_BACKGROUND_5',
            'COLOR_BACKGROUND_4',
            'COLOR_BACKGROUND_2',
            'COLOR_BACKGROUND_3',
            'COLOR_BACKGROUND_1',
            'COLOR_TEXT_1',
            'COLOR_TEXT_2',
            'COLOR_TEXT_3',
            'COLOR_TEXT_4',
            'COLOR_ACCENT_1',
            'COLOR_ACCENT_2',
            'COLOR_ACCENT_3',
            'COLOR_ACCENT_4',
            'OPACITY_TOOLTIP',
            'SIZE_BORDER_RADIUS',
            'BORDER_1',
            'BORDER_2',
            'BORDER_3',
            'BORDER_SELECTION_3',
            'BORDER_SELECTION_2',
            'BORDER_SELECTION_1',
            'W_STATUS_BAR_BACKGROUND_COLOR',
            'PATH_RESOURCES',
        ]
        dic = OrderedDict()
        for var in order:
            value = getattr(cls, var)

            if colors_only:
                if not var.startswith('COLOR'):
                    value = None

            if value:
                dic[var] = value

        return dic

    @classmethod
    def color_palette(cls):
        """Return the ordered colored palette dictionary."""
        return cls.to_dict(colors_only=True)
