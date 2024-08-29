# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module serving the "About Spyder" function"""

# Standard library imports
import sys

# Third party imports
import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QVBoxLayout, QLabel, QLayout,
                            QPushButton, QScrollArea, QTabWidget)

# Local imports
from spyder import (
    __project_url__ as project_url,
    __forum_url__ as forum_url,
    __trouble_url__ as trouble_url,
    __website_url__ as website_url,
    get_versions, get_versions_text
)
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.api.widgets.mixins import SvgToScaledPixmap
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import (
    AppStyle,
    DialogStyle,
    MAC,
    PREFERENCES_TABBAR_STYLESHEET,
    WIN
)


class AboutDialog(QDialog, SvgToScaledPixmap):

    PADDING = 5 if MAC else 15

    def __init__(self, parent):
        """Create About Spyder dialog with general information."""
        QDialog.__init__(self, parent)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self.setWindowTitle(_("About Spyder"))
        self.setWindowIcon(ima.icon("MessageBoxInformation"))
        versions = get_versions()

        # -- Show Git revision for development version
        revlink = ''
        if versions['revision']:
            rev = versions['revision']
            revlink = ("<a href='https://github.com/spyder-ide/spyder/"
                       "commit/%s'>%s</a>" % (rev, rev))

        # -- Style attributes
        font_family = self.font().family()
        font_size = DialogStyle.ContentFontSize

        # -- Labels
        twitter_url = "https://twitter.com/Spyder_IDE",
        facebook_url = "https://www.facebook.com/SpyderIDE",
        youtube_url = "https://www.youtube.com/Spyder-IDE",
        instagram_url = "https://www.instagram.com/spyderide/",
        self.label_overview = QLabel(
            f"""
            <style>
                p, h1 {{margin-bottom: 2em}}
                h1 {{margin-top: 0}}
            </style>

            <div style='font-family: "{font_family}";
                        font-size: {font_size};
                        font-weight: normal;
                        '>
            <br>
            <h1>Spyder IDE</h1>

            <p>
            The Scientific Python Development Environment
            <br>
            <a href="{website_url}">Spyder-IDE.org</a>
            </p>

            <p>
            Python {versions['python']} {versions['bitness']}-bit |
            Qt {versions['qt']} |
            {versions['qt_api']} {versions['qt_api_ver']}
            <br>
            {versions['system']} {versions['release']} ({versions['machine']})
            </p>

            <p>
            <a href="{project_url}">GitHub</a> | <a href="{twitter_url}">
            Twitter</a> |
            <a href="{facebook_url}">Facebook</a> | <a href="{youtube_url}">
            YouTube</a> |
            <a href="{instagram_url}">Instagram</a>
            </p>

            </div>"""
        )

        self.label_community = QLabel(
            f"""
            <div style='font-family: "{font_family}";
                        font-size: {font_size};
                        font-weight: normal;
                        '>
            <br>
            Created by Pierre Raybaut; current maintainer is Carlos Cordoba.
            Developed by the
            <a href="{project_url}/graphs/contributors">international
            Spyder community</a>. Many thanks to all the Spyder beta testers
            and dedicated users.
            <p>For help with Spyder errors and crashes, please read our
            <a href="{trouble_url}">Troubleshooting Guide</a>, and for bug
            reports and feature requests, visit our
            <a href="{project_url}">Github site</a>. For project discussion,
            see our <a href="{forum_url}">Google Group</a>.
            </p>
            <p>
            This project is part of a larger effort to promote and
            facilitate the use of Python for scientific and engineering
            software development.
            The popular Python distributions
            <a href="https://www.anaconda.com/download/">Anaconda</a> and
            <a href="https://winpython.github.io/">WinPython</a>
            also contribute to this plan.
            </p>
            </div>""")

        self.label_legal = QLabel(
            f"""
            <div style='font-family: "{font_family}";
                        font-size: {font_size};
                        font-weight: normal;
                        '>
            <br>
            Copyright &copy; 2009-2020 Spyder Project Contributors and
            <a href="{project_url}/blob/master/AUTHORS.txt">others</a>.
            Distributed under the terms of the
            <a href="{project_url}/blob/master/LICENSE.txt">MIT License</a>.
            <p>
            <p>Certain source files under other compatible permissive
            licenses and/or originally by other authors.
            Spyder 3 theme icons derived from
            <a href="https://fontawesome.com/">Font Awesome</a> 4.7
            (&copy; 2016 David Gandy; SIL OFL 1.1) and
            <a href="http://materialdesignicons.com/">Material Design</a>
            (&copy; 2014 Austin Andrews; SIL OFL 1.1).
            </p>
            <p>
            Splash screen photo by
            <a href="https://unsplash.com/@benchaccounting?utm_source=
            unsplash&utm_medium=referral&utm_content=creditCopyText">Bench
            Accounting</a> on <a href="https://unsplash.com/?utm_source=
            unsplash&utm_medium=referral&utm_content=creditCopyText">Unsplash
            </a>.
            </p>
            <p>
            See the
            <a href="{project_url}/blob/master/NOTICE.txt">NOTICE</a>
            file for full legal information.
            </p>
            </div>
            """)

        for label in [self.label_overview, self.label_community,
                      self.label_legal]:
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignTop)
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            label.setContentsMargins(
                (3 if MAC else 1) * self.PADDING,
                0,
                (3 if MAC else 1) * self.PADDING,
                (3 if MAC else 1) * self.PADDING,
            )

        self.label_pic = QLabel(self)
        self.label_pic.setPixmap(
            self.svg_to_scaled_pixmap("spyder_about", rescale=0.45)
        )
        self.label_pic.setAlignment(Qt.AlignBottom)

        self.info = QLabel(
            f"""
            <div style='font-family: "{font_family}";
                font-size: {font_size};
                font-weight: normal;
                '>
            {versions['spyder']}
            <br>{revlink}
            <br>({versions['installer']})
            <br>
            """
        )
        self.info.setAlignment(Qt.AlignHCenter)

        # -- Scroll areas
        scroll_overview = QScrollArea(self)
        scroll_overview.setWidgetResizable(True)
        scroll_overview.setWidget(self.label_overview)

        scroll_community = QScrollArea(self)
        scroll_community.setWidgetResizable(True)
        scroll_community.setWidget(self.label_community)

        scroll_legal = QScrollArea(self)
        scroll_legal.setWidgetResizable(True)
        scroll_legal.setWidget(self.label_legal)

        # Style for scroll areas needs to be applied after creating them.
        # Otherwise it doesn't have effect.
        for scroll_area in [scroll_overview, scroll_community, scroll_legal]:
            scroll_area.setStyleSheet(self._scrollarea_stylesheet)

        # -- Tabs
        self.tabs = QTabWidget(self)
        self.tabs.addTab(scroll_overview, _('Overview'))
        self.tabs.addTab(scroll_community, _('Community'))
        self.tabs.addTab(scroll_legal, _('Legal'))
        self.tabs.setElideMode(Qt.ElideNone)
        self.tabs.setStyleSheet(self._tabs_stylesheet)

        # -- Buttons
        bbox = SpyderDialogButtonBox(QDialogButtonBox.Ok)
        info_btn = QPushButton(_("Copy version info"))
        bbox.addButton(info_btn, QDialogButtonBox.ActionRole)

        # Apply style to buttons
        bbox.setStyleSheet(self._button_stylesheet)

        # -- Widget setup
        self.setWindowIcon(ima.icon('MessageBoxInformation'))
        self.setModal(False)

        # -- Layout
        piclayout = QVBoxLayout()
        piclayout.addStretch()
        piclayout.addWidget(self.label_pic)
        piclayout.addSpacing(-5)
        piclayout.addWidget(self.info)
        piclayout.addStretch()
        piclayout.setContentsMargins(
            # This makes the left and right margins around the image and info
            # to be the same on Linux and Windows.
            self.PADDING - (0 if MAC else 1) * AppStyle.MarginSize,
            0,
            self.PADDING,
            0
        )

        tabslayout = QHBoxLayout()
        tabslayout.addWidget(self.tabs)
        tabslayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        tabslayout.setContentsMargins(0, self.PADDING, 0, 0)

        btmhlayout = QHBoxLayout()
        btmhlayout.addStretch(1)
        btmhlayout.addWidget(bbox)
        btmhlayout.setContentsMargins(0, 0, self.PADDING, self.PADDING)
        btmhlayout.addStretch()

        vlayout = QVBoxLayout()
        vlayout.addLayout(tabslayout)
        vlayout.addLayout(btmhlayout)
        vlayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        mainlayout = QHBoxLayout(self)
        mainlayout.addLayout(piclayout)
        # This compensates the margin set for scroll areas to center them on
        # the tabbar
        mainlayout.addSpacing(-self.PADDING)
        mainlayout.addLayout(vlayout)

        # -- Signals
        info_btn.clicked.connect(self.copy_to_clipboard)
        bbox.accepted.connect(self.accept)

        # -- Style
        size = (600, 460) if MAC else ((585, 450) if WIN else (610, 455))
        self.setFixedSize(*size)
        self.setStyleSheet(self._main_stylesheet)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(get_versions_text())

    @property
    def _main_stylesheet(self):
        tabs_stylesheet = PREFERENCES_TABBAR_STYLESHEET.get_copy()
        css = tabs_stylesheet.get_stylesheet()

        # Set background color
        for widget in ["QDialog", "QLabel"]:
            css[widget].setValues(
                backgroundColor=DialogStyle.BackgroundColor
            )

        return css.toString()

    @property
    def _scrollarea_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # This is the only way to make the scroll areas to have the same
        # background color as the other widgets in the dialog.
        css.setValues(
            backgroundColor=DialogStyle.BackgroundColor
        )

        css.QScrollArea.setValues(
            # Default border color doesn't have enough contrast with the
            # background.
            border=f"1px solid {DialogStyle.BorderColor}",
            # This is necessary to center the tabbar on the scroll area
            marginLeft=f"{self.PADDING}px"
        )

        css.QScrollBar.setValues(
            # Default border color doesn't have enough contrast with the
            # background.
            border=f"1px solid {DialogStyle.BorderColor}",
        )

        return css.toString()

    @property
    def _button_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # Increase font size and padding
        css.QPushButton.setValues(
            fontSize=DialogStyle.ButtonsFontSize,
            padding=DialogStyle.ButtonsPadding
        )

        return css.toString()

    @property
    def _tabs_stylesheet(self):
        css = qstylizer.style.StyleSheet()

        # This fixes a visual glitch with the tabbar background color
        css.setValues(
            backgroundColor=DialogStyle.BackgroundColor
        )

        css['QTabWidget::pane'].setValues(
            # Set tab pane margins according to the dialog contents and layout
            marginTop=f"{(3 if MAC else 2) * AppStyle.MarginSize}px",
            marginRight=f"{self.PADDING}px",
            marginBottom=f"{(0 if MAC else 2) * AppStyle.MarginSize}px",
            marginLeft="0px",
            # Padding is not necessary in this case because we set a border for
            # the scroll areas.
            padding="0px",
        )

        return css.toString()


def test():
    """Run about widget test"""

    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # noqa
    abt = AboutDialog(None)
    abt.show()
    sys.exit(abt.exec_())


if __name__ == '__main__':
    test()
