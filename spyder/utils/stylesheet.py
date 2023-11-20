# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Custom stylesheets used in Spyder."""

# Standard library imports
import copy
import os
import sys

# Third-party imports
import qdarkstyle
from qdarkstyle.colorsystem import Gray
from qstylizer.parser import parse as parse_stylesheet
import qstylizer.style

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.config.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.utils import classproperty
from spyder.config.gui import is_dark_interface, OLD_PYQT
from spyder.utils.palette import QStylePalette


# =============================================================================
# ---- Constants
# =============================================================================
MAC = sys.platform == 'darwin'
WIN = os.name == 'nt'


class AppStyle:
    """
    Enum with several constants used in the application style.

    Notes
    -----
    All sizes are in pixels.
    """
    # Size of margins.
    MarginSize = 3

    # Size of find widget line edits (e.g. FinderWidget and FindReplace)
    FindMinWidth = 400
    FindHeight = 26

    # To have it for quick access because it's needed a lot in Mac
    MacScrollBarWidth = 16


# =============================================================================
# ---- Base stylesheet class
# =============================================================================
class SpyderStyleSheet:
    """Base class for Spyder stylesheets."""

    SET_STYLESHEET_AT_INIT = True
    """
    Decide if the stylesheet must be set when the class is initialized.

    Notes
    -----
    There are some stylesheets for which this is not possible (e.g. the ones
    that need to access our fonts).
    """

    def __init__(self):
        self._stylesheet = qstylizer.style.StyleSheet()
        if self.SET_STYLESHEET_AT_INIT:
            self.set_stylesheet()

    def get_stylesheet(self):
        return self._stylesheet

    def to_string(self):
        if self._stylesheet.toString() == "":
            self.set_stylesheet()
        return self._stylesheet.toString()

    def get_copy(self):
        """
        Return a copy of the sytlesheet.

        This allows it to be modified for specific widgets.
        """
        if self._stylesheet.toString() == "":
            self.set_stylesheet()
        return copy.deepcopy(self)

    def set_stylesheet(self):
        raise NotImplementedError(
            "Subclasses need to implement this method to set the _stylesheet "
            "attribute as a Qstylizer StyleSheet object."
        )

    def __str__(self):
        """
        Get a string representation of the stylesheet object this class
        holds.
        """
        return self.to_string()


# =============================================================================
# ---- Application stylesheet
# =============================================================================
class AppStylesheet(SpyderStyleSheet, SpyderConfigurationAccessor):
    """
    Class to build and access the stylesheet we use in the entire
    application.
    """

    # Don't create the stylesheet here so that Spyder gets the app font from
    # the system when it starts for the first time. This also allows us to
    # display the splash screen more quickly because the stylesheet is then
    # computed only when it's going to be applied to the app, not when this
    # object is imported.
    SET_STYLESHEET_AT_INIT = False

    def __init__(self):
        super().__init__()
        self._stylesheet_as_string = None

    def to_string(self):
        """Save stylesheet as a string for quick access."""
        if self._stylesheet_as_string is None:
            self.set_stylesheet()
            self._stylesheet_as_string = self._stylesheet.toString()
        return self._stylesheet_as_string

    def set_stylesheet(self):
        """
        This takes the stylesheet from QDarkstyle and applies our
        customizations to it.
        """
        stylesheet = qdarkstyle.load_stylesheet(palette=QStylePalette)
        self._stylesheet = parse_stylesheet(stylesheet)

        # Add our customizations
        self._customize_stylesheet()

    def _customize_stylesheet(self):
        """Apply our customizations to the stylesheet."""
        css = self._stylesheet

        # App font properties
        font_family = self.get_conf('app_font/family', section='appearance')
        font_size = int(self.get_conf('app_font/size', section='appearance'))

        # Remove padding and border for QStackedWidget (used in Plots
        # and the Variable Explorer)
        css['QStackedWidget'].setValues(
            border='0px',
            padding='0px',
        )

        # Remove margin when pressing buttons
        css["QToolButton:pressed"].setValues(
            margin='0px'
        )

        # Set the same color as the one used for the app toolbar
        css.QMenuBar.setValues(
            backgroundColor=QStylePalette.COLOR_BACKGROUND_4
        )

        # Remove padding when pressing main menus
        css['QMenuBar::item:pressed'].setValues(
            padding='0px'
        )

        # Remove border, padding and spacing for main toolbar
        css.QToolBar.setValues(
            borderBottom='0px',
            padding='0px',
            spacing='0px',
        )

        # Remove margins around separators
        css['QMainWindow::separator:horizontal'].setValues(
            marginTop='0px',
            marginBottom='0px'
        )

        css['QMainWindow::separator:vertical'].setValues(
            marginLeft='0px',
            marginRight='0px',
            height='3px'
        )

        # Set menu item properties
        css["QMenu::item"].setValues(
            height='1.6em',
            padding='4px 24px 4px 8px',
            fontFamily=font_family,
            fontSize=f'{font_size}pt'
        )

        if OLD_PYQT:
            css["QMenu::item"].setValues(
                padding='4px 24px 4px 28px',
            )

        css["QMenu#checkbox-padding::item"].setValues(
            padding='4px 24px 4px 28px',
        )

        # Increase padding for QPushButton's
        css.QPushButton.setValues(
            padding='3px',
        )

        for state in ['disabled', 'checked', 'checked:disabled']:
            css[f'QPushButton:{state}'].setValues(
                padding='3px',
            )

        # Adjust QToolButton style to our needs.
        # This affects not only the pane toolbars but also the
        # find/replace widget, the finder in the Variable Explorer,
        # and all QToolButton's that are not part of the main toolbar.
        for element in ['QToolButton', 'QToolButton:disabled']:
            css[f'{element}'].setValues(
                backgroundColor='transparent'
            )

        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = QStylePalette.COLOR_BACKGROUND_2
            else:
                color = QStylePalette.COLOR_BACKGROUND_3
            css[f'QToolButton:{state}'].setValues(
                backgroundColor=color
            )

        # Adjust padding of QPushButton's in QDialog's
        css["QDialog QPushButton"].setValues(
            padding='3px 15px 3px 15px',
        )

        css["QDialogButtonBox QPushButton:!default"].setValues(
            padding='3px 0px 3px 0px',
        )

        # Set font for widgets that don't inherit it from the application
        # This is necessary for spyder-ide/spyder#5942.
        for widget in ['QToolTip', 'QDialog', 'QListView', 'QTreeView',
                       'QHeaderView::section', 'QTableView']:
            css[f'{widget}'].setValues(
                fontFamily=font_family,
                fontSize=f'{font_size}pt'
            )

        # Make our comboboxes have a uniform height
        if font_size < 10:
            combobox_min_height = 1.8
        elif 10 <= font_size < 13:
            combobox_min_height = 1.7 if MAC else 1.6
        else:
            combobox_min_height = 1.5 if MAC else 1.4

        css.QComboBox.setValues(
            minHeight=f'{combobox_min_height}em'
        )

        # Add top and bottom padding to the inner contents of comboboxes
        css["QComboBox QAbstractItemView"].setValues(
            paddingTop=f"{2 * AppStyle.MarginSize}px",
            paddingBottom=f"{2 * AppStyle.MarginSize}px"
        )

        # Add margin and padding to combobox items
        css["QComboBox QAbstractItemView::item"].setValues(
            marginLeft=f"{AppStyle.MarginSize}px",
            marginRight=f"{AppStyle.MarginSize}px",
            padding=f"{AppStyle.MarginSize}px"
        )

        # Make color of hovered combobox items match the one used in other
        # Spyder widgets
        css["QComboBox QAbstractItemView::item:selected:active"].setValues(
            backgroundColor=QStylePalette.COLOR_BACKGROUND_3,
        )

        # Make lineedits have *almost* the same height as our comboboxes. This
        # is not perfect because (oddly enough) Qt doesn't set the same height
        # for both when using the same value, but it's close enough.
        css.QLineEdit.setValues(
            minHeight=f'{combobox_min_height - 0.2}em'
        )

        # Change QGroupBox style to avoid the "boxes within boxes" antipattern
        # in Preferences
        css.QGroupBox.setValues(
            border='0px',
            marginBottom='15px',
            fontSize=f'{font_size + 1}pt',
        )

        css['QGroupBox::title'].setValues(
            paddingTop='-0.3em',
            left='0px',
        )


APP_STYLESHEET = AppStylesheet()

# =============================================================================
# ---- Toolbar stylesheets
# =============================================================================
class ApplicationToolbarStylesheet(SpyderStyleSheet):
    """Stylesheet for application toolbars."""

    BUTTON_WIDTH = '47px'
    BUTTON_HEIGHT = '47px'
    BUTTON_MARGIN_LEFT = '3px'
    BUTTON_MARGIN_RIGHT = '3px'

    def set_stylesheet(self):
        css = self.get_stylesheet()

        # Main background color
        css.QToolBar.setValues(
            backgroundColor=QStylePalette.COLOR_BACKGROUND_4
        )

        # Adjust QToolButton to follow the main toolbar style.
        css.QToolButton.setValues(
            width=self.BUTTON_WIDTH,
            height=self.BUTTON_HEIGHT,
            marginLeft=self.BUTTON_MARGIN_RIGHT,
            marginRight=self.BUTTON_MARGIN_RIGHT,
            border='0px',
            padding='0px',
        )

        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = QStylePalette.COLOR_BACKGROUND_5
            else:
                color = QStylePalette.COLOR_BACKGROUND_6
            css[f'QToolBar QToolButton:{state}'].setValues(
                backgroundColor=color
            )

        # Remove indicator for popup mode
        css['QToolBar QToolButton::menu-indicator'].setValues(
            image='none'
        )


class PanesToolbarStyleSheet(SpyderStyleSheet):
    """Stylesheet for pane toolbars."""

    # These values make buttons to be displayed at 44px according to Gammaray
    BUTTON_WIDTH = '37px'
    BUTTON_HEIGHT = '37px'

    def set_stylesheet(self):
        css = self.get_stylesheet()

        css.QToolBar.setValues(
            spacing='4px'
        )

        css.QToolButton.setValues(
            height=self.BUTTON_HEIGHT,
            width=self.BUTTON_WIDTH,
            border='0px',
            margin='0px'
        )

        # Remove indicator for popup mode
        css['QToolButton::menu-indicator'].setValues(
            image='none'
        )


APP_TOOLBAR_STYLESHEET = ApplicationToolbarStylesheet()
PANES_TOOLBAR_STYLESHEET = PanesToolbarStyleSheet()


# =============================================================================
# ---- Tabbar stylesheets
# =============================================================================
class BaseTabBarStyleSheet(SpyderStyleSheet):
    """Base style for tabbars."""

    OBJECT_NAME = ''

    # Additional border for scroll buttons
    SCROLL_BUTTONS_BORDER_WIDTH = '0px'

    # Position for the scroll buttons additional border
    SCROLL_BUTTONS_BORDER_POS = ''

    def set_stylesheet(self):
        css = self.get_stylesheet()
        buttons_color = QStylePalette.COLOR_BACKGROUND_1

        # Set style for scroll buttons
        css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
            background=buttons_color,
            borderRadius='0px',
        )

        if self.SCROLL_BUTTONS_BORDER_POS == 'right':
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                borderRight=(
                    f'{self.SCROLL_BUTTONS_BORDER_WIDTH} solid {buttons_color}'
                )
            )
        else:
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                borderBottom=(
                    f'{self.SCROLL_BUTTONS_BORDER_WIDTH} solid {buttons_color}'
                )
            )

        # Hover and pressed state for scroll buttons
        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = QStylePalette.COLOR_BACKGROUND_2
            else:
                color = QStylePalette.COLOR_BACKGROUND_3
            css[f'QTabBar{self.OBJECT_NAME} QToolButton:{state}'].setValues(
                background=color
            )

        # Set width for scroll buttons
        # This makes one button huge and the other very small in PyQt 5.9
        if not OLD_PYQT:
            css['QTabBar::scroller'].setValues(
                width='66px',
            )


class PanesTabBarStyleSheet(PanesToolbarStyleSheet, BaseTabBarStyleSheet):
    """Stylesheet for pane tabbars"""

    TOP_MARGIN = '12px'
    OBJECT_NAME = '#pane-tabbar'
    SCROLL_BUTTONS_BORDER_WIDTH = '5px'
    SCROLL_BUTTONS_BORDER_POS = 'right'

    def set_stylesheet(self):
        # Calling super().set_stylesheet() here doesn't work.
        PanesToolbarStyleSheet.set_stylesheet(self)
        BaseTabBarStyleSheet.set_stylesheet(self)
        css = self.get_stylesheet()

        # This removes a white dot that appears to the left of right corner
        # widgets
        css.QToolBar.setValues(
            marginLeft='-3px' if WIN else '-1px',
        )

        # QTabBar forces the corner widgets to be smaller than they should.
        # be. The added top margin allows the toolbuttons to expand to their
        # normal size.
        # See: spyder-ide/spyder#13600
        css['QTabBar::tab'].setValues(
            marginTop=self.TOP_MARGIN,
            paddingTop='4px',
            paddingBottom='4px',
            paddingLeft='4px' if MAC else '10px',
            paddingRight='10px' if MAC else '4px'
        )

        if MAC:
            # Show tabs left-aligned on Mac and remove spurious
            # pixel to the left.
            css.QTabBar.setValues(
                alignment='left',
                marginLeft='-1px'
            )

            css['QTabWidget::tab-bar'].setValues(
                alignment='left',
            )
        else:
            # Remove spurious pixel to the left
            css.QTabBar.setValues(
                marginLeft='-3px' if WIN else '-1px'
            )

        # Fix minor visual glitch when hovering tabs
        # See spyder-ide/spyder#15398
        css['QTabBar::tab:hover'].setValues(
            paddingTop='3px',
            paddingBottom='3px',
            paddingLeft='3px' if MAC else '9px',
            paddingRight='9px' if MAC else '3px'
        )

        for state in ['selected', 'selected:hover']:
            css[f'QTabBar::tab:{state}'].setValues(
                paddingTop='4px',
                paddingBottom='3px',
                paddingLeft='4px' if MAC else '10px',
                paddingRight='10px' if MAC else '4px'
            )

        # Remove border between selected tab and pane below
        css['QTabWidget::pane'].setValues(
            borderTop='0px',
        )

        # Adjust margins of corner widgets
        css['QTabWidget::left-corner'].setValues(
            top='-1px',
        )

        css['QTabWidget::right-corner'].setValues(
            top='-1px',
            right='-3px' if WIN else '-1px'
        )

        # Make scroll button icons smaller on Windows and Mac
        if WIN or MAC:
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                padding=f'{5 if WIN else 7}px',
            )


class BaseDockTabBarStyleSheet(BaseTabBarStyleSheet):
    """Base style for dockwidget tabbars."""

    SCROLL_BUTTONS_BORDER_WIDTH = '2px'
    SCROLL_BUTTONS_PADDING = 7 if WIN else 9

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        self.color_tabs_separator = f'{Gray.B70}'

        if is_dark_interface():
            self.color_selected_tab = f'{QStylePalette.COLOR_ACCENT_2}'
        else:
            self.color_selected_tab = f'{QStylePalette.COLOR_ACCENT_5}'

        # Center tabs to differentiate them from the regular ones.
        # See spyder-ide/spyder#9763 for details.
        css.QTabBar.setValues(
            alignment='center'
        )

        css['QTabWidget::tab-bar'].setValues(
            alignment='center'
        )

        # Style for selected tabs
        css['QTabBar::tab:selected'].setValues(
            color=(
                f'{QStylePalette.COLOR_TEXT_1}' if is_dark_interface() else
                f'{QStylePalette.COLOR_BACKGROUND_1}'
            ),
            backgroundColor=f'{self.color_selected_tab}',
        )

        # Make scroll button icons smaller on Windows and Mac
        if WIN or MAC:
            css['QTabBar QToolButton'].setValues(
                padding=f'{self.SCROLL_BUTTONS_PADDING}px',
            )


class SpecialTabBarStyleSheet(BaseDockTabBarStyleSheet):
    """
    Style for special tab bars.

    Notes
    -----
    This is the base class for horizontal tab bars that follow the design
    discussed on issue spyder-ide/ux-improvements#4.
    """

    SCROLL_BUTTONS_BORDER_POS = 'right'

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # Basic style
        css['QTabBar::tab'].setValues(
            # Only add margin to the bottom
            margin=f'0px 0px {2 * margin_size}px 0px',
            # Border radius is added for specific tabs (see below)
            borderRadius='0px',
            # Remove a colored border added by QDarkStyle
            borderBottom='0px',
            # Add right border to make it work as our tabs separator
            borderRight=f'1px solid {self.color_tabs_separator}',
            # Padding for text inside tabs
            padding='4px 10px',
        )

        # Hide tabs separator for the selected tab and the one to its left.
        # Note: For some strange reason, Qt uses the `next-selected` state for
        # the left tab.
        for state in ['QTabBar::tab:selected', 'QTabBar::tab:next-selected']:
            css[state].setValues(
                borderRight=f'1px solid {self.color_selected_tab}',
            )

        # Style for hovered tabs
        css['QTabBar::tab:!selected:hover'].setValues(
            border='0px',
            borderRight=f'1px solid {self.color_tabs_separator}',
            backgroundColor=f'{QStylePalette.COLOR_BACKGROUND_5}'
        )

        css['QTabBar::tab:previous-selected:hover'].setValues(
            borderLeft=f'1px solid {self.color_tabs_separator}',
        )

        # First and last tabs have rounded borders
        css['QTabBar::tab:first'].setValues(
            borderTopLeftRadius='4px',
            borderBottomLeftRadius='4px',
        )

        css['QTabBar::tab:last'].setValues(
            borderTopRightRadius='4px',
            borderBottomRightRadius='4px',
        )

        # Last tab doesn't need to show the separator
        for state in ['QTabBar::tab:last:!selected:hover',
                      'QTabBar::tab:last']:
            css[state].setValues(
                borderRightColor=f'{QStylePalette.COLOR_BACKGROUND_4}'
            )

        # Set bottom margin for scroll buttons.
        css['QTabBar QToolButton'].setValues(
            marginBottom=f'{2 * margin_size}px',
        )


class PreferencesTabBarStyleSheet(SpecialTabBarStyleSheet, SpyderFontsMixin):
    """Style for tab bars in our Preferences dialog."""

    # This is necessary because this class needs to access fonts
    SET_STYLESHEET_AT_INIT = False

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        font = self.get_font(SpyderFontType.Interface, font_size_delta=1)

        # Set font size to be one point bigger than the regular text.
        css.QTabBar.setValues(
            fontSize=f'{font.pointSize()}pt',
        )

        # Make scroll buttons a bit bigger on Windows and Mac (this has no
        # effect on Linux).
        if WIN or MAC:
            css['QTabBar QToolButton'].setValues(
                padding=f'{self.SCROLL_BUTTONS_PADDING - 1}px',
            )

        # Increase padding around text because we're using a larger font.
        css['QTabBar::tab'].setValues(
            padding='6px 10px',
        )

        # Remove border and add padding for content inside tabs
        css['QTabWidget::pane'].setValues(
            border='0px',
            padding='15px',
        )


class HorizontalDockTabBarStyleSheet(SpecialTabBarStyleSheet):
    """Style for horizontal dockwidget tab bars."""

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # Tabs style
        css['QTabBar::tab'].setValues(
            # No margins to left/right but top/bottom to separate tabbar from
            # the dockwidget areas.
            # Notes:
            # * Top margin is half the one at the bottom so that we can show
            #   a bottom margin on dockwidgets that are not tabified.
            # * The other half is added through the _margin_bottom attribute of
            #   PluginMainWidget.
            margin=f'{margin_size}px 0px {2 * margin_size}px 0px',
            # Remove a colored border added by QDarkStyle
            borderTop='0px',
        )

        # Add margin to first and last tabs to avoid them touching the left and
        # right dockwidget areas, respectively.
        css['QTabBar::tab:first'].setValues(
            marginLeft=f'{2 * margin_size}px',
        )

        css['QTabBar::tab:last'].setValues(
            marginRight=f'{2 * margin_size}px',
        )

        # Make top and bottom margins for scroll buttons even.
        # This is necessary since the tabbar top margin is half the one at the
        # bottom (see the notes in the 'QTabBar::tab' style above).
        css['QTabBar QToolButton'].setValues(
            marginTop='0px',
            marginBottom=f'{margin_size}px',
        )


class VerticalDockTabBarStyleSheet(BaseDockTabBarStyleSheet):
    """Style for vertical dockwidget tab bars."""

    SCROLL_BUTTONS_BORDER_POS = 'bottom'

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # Basic style
        css['QTabBar::tab'].setValues(
            # No margins to top/bottom but left/right to separate tabbar from
            # the dockwidget areas
            margin=f'0px {2 * margin_size}px',
            # Border radius is added for specific tabs (see below)
            borderRadius='0px',
            # Remove colored borders added by QDarkStyle
            borderLeft='0px',
            borderRight='0px',
            # Add border to make it work as our tabs separator
            borderBottom=f'1px solid {self.color_tabs_separator}',
            # Padding for text inside tabs
            padding='10px 4px',
        )

        # Hide tabs separator for the selected tab and the one to its bottom.
        for state in ['QTabBar::tab:selected', 'QTabBar::tab:next-selected']:
            css[state].setValues(
                borderBottom=f'1px solid {self.color_selected_tab}',
            )

        # Style for hovered tabs
        css['QTabBar::tab:!selected:hover'].setValues(
            border='0px',
            borderBottom=f'1px solid {self.color_tabs_separator}',
            backgroundColor=f'{QStylePalette.COLOR_BACKGROUND_5}'
        )

        css['QTabBar::tab:previous-selected:hover'].setValues(
            borderTop=f'1px solid {self.color_tabs_separator}',
        )

        # First and last tabs have rounded borders. Also, add margin to avoid
        # them touch the top and bottom borders, respectively.
        css['QTabBar::tab:first'].setValues(
            borderTopLeftRadius='4px',
            borderTopRightRadius='4px',
            marginTop=f'{2 * margin_size}px',
        )

        css['QTabBar::tab:last'].setValues(
            borderBottomLeftRadius='4px',
            borderBottomRightRadius='4px',
            marginBottom=f'{2 * margin_size}px',
        )

        # Last tab doesn't need to show the separator
        for state in ['QTabBar::tab:last:!selected:hover',
                      'QTabBar::tab:last']:
            css[state].setValues(
                borderBottomColor=f'{QStylePalette.COLOR_BACKGROUND_4}'
            )

        # Make style for scroll buttons match the horizontal one
        css['QTabBar QToolButton'].setValues(
            marginLeft=f'{margin_size}px',
            marginRight=f'{margin_size}px',
        )


PANES_TABBAR_STYLESHEET = PanesTabBarStyleSheet()
HORIZONTAL_DOCK_TABBAR_STYLESHEET = HorizontalDockTabBarStyleSheet()
VERTICAL_DOCK_TABBAR_STYLESHEET = VerticalDockTabBarStyleSheet()
PREFERENCES_TABBAR_STYLESHEET = PreferencesTabBarStyleSheet()


# =============================================================================
# ---- Style for special dialogs
# =============================================================================
class DialogStyle(SpyderFontsMixin):
    """Style constants for tour and about dialogs."""

    IconScaleFactor = 0.5
    ButtonsPadding = '6px' if MAC else '4px 10px'

    @classproperty
    def _fs(cls):
        return cls.get_font(SpyderFontType.Interface).pointSize()

    @classproperty
    def TitleFontSize(cls):
        if WIN:
            return f"{cls._fs + 6}pt"
        elif MAC:
            return f"{cls._fs + 6}pt"
        else:
            return f"{cls._fs + 4}pt"

    @classproperty
    def ContentFontSize(cls):
        if WIN:
            return f"{cls._fs + 4}pt"
        elif MAC:
            return f"{cls._fs + 2}pt"
        else:
            return f"{cls._fs + 2}pt"

    @classproperty
    def ButtonsFontSize(cls):
        if WIN:
            return f"{cls._fs + 5}pt"
        elif MAC:
            return f"{cls._fs + 2}pt"
        else:
            return f"{cls._fs + 3}pt"
