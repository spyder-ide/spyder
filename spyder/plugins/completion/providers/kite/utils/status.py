# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite status functions."""

# Standard library imports
from functools import lru_cache
import logging
import os
import os.path as osp
import subprocess
import sys

# Third-party imports
import psutil
import requests

NOT_INSTALLED = 'not installed'
RUNNING = 'ready'
NOT_RUNNING = 'not running'

# Installer URLs
WINDOWS_URL = "https://release.kite.com/dls/windows/current"
LINUX_URL = "https://release.kite.com/dls/linux/current"
MAC_URL = "https://release.kite.com/dls/mac/current"

logger = logging.getLogger(__name__)


def check_if_kite_installed():
    """Detect if kite is installed and return the installation path."""
    path = ''
    if os.name == 'nt':
        path = 'C:\\Program Files\\Kite\\kited.exe'
    elif sys.platform.startswith('linux'):
        path = osp.expanduser('~/.local/share/kite/kited')
    elif sys.platform == 'darwin':
        path = locate_kite_darwin()
    return osp.exists(osp.realpath(path)), path


def check_if_kite_running():
    """Detect if kite is running."""
    running = False
    try:
        for proc in psutil.process_iter(attrs=['pid', 'name', 'username',
                                               'status']):
            if is_proc_kite(proc):
                logger.debug('Kite process already '
                             'running with PID {0}'.format(proc.pid))
                running = True
                break
    except OSError:
        # Needed to handle a possible WinError 0. See spyder-ide/spyder#12510
        pass
    return running


@lru_cache(maxsize=1)
def locate_kite_darwin():
    """
    Looks up where Kite.app is installed on macOS systems. The bundle ID
    is checked first and if nothing is found or an error occurs, the
    default path is used.
    """
    default_path = '/Applications/Kite.app'
    path = ''
    try:
        out = subprocess.check_output(
            ['mdfind', 'kMDItemCFBundleIdentifier="com.kite.Kite"'])
        installed = len(out) > 0
        path = (out.decode('utf-8', 'replace').strip().split('\n')[0]
                if installed else default_path)
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        # Use the default path
        path = default_path
    finally:
        return path


def is_proc_kite(proc):
    try:
        # This is raising `ZombieProcess: psutil.ZombieProcess` on OSX
        # if kite is not running.
        name = proc.name()
    except Exception:
        name = ''

    if os.name == 'nt' or sys.platform.startswith('linux'):
        is_kite = 'kited' in name and proc.status() != 'zombie'
    else:
        is_kite = 'Kite' == name

    return is_kite


def status(extra_status=''):
    """Kite completions status: not installed, ready, not running."""
    kite_installed, _ = check_if_kite_installed()
    if not kite_installed:
        return NOT_INSTALLED + extra_status
    elif check_if_kite_running():
        return RUNNING + extra_status
    else:
        return NOT_RUNNING + extra_status


def check_kite_installers_availability():
    """Check if Kite installers are available."""
    url = LINUX_URL
    if os.name == 'nt':
        url = WINDOWS_URL
    elif sys.platform == 'darwin':
        url = MAC_URL

    available = False
    try:
        req = requests.head(url, timeout=0.2)
        available = req.ok
        if req.ok:
            if req.is_redirect:
                loc = req.headers['Location']
                req = requests.head(loc)
                available = req.ok
    except Exception:
        pass
    return available
