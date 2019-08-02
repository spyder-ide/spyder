# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import json
import os
import re
import ssl
import sys

# Third party imports
from qtpy.QtCore import QObject, Signal

# Local imports
from spyder import __version__
from spyder.config.base import _, is_stable_version
from spyder.py3compat import PY3, is_text_string
from spyder.config.utils import is_anaconda
from spyder.utils.programs import check_version


if PY3:
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
else:
    from urllib2 import urlopen, URLError, HTTPError


class WorkerUpdates(QObject):
    """
    Worker that checks for releases using either the Anaconda
    default channels or the Github Releases page without
    blocking the Spyder user interface, in case of connection
    issues.
    """
    sig_ready = Signal()

    def __init__(self, parent, startup, version="", releases=None):
        QObject.__init__(self)
        self._parent = parent
        self.error = None
        self.latest_release = None
        self.startup = startup
        self.releases = releases

        if not version:
            self.version = __version__
        else:
            self.version = version

    def check_update_available(self):
        """Checks if there is an update available.

        It takes as parameters the current version of Spyder and a list of
        valid cleaned releases in chronological order.
        Example: ['2.3.2', '2.3.3' ...] or with github ['2.3.4', '2.3.3' ...]
        """
        # Don't perform any check for development versions
        if 'dev' in self.version:
            return (False, latest_release)

        # Filter releases
        if is_stable_version(self.version):
            releases = [r for r in self.releases if is_stable_version(r)]
        else:
            releases = [r for r in self.releases
                        if not is_stable_version(r) or r in self.version]

        latest_release = releases[-1]

        return (check_version(self.version, latest_release, '<'),
                latest_release)

    def start(self):
        """Main method of the WorkerUpdates worker"""
        if is_anaconda():
            self.url = 'https://repo.anaconda.com/pkgs/main'
            if os.name == 'nt':
                self.url += '/win-64/repodata.json'
            elif sys.platform == 'darwin':
                self.url += '/osx-64/repodata.json'
            else:
                self.url += '/linux-64/repodata.json'
        else:
            self.url = ('https://api.github.com/repos/'
                        'spyder-ide/spyder/releases')
        self.update_available = False
        self.latest_release = __version__

        error_msg = None

        try:
            if hasattr(ssl, '_create_unverified_context'):
                # Fix for spyder-ide/spyder#2685.
                # [Works only with Python >=2.7.9]
                # More info: https://www.python.org/dev/peps/pep-0476/#opting-out
                context = ssl._create_unverified_context()
                page = urlopen(self.url, context=context)
            else:
                page = urlopen(self.url)
            try:
                data = page.read()

                # Needed step for python3 compatibility
                if not is_text_string(data):
                    data = data.decode()
                data = json.loads(data)

                if is_anaconda():
                    if self.releases is None:
                        self.releases = []
                        for item in data['packages']:
                            if ('spyder' in item and
                                    not re.search(r'spyder-[a-zA-Z]', item)):
                                self.releases.append(item.split('-')[1])
                    result = self.check_update_available()
                else:
                    if self.releases is None:
                        self.releases = [item['tag_name'].replace('v', '')
                                         for item in data]
                        self.releases = list(reversed(self.releases))

                result = self.check_update_available()
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

        # Don't show dialog when starting up spyder and an error occur
        if not (self.startup and error_msg is not None):
            self.error = error_msg
            self.sig_ready.emit()
