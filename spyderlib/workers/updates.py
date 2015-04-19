# -*- coding: utf-8 -*-
#
# Copyright © 2009-2013 Pierre Raybaut
# Copyright © 2013-2015 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

import json


from spyderlib import __version__
from spyderlib.baseconfig import _
from spyderlib.py3compat import PY3
from spyderlib.qt.QtGui import QMessageBox, QCheckBox, QSpacerItem, QVBoxLayout
from spyderlib.qt.QtCore import Signal, Qt, QObject
from spyderlib.utils.programs import check_version


if PY3:
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
else:
    from urllib2 import urlopen, URLError, HTTPError


class MessageCheckBox(QMessageBox):
    """
    A QMessageBox derived widget that includes a QCheckBox aligned to the right
    under the message and on top of the buttons.
    """
    def __init__(self, *args, **kwargs):
        super(MessageCheckBox, self).__init__(*args, **kwargs)

        self._checkbox = QCheckBox()

        # Set layout to include checkbox
        size = 9
        check_layout = QVBoxLayout()
        check_layout.addItem(QSpacerItem(size, size))
        check_layout.addWidget(self._checkbox, 0, Qt.AlignRight)
        check_layout.addItem(QSpacerItem(size, size))

        # Access the Layout of the MessageBox to add the Checkbox
        layout = self.layout()
        layout.addLayout(check_layout, 1, 1)

    # --- Public API
    # Methods to access the checkbox
    def is_checked(self):
        return self._checkbox.isChecked()

    def set_checked(self, value):
        return self._checkbox.setChecked(value)

    def set_check_visible(self, value):
        self._checkbox.setVisible(value)

    def is_check_visible(self):
        self._checkbox.isVisible()

    def checkbox_text(self):
        self._checkbox.text()

    def set_checkbox_text(self, text):
        self._checkbox.setText(text)


class WorkerUpdates(QObject):
    """
    Worker that checks for releases using the Github API without blocking the
    Spyder user interface, in case of connections issues.
    """
    sig_ready = Signal()

    def __init__(self, parent, feedback):
        QObject.__init__(self)
        self._parent = parent
        self.feedback = feedback
        self.error = feedback
        self.latest_release = None

    def is_stable_version(self, version):
        """
        A stable version has no letters in the final part, it has only numbers.

        Stable version example: 1.2, 1.3.4, 1.0.5
        Not stable version: 1.2alpha, 1.3.4beta, 0.1.0rc1, 3.0.0dev
        """
        if not isinstance(version, tuple):
            version = version.split('.')
        last_part = version[-1]

        try:
            int(last_part)
            return True
        except ValueError:
            return False

    def check_update_available(self, version, releases):
        """Checks if there is an update available.

        It takes as parameters the current version of Spyder and a list of
        valid cleaned releases in chronological order (what github api returns
        by default). Example: ['2.3.4', '2.3.3' ...]"""
        if self.is_stable_version(version):
            # Remove non stable versions from the list
            releases = [r for r in releases if self.is_stable_version(r)]

        latest_release = releases[0]

        if version.endswith('dev'):
            return (False, latest_release)

        # check_version is based on LooseVersion, so a small hack is needed so
        # that LooseVersion understands that '3.0.0' is in fact bigger than
        # '3.0.0rc1'
        if self.is_stable_version(latest_release) and \
          version.startswith(latest_release) and latest_release != version:
            parts = latest_release.split('.')
            parts = parts[:-1] + [parts[-1] + 'z']
            latest_mod = '.'.join(parts)
        else:
            latest_mod = releases[0]

        return (check_version(version, latest_mod, '<'), latest_release)

    def start(self):
        """Main method of the WorkerUpdates worker"""
        self.url = 'https://api.github.com/repos/spyder-ide/spyder/releases'
        self.update_available = False
        self.latest_release = __version__

        error_msg = None
        try:
            page = urlopen(self.url)
            try:
                data = page.read()
                if not isinstance(data, str):
                    data = data.decode()
                data = json.loads(data)
                releases = [item['tag_name'].replace('v', '') for item in data]
                version = __version__
                result = self.check_update_available(version, releases)
                self.update_available, self.latest_release = result
            except Exception:
                error_msg = _('Unable to retrieve information.')
        except HTTPError:
            error_msg = _('Unable to retrieve information.')
        except URLError:
            error_msg = _('Unable to connect to the internet. <br><br>Make '
                          'sure the connection is working properly.')
        except Exception:
            error_msg = _('Unable to check for updates.')

        self.error = error_msg
        self.sig_ready.emit()


def test_msgcheckbox():
    from spyderlib.utils.qthelpers import qapplication
    app = qapplication()
    app.setStyle('Plastique')
    box = MessageCheckBox()
    box.setWindowTitle(_("Spyder updates"))
    box.setText("Testing checkbox")
    box.set_checkbox_text("Check for updates on startup?")
    box.setStandardButtons(QMessageBox.Ok)
    box.setDefaultButton(QMessageBox.Ok)
    box.setIcon(QMessageBox.Information)
    box.exec_()

if __name__ == '__main__':
    test_msgcheckbox()
