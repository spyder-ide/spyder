# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Module with functions to check the spyder latest updates and release versions.
"""

# Standard library imports
from collections import OrderedDict
import bz2
import json
import logging
import os
import re
import ssl
import sys

# Third party imports
from qtpy.QtCore import QObject, Signal
import chardet

# Local imports
from spyder import __version__
from spyder.config.base import _, is_stable_version
from spyder.py3compat import PY3, is_text_string
from spyder.config.utils import is_anaconda
from spyder.utils.programs import check_version


if PY3:
    from urllib.request import Request, urlopen
    from urllib.error import URLError, HTTPError
else:
    from urllib2 import Request, urlopen, URLError, HTTPError


logger = logging.getLogger(__name__)


def get_encoding(headers, raw_data):
    """Get encoding from headers."""
    content_type = headers.get('Content-Type',
                               headers.get('content-type', ''))
    content_type = content_type.lower()
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1].strip()
    else:
        results = chardet.detect(raw_data)
        if results.get('encoding') is None:
            if os.name == 'nt':
                encoding = 'cp-1252'  # 'iso-8859-1'
            else:
                encoding = 'utf-8'
        else:
            encoding = results.get('encoding')
    return encoding


# TODO: This could be moved to a dowloand and url handling module/utils?
def download(url):
    """Download and decode data from url."""
    headers = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 '
                       '(KHTML, like Gecko) Chrome/23.0.1271.64 '
                       'Safari/537.11'),
        'Accept': ('text/html,application/xhtml+xml,'
                   'application/xml;q=0.9,*/*;q=0.8'),
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive',
    }
    req = Request(url, headers=headers)

    if hasattr(ssl, '_create_unverified_context'):
        # Fix for issue #2685 [Works only with Python >=2.7.9]
        # More info: https://www.python.org/dev/peps/pep-0476/#opting-out
        context = ssl._create_unverified_context()
        page = urlopen(req, context=context)
    else:
        page = urlopen(req)

    raw_data = page.read()

    # Needed step for Python 3 compatibility
    if not is_text_string(raw_data):
        headers = dict(page.info())
        encoding = get_encoding(headers, raw_data)
        raw_data = raw_data.decode(encoding)

    return raw_data


def check_update_available(version, releases):
    """Checks if there is an update available.

    It takes as parameters the current version of Spyder and a list of
    valid cleaned releases in chronological order.
    """
    # Filter releases
    if is_stable_version(version):
        releases = [r for r in releases if is_stable_version(r)]
    else:
        releases = [r for r in releases
                    if not is_stable_version(r) or r in version]

    latest_release = releases[-1] if releases else version

    return check_version(version, latest_release, '<'), latest_release


def get_updates_url(anaconda=True):
    """Returns the url to use for downloading release versions data."""
    if anaconda:
        url = 'https://repo.anaconda.com/pkgs/main'
        # We could use .bz2 files but encoding is not provided
        if os.name == 'nt':
            url += '/win-64/repodata.json'
        elif sys.platform == 'darwin':
            url += '/osx-64/repodata.json'
        else:
            url += '/linux-64/repodata.json'
    else:
        url = 'https://api.github.com/repos/spyder-ide/spyder/releases'

    return url


def process_releases(data, anaconda=True):
    """Load releases data."""
    releases = []
    if anaconda:
        for item in data['packages']:
            # The 'spyder-[a-zA-Z]' is to avoid packages like spyder-kernels
            if ('spyder' in item and not re.search(r'spyder-[a-zA-Z]', item)):
                # Example: ['spyder-3.3.3-py36_0.tar.bz2', ...]
                release_version = item.split('-')[1]

                # Example: ['2.3.2', '2.3.3' ...]
                if release_version not in releases:
                    releases.append(release_version)
    else:
        releases = [item['tag_name'].replace('v', '') for item in data]
        # With github ['2.3.4', '2.3.3' ...], so we reverse the list
        releases = list(reversed(releases))

    return releases


def check_updates(version=None, releases=None):
    """Check for Spyder updates."""
    update_available, latest_release, error_msg = False, __version__, None
    version = version if version is not None else __version__

    # Don't perform any check for development versions
    if 'dev' not in version.lower():
        anaconda = is_anaconda()
        url = get_updates_url(anaconda)
        try:
            raw_data = download(url)
            if anaconda and url.endswith('.bz2'):
                raw_data = bz2.decompress(raw_data)

            try:
                # Needed to preserve order
                # See: https://stackoverflow.com/questions/6921699/
                data = json.loads(raw_data, object_pairs_hook=OrderedDict)
                releases = releases if releases else process_releases(data)
                result = check_update_available(version, releases)
                update_available, latest_release = result
            except Exception as err:
                logger.error(err)
                error_msg = _('Unable to retrieve information.')
        except HTTPError:
            error_msg = _('Unable to retrieve information.')
        except URLError:
            error_msg = _('Unable to connect to the internet. <br><br>Make '
                          'sure the connection is working properly.')
        except Exception as err:
            logger.error(err)
            error_msg = _('Unable to check for updates.')

    return update_available, latest_release, error_msg
