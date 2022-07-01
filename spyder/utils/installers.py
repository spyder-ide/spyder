# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Utility functions for tesing Spyder installers."""

import os
import glob
import textwrap
import logging

from spyder.config.base import get_conf_path


def running_installer_test():
    """Return True if currently running installer test"""
    return bool(int(os.environ.get('INSTALLER_TEST', '0')))


class SpyderInstallerError(object):
    """
    Base class for installer error; do not use directly.
    Exit Spyder with code 1.
    """
    logger = logging.getLogger('Installer')
    logger.setLevel(logging.DEBUG)
    def __init__(self, msg):
        if not running_installer_test():
            # Don't do anything
            return

        msg = self._msg(msg)

        self.logger.error(msg + '\n', stack_info=True)

        raise SystemExit(1)

    def _msg(self, msg):
        raise NotImplementedError()


class InstallerMissingDependencies(SpyderInstallerError):
    """Error for missing dependencies"""
    def _msg(self, msg):
        msg = msg.replace('<br>', '\n')
        msg = 'Missing dependencies' + textwrap.indent(msg, '  ')

        return msg


class InstallerIPythonKernelError(SpyderInstallerError):
    """Error for IPython kernel issues"""
    def _msg(self, msg):
        msg = msg.replace('<tt>', '').replace('</tt>', '')
        msg = 'IPython kernel error\n' + textwrap.indent(msg, '  ')

        return msg


class InstallerInternalError(SpyderInstallerError):
    """Error for internal issues"""
    def _msg(self, msg):
        msg = 'Spyder internal error\n' + textwrap.indent(msg, '  ')

        return msg


class InstallerPylspError(SpyderInstallerError):
    """Error for PyLSP issues"""
    def _msg(self, msg):

        files = glob.glob(os.path.join(get_conf_path('lsp_logs'), '*.log'))
        cat = ''
        for file in files:
            cat += f'{file}\n'
            with open(file, 'r') as f:
                cat += textwrap.indent(f.read(), '  ')

        msg = f'PyLSP Error: {msg}\n' + textwrap.indent(cat, '  ')

        return msg
