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
                            QHBoxLayout, QVBoxLayout, QLabel, QPushButton, )

# Local imports
from spyder import (__project_url__, __forum_url__,
                    __trouble_url__, __website_url__, get_versions)
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.image_path_manager import get_image_path


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
            revlink = " (<a href='https://github.com/spyder-ide/spyder/" \
                      "commit/%s'>Commit: %s</a>)" % (rev, rev)

        # Get current font properties
        font = self.font()
        font_family = font.family()
        font_size = font.pointSize()
        if sys.platform == 'darwin':
            font_size -= 2

        self.label = QLabel((
            """
            <div style='font-family: "{font_family}";
                        font-size: {font_size}pt;
                        font-weight: normal;
                        '>
            <p>
            <b>Spyder {spyder_ver}</b> {revision}
            <br>
            The Scientific Python Development Environment |
            <a href="{website_url}">Spyder-IDE.org</a>
            <br>
            Copyright &copy; 2009-2020 Spyder Project Contributors and
            <a href="{github_url}/blob/master/AUTHORS.txt">others</a>.
            <br>
            Distributed under the terms of the
            <a href="{github_url}/blob/master/LICENSE.txt">MIT License</a>.
            </p>
            <p>
            Created by Pierre Raybaut; current maintainer is Carlos Cordoba.
            Developed by the
            <a href="{github_url}/graphs/contributors">international
            Spyder community</a>. Many thanks to all the Spyder beta testers
            and dedicated users.
            </p>
            <p>For help with Spyder errors and crashes, please read our
            <a href="{trouble_url}">Troubleshooting Guide</a>, and for bug
            reports and feature requests, visit our
            <a href="{github_url}">Github site</a>. For project discussion,
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
            <p>
            Python {python_ver} {bitness}-bit | Qt {qt_ver} |
            {qt_api} {qt_api_ver} | {os_name} {os_ver}
            </p>
            <p><small>Certain source files under other compatible permissive
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
            (&copy; 2007 KDE Artists; LGPL 3.0+).</small>
            </p>
            <p>
            See the <a href="{github_url}/blob/master/NOTICE.txt">NOTICE</a>
            file for full legal information.
            </p>
            </div>
            """).format(
                spyder_ver=versions['spyder'],
                revision=revlink,
                website_url=__website_url__,
                github_url=__project_url__,
                trouble_url=__trouble_url__,
                forum_url=__forum_url__,
                python_ver=versions['python'],
                bitness=versions['bitness'],
                qt_ver=versions['qt'],
                qt_api=versions['qt_api'],
                qt_api_ver=versions['qt_api_ver'],
                os_name=versions['system'],
                os_ver=versions['release'],
                font_family=font_family,
                font_size=font_size,
            )
        )
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop)
        self.label.setOpenExternalLinks(True)
        self.label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.label.setFixedWidth(350)

        icon_filename = "spyder_about"
        pixmap = QPixmap(get_image_path(icon_filename))
        self.label_pic = QLabel(self)
        self.label_pic.setPixmap(
            pixmap.scaledToWidth(64, Qt.SmoothTransformation))
        self.label_pic.setAlignment(Qt.AlignTop)

        btn = QPushButton(_("Copy to clipboard"), )
        bbox = QDialogButtonBox(QDialogButtonBox.Ok)

        # Widget setup
        self.setWindowIcon(ima.icon('MessageBoxInformation'))
        self.setModal(False)

        # Layout
        tophlayout = QHBoxLayout()
        tophlayout.addWidget(self.label_pic)
        tophlayout.addWidget(self.label)

        btmhlayout = QHBoxLayout()
        btmhlayout.addWidget(btn)
        btmhlayout.addStretch()
        btmhlayout.addWidget(bbox)

        vlayout = QVBoxLayout(self)
        vlayout.addLayout(tophlayout)
        vlayout.addSpacing(25)
        vlayout.addLayout(btmhlayout)
        vlayout.setSizeConstraint(vlayout.SetFixedSize)

        # Signals
        btn.clicked.connect(self.copy_to_clipboard)
        bbox.accepted.connect(self.accept)

    def copy_to_clipboard(self):
        versions = get_versions()
        QApplication.clipboard().setText(
            "* Spyder version: {spyder_ver} {revision}\n"
            "* Python version: {python_ver} {bitness}-bit\n"
            "* Qt version: {qt_ver}\n"
            "* {qt_api} version: {qt_api_ver}\n"
            "* Operating System: {os_name} {os_ver}".format(
                spyder_ver=versions['spyder'],
                revision=versions['revision'],
                python_ver=versions['python'],
                bitness=versions['bitness'],
                qt_ver=versions['qt'],
                qt_api=versions['qt_api'],
                qt_api_ver=versions['qt_api_ver'],
                os_name=versions['system'],
                os_ver=versions['release']))


def test():
    """Run about widget test"""

    from spyder.utils.qthelpers import qapplication
    qapplication()
    abt = AboutDialog(None)
    abt.show()
    sys.exit(abt.exec_())


if __name__ == '__main__':
    test()
