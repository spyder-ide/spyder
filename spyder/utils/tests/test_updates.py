# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------
"""
Tests for spyder update checking utilities.
"""

# Standard library imports
from collections import OrderedDict
import bz2
import json

# Third party imports
import pytest

# Local imports
from spyder.config.utils import is_anaconda
from spyder.utils.updates import (check_update_available, check_updates,
                                  download, get_updates_url, process_releases,
                                  urlopen)


# Example data
ANACONDA_RELEASES = ['3.2.3', '3.2.4', '3.2.5', '3.2.6', '3.2.7', '3.2.8',
                     '3.3.0', '3.3.1', '3.3.2', '3.3.3']

GITHUB_RELEASES = ['3.0.0b2', '2.3.9', '3.0.0b3', '3.0.0b4', '3.0.0b5',
                   '3.0.0b6', '3.0.0b7', '3.0.0', '3.0.1', '3.0.2',
                   '3.1.0', '3.1.1', '3.1.2', '3.1.3', '3.1.4', '3.2.0',
                   '3.2.1', '3.2.2', '3.2.3', '3.2.4', '3.2.5', '3.2.6',
                   '3.2.7', '3.2.8', '3.3.0', '3.3.1', '4.0.0b1', '3.3.2',
                   '3.3.3', '3.3.4']
RELEASE_TYPES = [ANACONDA_RELEASES, GITHUB_RELEASES]


def test_download():
    """Test download util."""
    data = download(url='https://www.google.com/')
    assert '<title>Google</title>' in data


def test_check_update_available():
    """Test different version combinations."""
    for releases in RELEASE_TYPES:
        # Test we offer updates for lower versions
        update, _ = check_update_available("1.0.0", releases=releases)
        assert update

        # Test we don't offer updates for very high versions.
        update, _ = check_update_available("1000.0.0", releases=releases)
        assert not update

    # Test we don't offer updates for development versions
    update, _ = check_update_available("3.3.2.dev0", releases=['3.3.1'])
    assert not update

    # Test we offer updates between prereleases
    update, _ = check_update_available('4.0.0a1', releases=['4.0.0b5'])
    assert update

    # Test we offer updates from prereleases to the final versions
    update, _ = check_update_available('4.0.0b3', releases=['4.0.0'])
    assert update


def test_get_updates_url():
    """Check that the urls for anaconda and github are valid."""
    for value in [True, False]:
        url = get_updates_url(anaconda=value)
        response = urlopen(url)
        info = dict(response.info())
        content_type = info.get('Content-Type', info.get('content-type', ''))
        assert content_type.lower().startswith('application/json')


def test_process_releases_live_data():
    """Test the api remains consistent."""
    for value in [True, False]:
        url = get_updates_url(anaconda=value)
        raw_data = download(url)

        if value and url.endswith('.bz2'):
            raw_data = bz2.decompress(raw_data)

        data = json.loads(raw_data, object_pairs_hook=OrderedDict)
        releases = process_releases(data, anaconda=value)

        if value:
            assert '0.2.4' not in releases
        else:
            assert '3.3.4' in releases


def test_process_releases_mock_data():
    """Test we don't include spyder-kernels releases in detected releases."""
    anaconda_data = {
        "info": {
            "subdir": "osx-64"
        },
        "packages": {
            'spyder-3.2.3-py27h7402f24_0.tar.bz2': None,
            'spyder-kernels-0.2.4-py27_0.tar.bz2': None,
        }
    }
    releases = process_releases(anaconda_data, anaconda=True)
    assert '0.2.4' not in releases

    github_data = [{"tag_name": "v3.3.4"}, {"tag_name": "v3.3.3"}]
    releases = process_releases(github_data, anaconda=False)
    assert ['3.3.3', '3.3.4'] == releases


def test_check_updates():
    """Test the complete update checking process."""
    update_available, latest_release, error_msg = check_updates()

    # Since this will run on CI servers, it should return `False`
    assert not update_available

    # Latest release will be the either the latest or the current
    # one, so this will always return a valid version string
    assert bool(latest_release)

    # There should not be any error messages from this process running
    # on CI servers (Unless there are connectivity problems)
    assert error_msg is None


if __name__ == "__main__":
    pytest.main()
