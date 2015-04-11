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
from spyderlib.qt.QtGui import (QMessageBox, QCheckBox)
from spyderlib.qt.QtCore import Signal, Qt, QObject


class MessageCheckBox(QMessageBox):
    """
    A QMessageBox derived widget that includes a QCheckBox under the message
    and on top of the buttons.
    """
    def __init__(self, *args, **kwargs):
        super(MessageCheckBox, self).__init__(*args, **kwargs)

        self._checkbox = QCheckBox()

        # Access the Layout of the MessageBox to add the Checkbox
        layout = self.layout()
        layout.addWidget(self._checkbox, 1, 1, Qt.AlignRight)

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
        """ """
        from spyderlib.utils.programs import check_version

        if self.is_stable_version(version):
            # Remove non stable versions from the list
            releases = [r for r in releases if self.is_stable_version(r)]

        latest = releases[0]
        latest_release = releases[0]

        if version.endswith('dev'):
            return (False, latest_release)

        if self.is_stable_version(latest) and \
                version.startswith(latest) and latest != version:
            # Modify the last part so that i.e. 3.0.0 is bigger than 3.0.0rc2
            parts = latest.split('.')
            parts = parts[:-1] + [parts[-1] + 'z']
            latest = '.'.join(parts)

        return (check_version(version, latest, '<'), latest_release)

    def start(self):
        """ """
        if PY3:
            from urllib.request import urlopen
            from urllib.error import URLError, HTTPError
        else:
            from urllib2 import urlopen, URLError, HTTPError

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
            except Exception as error:
                #print(error)
                error_msg = _('Unable to retrieve information.')
        except HTTPError as error:
            error_msg = _('Unable to retrieve information.')
            msg = 'HTTPError = ' + str(error.code)
            #print(msg)
        except URLError as error:
            error_msg = _('Unable to connect to the internet. <br><br>Make '
                          'sure the connection is working properly.')
            msg = 'URLError = ' + str(error.reason)
            #print(msg)
        except Exception as error:
            error_msg = _('Unable to check for updates.')
            msg = error
            #print(msg)

        self.error = error_msg
        self.sig_ready.emit()
