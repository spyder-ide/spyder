# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Local imports
from spyder.utils.color_system import Green, Red, Orange, GroupDark, GroupLight
from qdarkstyle.colorsystem import Blue, Gray
from qdarkstyle.darkpalette import DarkPalette
from spyder.config.gui import is_dark_interface


class SpyderPaletteDark:

    # Colors for information and feedback in dialogs

    COLOR_SUCCESS_1 = Green.B40
    COLOR_SUCCESS_2 = Green.B70
    COLOR_SUCCESS_3 = Green.B110

    COLOR_ERROR_1 = Red.B40
    COLOR_ERROR_2 = Red.B70
    COLOR_ERROR_3 = Red.B110

    COLOR_WARN_1 = Orange.B40
    COLOR_WARN_2 = Red.B70
    COLOR_WARN_3 = Orange.B110

    # Icon colors

    ICON_1 = Gray.B140
    ICON_2 = Blue.B70
    ICON_3 = Green.B40
    ICON_4 = Red.B40
    ICON_5 = Orange.B40
    ICON_6 = Gray.B30

    # Colors for icons and variable explorer in dark mode

    GROUP_DARK_1 = GroupDark.B10
    GROUP_DARK_2 = GroupDark.B20
    GROUP_DARK_3 = GroupDark.B30
    GROUP_DARK_4 = GroupDark.B40
    GROUP_DARK_5 = GroupDark.B50
    GROUP_DARK_6 = GroupDark.B60
    GROUP_DARK_7 = GroupDark.B70
    GROUP_DARK_8 = GroupDark.B80
    GROUP_DARK_9 = GroupDark.B90
    GROUP_DARK_10 = GroupDark.B100
    GROUP_DARK_11 = GroupDark.B110
    GROUP_DARK_12 = GroupDark.B120


class SpyderPaletteLight:

    # Colors for information and feedback in dialogs

    COLOR_SUCCESS_1 = Green.B40
    COLOR_SUCCESS_2 = Green.B70
    COLOR_SUCCESS_3 = Green.B110

    COLOR_ERROR_1 = Red.B40
    COLOR_ERROR_2 = Red.B70
    COLOR_ERROR_3 = Red.B110

    COLOR_WARN_1 = Orange.B40
    COLOR_WARN_2 = Red.B70
    COLOR_WARN_3 = Orange.B110

    # Icon colors

    ICON_1 = Gray.B30
    ICON_2 = Blue.B70
    ICON_3 = Green.B70
    ICON_4 = Red.B70
    ICON_5 = Orange.B70
    ICON_6 = Gray.B140

    # Colors for icons and variable explorer in light mode

    GROUP_LIGHT_1 = GroupLight.B10
    GROUP_LIGHT_2 = GroupLight.B20
    GROUP_LIGHT_3 = GroupLight.B30
    GROUP_LIGHT_4 = GroupLight.B40
    GROUP_LIGHT_5 = GroupLight.B50
    GROUP_LIGHT_6 = GroupLight.B60
    GROUP_LIGHT_7 = GroupLight.B70
    GROUP_LIGHT_8 = GroupLight.B80
    GROUP_LIGHT_9 = GroupLight.B90
    GROUP_LIGHT_10 = GroupLight.B100
    GROUP_LIGHT_11 = GroupLight.B110
    GROUP_LIGHT_12 = GroupLight.B120

class LightPalette(object):
    """Theme variables."""

    # Color
    COLOR_BACKGROUND_1 = Gray.B140
    COLOR_BACKGROUND_2 = Gray.B130
    COLOR_BACKGROUND_3 = Gray.B120
    COLOR_BACKGROUND_4 = Gray.B110
    COLOR_BACKGROUND_5 = Gray.B100
    COLOR_BACKGROUND_6 = Gray.B90

    COLOR_TEXT_1 = Gray.B10
    COLOR_TEXT_2 = Gray.B30
    COLOR_TEXT_3 = Gray.B50
    COLOR_TEXT_4 = Gray.B70

    COLOR_ACCENT_1 = Blue.B130
    COLOR_ACCENT_2 = Blue.B100
    COLOR_ACCENT_3 = Blue.B90
    COLOR_ACCENT_4 = Blue.B70
    COLOR_ACCENT_5 = Blue.B50

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

if is_dark_interface():
    SpyderPalette = SpyderPaletteDark
    QDarkPalette = DarkPalette
else:
    SpyderPalette = SpyderPaletteLight
    QDarkPalette = LightPalette
