# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Module serving the "About Spyder" function"""

# Standard library imports
import sys

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                            QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
                            QScrollArea, QTabWidget)

# Local imports
from spyder import (
    __project_url__ as project_url,
    __forum_url__ as forum_url,
    __trouble_url__ as trouble_url,
    __website_url__ as website_url,
    get_versions, get_versions_text
)
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.palette import QStylePalette
from spyder.utils.stylesheet import APP_STYLESHEET, DialogStyle


class AboutDialog(QDialog):

    def __init__(self, parent):
        """Create About Spyder dialog with general information."""
        QDialog.__init__(self, parent)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        versions = get_versions()
        # Show Git revision for development version
        revlink = ''
        if versions['revision']:
            rev = versions['revision']
            revlink = ("<a href='https://github.com/spyder-ide/spyder/"
                       "commit/%s'>%s</a>" % (rev, rev))

        # Get current font properties
        font = self.font()
        font_family = font.family()
        buttons_padding = DialogStyle.ButtonsPadding
        buttons_font_size = DialogStyle.ButtonsFontSize
        font_size = DialogStyle.ContentFontSize
        dialog_background_color = QStylePalette.COLOR_BACKGROUND_2

        twitter_url = "https://twitter.com/Spyder_IDE",
        facebook_url = "https://www.facebook.com/SpyderIDE",
        youtube_url = "https://www.youtube.com/Spyder-IDE",
        instagram_url = "https://www.instagram.com/spyderide/",
        self.label_overview = QLabel(
            f"""
            <div style='font-family: "{font_family}";
                        font-size: {font_size};
                        font-weight: normal;
                        '>
            <br>
            <p>
            <b> Spyder IDE</b>
            <br> <br>
            The Scientific Python Development Environment |
            <a href="{website_url}">Spyder-IDE.org</a>
            <br>
            <p>
            Python {versions['python']} {versions['bitness']}-bit |
            Qt {versions['qt']} |
            {versions['qt_api']} {versions['qt_api_ver']} |
            {versions['system']} {versions['release']} ({versions['machine']})
            </p>
            <br> <br>
            <a href="{project_url}">GitHub</a> | <a href="{twitter_url}">
            Twitter</a> |
            <a href="{facebook_url}">Facebook</a> | <a href="{youtube_url}">
            YouTube</a> |
            <a href="{instagram_url}">Instagram</a>

            </div>""")

        self.label_community = QLabel(
            f"""
            <div style='font-family: "{font_family}";
                        font-size: {font_size};
                        font-weight: normal;
                        '>
            <br>
            <p>
            Created by Pierre Raybaut; current maintainer is Carlos Cordoba.
            Developed by the
            <a href="{project_url}/graphs/contributors">international
            Spyder community</a>. Many thanks to all the Spyder beta testers
            and dedicated users.
            </p>
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
            <p>
            Copyright &copy; 2009-2020 Spyder Project Contributors and
            <a href="{project_url}/blob/master/AUTHORS.txt">others</a>.
            Distributed under the terms of the
            <a href="{project_url}/blob/master/LICENSE.txt">MIT License</a>.
            </p>
            <p>
            <p>Certain source files under other compatible permissive
            licenses and/or originally by other authors.
            Spyder 3 theme icons derived from
            <a href="https://fontawesome.com/">Font Awesome</a> 4.7
            (&copy; 2016 David Gandy; SIL OFL 1.1) and
            <a href="http://materialdesignicons.com/">Material Design</a>
            (&copy; 2014 Austin Andrews; SIL OFL 1.1).
            Most Spyder 2 theme icons sourced from the
            <a href="https://www.everaldo.com">Crystal Project iconset</a>
            (&copy; 2006-2007 Everaldo Coelho; LGPL 2.1+).
            Other icons from
            <a href="http://p.yusukekamiyamane.com/">Yusuke Kamiyamane</a>
            (&copy; 2013 Yusuke Kamiyamane; CC-BY 3.0),
            the <a href="http://www.famfamfam.com/lab/icons/silk/">FamFamFam
            Silk icon set</a> 1.3 (&copy; 2006 Mark James; CC-BY 2.5), and
            the <a href="https://www.kde.org/">KDE Oxygen icons</a>
            (&copy; 2007 KDE Artists; LGPL 3.0+).
            </p>
            <p>
            Splash screen photo by
            <a href="https://unsplash.com/@benchaccounting?utm_source=
            unsplash&utm_medium=referral&utm_content=creditCopyText">Bench
            Accounting</a> on <a href="https://unsplash.com/?utm_source=
            unsplash&utm_medium=referral&utm_content=creditCopyText">Unsplash
            </a>
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
            label.setContentsMargins(15, 0, 25, 0)

        icon_filename = "spyder_about"
        pixmap = QPixmap(get_image_path(icon_filename))
        self.label_pic = QLabel(self)
        self.label_pic.setPixmap(
            pixmap.scaledToWidth(100, Qt.SmoothTransformation))
        self.label_pic.setAlignment(Qt.AlignBottom)
        self.info = QLabel((
            """
            <div style='font-family: "{font_family}";
                font-size: {font_size};
                font-weight: normal;
                '>
            <p>
            <b>Spyder IDE</b>
            <br>{spyder_ver}
            <br>{revision}
            <br>({installer})
            <br>""").format(
            spyder_ver=versions['spyder'],
            revision=revlink,
            installer=versions['installer'],
            font_family=font_family,
            font_size=font_size))
        self.info.setAlignment(Qt.AlignHCenter)

        btn = QPushButton(_("Copy version info"), )
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)
        bbox.setStyleSheet(f"font-size: {buttons_font_size};"
                           f"padding: {buttons_padding}")
        btn.setStyleSheet(f"font-size: {buttons_font_size};"
                          f"padding: {buttons_padding}")

        # Widget setup
        self.setWindowIcon(ima.icon('MessageBoxInformation'))
        self.setModal(False)

        # Layout
        piclayout = QVBoxLayout()
        piclayout.addWidget(self.label_pic)
        piclayout.addWidget(self.info)
        piclayout.setContentsMargins(20, 0, 15, 0)

        scroll_overview = QScrollArea(self)
        scroll_overview.setWidgetResizable(True)
        scroll_overview.setWidget(self.label_overview)

        scroll_community = QScrollArea(self)
        scroll_community.setWidgetResizable(True)
        scroll_community.setWidget(self.label_community)

        scroll_legal = QScrollArea(self)
        scroll_legal.setWidgetResizable(True)
        scroll_legal.setWidget(self.label_legal)

        self.tabs = QTabWidget()
        self.tabs.addTab(scroll_overview, _('Overview'))
        self.tabs.addTab(scroll_community, _('Community'))
        self.tabs.addTab(scroll_legal, _('Legal'))
        self.tabs.setStyleSheet(
            f"background-color: {dialog_background_color}")
        tabslayout = QHBoxLayout()
        tabslayout.addWidget(self.tabs)
        tabslayout.setSizeConstraint(tabslayout.SetFixedSize)
        tabslayout.setContentsMargins(0, 15, 15, 0)

        btmhlayout = QHBoxLayout()
        btmhlayout.addWidget(btn)
        btmhlayout.addWidget(bbox)
        btmhlayout.setContentsMargins(100, 20, 0, 20)
        btmhlayout.addStretch()

        vlayout = QVBoxLayout()
        vlayout.addLayout(tabslayout)
        vlayout.addLayout(btmhlayout)
        vlayout.setSizeConstraint(vlayout.SetFixedSize)

        mainlayout = QHBoxLayout(self)
        mainlayout.addLayout(piclayout)
        mainlayout.addLayout(vlayout)

        # Signals
        btn.clicked.connect(self.copy_to_clipboard)
        bbox.accepted.connect(self.accept)

        # Size
        self.resize(550, 430)

        # Style
        css = APP_STYLESHEET.get_copy()
        css = css.get_stylesheet()
        css.QDialog.setValues(backgroundColor=dialog_background_color)
        css.QLabel.setValues(backgroundColor=dialog_background_color)
        self.setStyleSheet(str(css))

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(get_versions_text())


def test():
    """Run about widget test"""

    from spyder.utils.qthelpers import qapplication
    app = qapplication()  # noqa
    abt = AboutDialog(None)
    abt.show()
    sys.exit(abt.exec_())


if __name__ == '__main__':
    test()
