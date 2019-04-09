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
import requests

# Local imports
from spyder import __version__
from spyder.config.base import _, is_stable_version
from spyder.py3compat import PY3, is_text_string
from spyder.config.utils import is_anaconda
from spyder.utils.programs import check_version


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


def download(url):
    """
    Download and return the response object from requests.

    Adds headers to avoid 403 errors.
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    return response


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
            url += '/win-64/repodata.json.bz2'
        elif sys.platform == 'darwin':
            url += '/osx-64/repodata.json.bz2'
        else:
            url += '/linux-64/repodata.json.bz2'
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
            response = download(url)
            raw_data = response.content
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
