# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Custom stylesheets used in Spyder."""

# Standard library imports
import copy

# Third-party imports
import qdarkstyle
import qstylizer
from qstylizer.parser import parse as parse_stylesheet

# Local imports
from spyder.utils.palette import QStylePalette


# =============================================================================
# ---- Application stylesheet
# =============================================================================
class AppStylesheet:
    """
    Class to build and access the stylesheet we use in the entire
    application.
    """

    def __init__(self):
        self._stylesheet = None
        self._stylesheet_as_string = None
        self._get_stylesheet()

    def as_string(self):
        """Return the stylesheet as a string."""
        return self._stylesheet_as_string

    def as_object(self):
        """
        Return the stylesheet as an object.

        This allows us to be modified for specific widgets.
        """
        return copy.deepcopy(self._stylesheet)

    def _get_stylesheet(self):
        """
        Get the stylesheet as a Qstylizer StyleSheet object.

        This takes the stylesheet from QDarkstyle and applies our
        customizations to it.
        """
        if self._stylesheet is None:
            stylesheet = qdarkstyle.load_stylesheet()
            self._stylesheet = parse_stylesheet(stylesheet)

            # Add our customizations
            self._customize_stylesheet()

            # Save stylesheet as a string for quick access
            self._stylesheet_as_string = self._stylesheet.toString()

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
            # TODO: This requires a fix in qstylizer
            #iconSize='0.8em'
        )

    def __str__(self):
        return self.as_string()


APP_STYLESHEET = AppStylesheet()

# =============================================================================
# ---- Toolbar stylesheets
# =============================================================================
class ApplicationToolbarStylesheet:
    """Stylesheet for application toolbars."""

    BUTTON_WIDTH = '2.8em'
    BUTTON_HEIGHT = '2.8em'
    BUTTON_MARGIN_LEFT = '0.25em'
    BUTTON_MARGIN_RIGHT = '0.25em'

    def __init__(self):
        self._stylesheet = None
        self._get_stylesheet()

    def _get_stylesheet(self):
        """Get the stylesheet as a Qstylizer StyleSheet object."""
        if self._stylesheet is None:
            css = qstylizer.style.StyleSheet()

            css.QToolButton.setValues(
                width=self.BUTTON_WIDTH,
                height=self.BUTTON_HEIGHT,
                marginLeft=self.BUTTON_MARGIN_RIGHT,
                marginRight=self.BUTTON_MARGIN_RIGHT,
                border='0px',
                padding='0px',
            )

            css.QToolBar.setValues(
                backgroundColor=QStylePalette.COLOR_BACKGROUND_4
            )

            self._stylesheet = css

    def __str__(self):
        return self._stylesheet.toString()


class PanesToolbarStyleSheet:
    """Stylesheet for pane toolbars."""

    BUTTON_WIDTH = '2.2em'
    BUTTON_HEIGHT = '2.2em'

    def __init__(self):
        self._stylesheet = None
        self._get_stylesheet()

    def _get_stylesheet(self):
        """Get the stylesheet as a Qstylizer StyleSheet object."""
        if self._stylesheet is None:
            css = qstylizer.style.StyleSheet()
            app_css = APP_STYLESHEET._stylesheet

            css.QToolBar.setValues(
                spacing='0.3em'
            )

            css.QToolButton.setValues(
                height=self.BUTTON_HEIGHT,
                width=self.BUTTON_WIDTH,
                border='0px',
                background=app_css.QToolButton.backgroundColor.value,
            )

            for state in ['hover', 'pressed', 'checked']:
                color = app_css[f'QToolButton:{state}'].backgroundColor.value
                css[f'QToolButton:{state}'].setValues(
                    backgroundColor=color
                )

            self._stylesheet = css

    def __str__(self):
        return self._stylesheet.toString()


APP_TOOLBAR_STYLESHEET = ApplicationToolbarStylesheet()
PANES_TOOLBAR_STYLESHEET = PanesToolbarStyleSheet()
