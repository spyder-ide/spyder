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
from qstylizer.parser import parse as parse_stylesheet
import qstylizer.style

# Local imports
from spyder.config.gui import OLD_PYQT
from spyder.utils.palette import QStylePalette


MAC = sys.platform == 'darwin'
WIN = os.name == 'nt'


# =============================================================================
# ---- Base stylesheet class
# =============================================================================
class SpyderStyleSheet:
    """Base class for Spyder stylesheets."""

    def __init__(self):
        self._stylesheet = qstylizer.style.StyleSheet()
        self.set_stylesheet()

    def get_stylesheet(self):
        return self._stylesheet

    def to_string(self):
        return self._stylesheet.toString()

    def get_copy(self):
        """
        Return a copy of the sytlesheet.

        This allows it to be modified for specific widgets.
        """
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
class AppStylesheet(SpyderStyleSheet):
    """
    Class to build and access the stylesheet we use in the entire
    application.
    """

    def __init__(self):
        super().__init__()
        self._stylesheet_as_string = None

    def to_string(self):
        "Save stylesheet as a string for quick access."
        if self._stylesheet_as_string is None:
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
            height='1.4em',
            fontSize='0.7em',
            padding='4px 24px 4px 8px',
            # TODO: This requires a fix in qstylizer
            # iconSize='0.8em'
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


APP_STYLESHEET = AppStylesheet()

# =============================================================================
# ---- Toolbar stylesheets
# =============================================================================
class ApplicationToolbarStylesheet(SpyderStyleSheet):
    """Stylesheet for application toolbars."""

    BUTTON_WIDTH = '2.7em'
    BUTTON_HEIGHT = '2.7em'
    BUTTON_MARGIN_LEFT = '0.25em'
    BUTTON_MARGIN_RIGHT = '0.25em'

    def set_stylesheet(self):
        css = self._stylesheet

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

    BUTTON_WIDTH = '2.2em'
    BUTTON_HEIGHT = '2.2em'

    def set_stylesheet(self):
        css = self._stylesheet

        css.QToolBar.setValues(
            spacing='0.3em'
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
# ---- Tabbar stylesheet
# =============================================================================
class PanesTabBarStyleSheet(PanesToolbarStyleSheet):
    """Stylesheet for pane tabbars"""

    # TODO: This needs to be changed to 1.0em when the IPython console
    # and the Editor are migrated.
    TOP_MARGIN = '0.8em'

    def set_stylesheet(self):
        super().set_stylesheet()
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

        # This crops the close button a bit at the bottom in order to
        # center it. But a bigger negative padding-bottom crops it even
        # more.
        css['QTabBar::close-button'].setValues(
            paddingBottom='-5px' if MAC else '-6px',
        )

        # Set style for scroller buttons
        css['QTabBar#pane-tabbar QToolButton'].setValues(
            background=QStylePalette.COLOR_BACKGROUND_1,
            borderRadius='0px',
            borderRight=f'0.3em solid {QStylePalette.COLOR_BACKGROUND_1}'
        )

        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = QStylePalette.COLOR_BACKGROUND_2
            else:
                color = QStylePalette.COLOR_BACKGROUND_3
            css[f'QTabBar#pane-tabbar QToolButton:{state}'].setValues(
                background=color
            )

        # This makes one button huge and the other very small in PyQt 5.9
        if not OLD_PYQT:
            css['QTabBar::scroller'].setValues(
                width='4.0em',
            )

        # Remove border between selected tab and pane below
        css['QTabWidget::pane'].setValues(
            borderTop='0px',
        )

        # Adjust margins of corner widgets
        css['QTabWidget::left-corner'].setValues(
            top='-1px',
            bottom='-2px'
        )

        css['QTabWidget::right-corner'].setValues(
            top='-1px',
            bottom='-2px',
            right='-3px' if WIN else '-1px'
        )


PANES_TABBAR_STYLESHEET = PanesTabBarStyleSheet()


# =============================================================================
# ---- Style for special dialogs
# =============================================================================
class DialogStyle:
    """Style constants for tour, about and kite dialogs."""

    IconScaleFactor = 0.5
    TitleFontSize = '19pt' if MAC else '14pt'
    ContentFontSize = '15pt' if MAC else '12pt'
    ButtonsFontSize = '15pt' if MAC else '13pt'
    ButtonsPadding = '6px' if MAC else '4px 10px'
