# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Utilities for file explorer widgets.
"""

# Standard library imports
from __future__ import print_function
import glob
import itertools
import os
import sys

# Third party imports
from qtpy.QtGui import QIcon

# Local imports
from spyder.config.base import _, get_conf_path
from spyder.utils import icon_manager as ima


def parse_linux_desktop_entry(fpath):
    """Load data from desktop entry with xdg specification."""
    from xdg.DesktopEntry import DesktopEntry

    try:
        entry = DesktopEntry(fpath)
        entry_data = {}
        entry_data['name'] = entry.getName()
        entry_data['icon_path'] = entry.getIcon()
        entry_data['exec'] = entry.getExec()
        entry_data['type'] = entry.getType()
        entry_data['hidden'] = entry.getHidden()
        entry_data['fpath'] = fpath
    except Exception:
        entry_data = {
            'name': '',
            'icon_path': '',
            'hidden': '',
            'exec': '',
            'type': '',
            'fpath': fpath
        }

    return entry_data


def _get_mac_application_icon_path(app_bundle_path):
    """Parse mac application bundle and return path for *.icns file."""
    import plistlib
    contents_path = info_path = os.path.join(app_bundle_path, 'Contents')
    info_path = os.path.join(contents_path, 'Info.plist')

    pl = {}
    if os.path.isfile(info_path):
        try:
            # readPlist is deprecated but needed for py27 compat
            pl = plistlib.readPlist(info_path)
        except Exception:
            # TODO: Add the specific errors to catch
            pass

    icon_file = pl.get('CFBundleIconFile')
    icon_path = None
    if icon_file:
        icon_path = os.path.join(contents_path, 'Resources', icon_file)

        # Some app bundles seem to list the icon name without extension
        if not icon_path.endswith('.icns'):
            icon_path = icon_path + '.icns'

        if not os.path.isfile(icon_path):
            icon_path = None

    return icon_path


def get_username():
    """Return current session username."""
    if os.name == 'nt':
        username = os.getlogin()
    else:
        import pwd
        username = pwd.getpwuid(os.getuid())[0]

    return username


def _get_win_reg_info(key_path, hive, flag, subkeys):
    """
    See:
    https://stackoverflow.com/questions/53132434/list-of-installed-programs
    """
    import winreg

    reg = winreg.ConnectRegistry(None, hive)
    software_list = []
    try:
        key = winreg.OpenKey(reg, key_path, 0, winreg.KEY_READ | flag)
        count_subkey = winreg.QueryInfoKey(key)[0]

        for index in range(count_subkey):
            software = {}
            try:
                subkey_name = winreg.EnumKey(key, index)
                if not (subkey_name.startswith('{')
                        and subkey_name.endswith('}')):
                    software['key'] = subkey_name
                    subkey = winreg.OpenKey(key, subkey_name)
                    for property in subkeys:
                        try:
                            value = winreg.QueryValueEx(subkey, property)[0]
                            software[property] = value
                        except EnvironmentError:
                            software[property] = ''
                    software_list.append(software)
            except EnvironmentError:
                continue
    except Exception:
        pass

    return software_list


def _get_win_applications():
    """Return all system installed windows applications."""
    import winreg

    # See:
    # https://docs.microsoft.com/en-us/windows/desktop/shell/app-registration
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths'

    # Hive and flags
    hfs = [
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_CURRENT_USER, 0),
    ]
    subkeys = [None]
    sort_key = 'key'
    app_paths = {}
    _apps = [_get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        if software[None]:
            key = software['key'].capitalize().replace('.exe', '')
            app_paths[key] = software[None].lower()

    # See:
    # https://www.blog.pythonlibrary.org/2010/03/03/finding-installed-software-using-python/
    # https://stackoverflow.com/questions/53132434/list-of-installed-programs
    key_path = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall'
    subkeys = ['DisplayName', 'InstallLocation', 'DisplayIcon']
    sort_key = 'DisplayName'
    apps = {}
    _apps = [_get_win_reg_info(key_path, hf[0], hf[1], subkeys) for hf in hfs]
    software_list = itertools.chain(*_apps)
    for software in sorted(software_list, key=lambda x: x[sort_key]):
        location = software['InstallLocation']
        name = software['DisplayName']
        icon = software['DisplayIcon']
        key = software['key']
        if name and icon:
            icon = icon.replace('"', '').replace("'", '')
            icon = icon.split(',')[0]

            if location == '' and icon:
                location = os.path.dirname(icon)

            if not os.path.isfile(icon):
                icon = ''

            if location and os.path.isdir(location):
                files = [f for f in os.listdir(location)
                         if os.path.isfile(os.path.join(location, f))]
                if files:
                    for fname in files:
                        fn_low = fname.lower()
                        valid_file = fn_low.endswith(('.exe', '.com', '.bat'))
                        if valid_file and not fn_low.startswith('unins'):
                            fpath = os.path.join(location, fname)
                            apps[name + ' (' + fname + ')'] = fpath.lower()
    # Join data
    values = list(zip(*apps.values()))[-1]
    for name, fpath in app_paths.items():
        if fpath not in values:
            apps[name] = fpath

    return apps


def _get_linux_applications():
    """Return all system installed linux applications."""
    # See:
    # https://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
    # https://askubuntu.com/questions/433609/how-can-i-list-all-applications-installed-in-my-system
    apps = {}
    desktop_app_paths = [
        '/usr/share/**/*.desktop',
        '~/.local/share/**/*.desktop',
    ]
    all_entries_data = []
    for path in desktop_app_paths:
        fpaths = glob.glob(path)
        for fpath in fpaths:
            entry_data = parse_linux_desktop_entry(fpath)
            all_entries_data.append(entry_data)

    for entry_data in sorted(all_entries_data, key=lambda x: x['name']):
        if not entry_data['hidden'] and entry_data['type'] == 'Application':
            apps[entry_data['name']] = entry_data['fpath']

    return apps


def _get_mac_applications():
    """Return all system installed osx applications."""
    apps = {}
    app_folders = [
        '/**/*.app',
        '/Users/{}/**/*.app'.format(get_username())
    ]

    fpaths = []
    for path in app_folders:
        fpaths += glob.glob(path)

    for fpath in fpaths:
        if os.path.isdir(fpath):
            name = os.path.basename(fpath).split('.app')[0]
            apps[name] = fpath

    return apps


def get_application_icon(fpath):
    """Return application icon or default icon if not found."""
    if os.path.isfile(fpath) or os.path.isdir(fpath):
        icon = ima.icon('no_match')
        if sys.platform == 'darwin':
            icon_path = _get_mac_application_icon_path(fpath)
            if icon_path and os.path.isfile(icon_path):
                icon = QIcon(icon_path)
        elif os.name == 'nt':
            pass
        else:
            entry_data = parse_linux_desktop_entry(fpath)
            icon_path = entry_data['icon_path']
            if icon_path:
                if os.path.isfile(icon_path):
                    icon = QIcon(icon_path)
                else:
                    icon = QIcon.fromTheme(icon_path)
    else:
        icon = ima.icon('help')

    return icon


def get_installed_applications():
    """
    Return all system installed applications.

    The return value is a list of tuples where the first item is the icon path
    and the second item is the program executable path.
    """
    apps = {}
    if sys.platform == 'darwin':
        apps = _get_mac_applications()
    elif os.name == 'nt':
        apps = _get_win_applications()
    else:
        apps = _get_linux_applications()

    return apps
