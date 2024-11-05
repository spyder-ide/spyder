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

SPYDER_REMOTE_MIN_VERSION = "0.1.3"
SPYDER_REMOTE_MAX_VERSION = '1.0.0'
SPYDER_REMOTE_VERSION = (
    f'>={SPYDER_REMOTE_MIN_VERSION},<{SPYDER_REMOTE_MAX_VERSION}'
)

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
        f'"{SPYDER_REMOTE_VERSION}" "{SPYDER_KERNELS_VERSION}"'
    )


def get_server_version_command(platform: str) -> str:
    return (
        f"${{HOME}}/.local/bin/micromamba run -n {SERVER_ENV} python -c "
        "'import spyder_remote_services as sprs; print(sprs.__version__)'"
    )
