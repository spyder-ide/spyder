# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from spyder.plugins.ipythonconsole import SPYDER_KERNELS_VERSION
from spyder.config.base import running_remoteclient_tests


SERVER_ENTRY_POINT = "spyder-server"
SERVER_ENV = "spyder-remote"
PACKAGE_NAME = "spyder-remote-services"
PACKAGE_VERSION = "0.1.3"

ENCODING = "utf-8"

SCRIPT_URL = (
    f"https://raw.githubusercontent.com/spyder-ide/{PACKAGE_NAME}/master/scripts"
)

def get_installer_command(platform: str) -> str:
    if platform == "win":
        raise NotImplementedError("Windows is not supported yet")
    
    if running_remoteclient_tests():
        return '\n'  # server should be aready installed in the test environment

    return (
        f'"${{SHELL}}" <(curl -L {SCRIPT_URL}/installer.sh) '
        f'"{PACKAGE_VERSION}" "{SPYDER_KERNELS_VERSION}"'
    )
