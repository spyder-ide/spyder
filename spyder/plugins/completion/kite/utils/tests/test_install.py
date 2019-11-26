# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite install utilities test."""

# Local imports
import os
import re
import sys

# Third-party imports
import pytest

# Local imports
from spyder.plugins.completion.kite.utils.install import (
    KiteInstallationThread, DOWNLOADING_INSTALLER, DOWNLOADING_SCRIPT,
    INSTALLING, FINISHED)
from spyder.plugins.completion.kite.utils.status import (
    check_if_kite_installed, check_if_kite_running)

# Time to wait until the installation finishes
# (6 minutes in milliseconds)
INSTALL_TIMEOUT = 360000


@pytest.mark.slow
@pytest.mark.skipif((not sys.platform.startswith('linux')
                     or os.environ.get('CI', None) is None),
                    reason=("Only works reliably on Linux and "
                            "it's not meant to be run outside of CIs"))
def test_kite_install(qtbot):
    """Test the correct execution of the installation process of kite."""
    install_manager = KiteInstallationThread(None)
    installation_statuses = []

    def installation_status(status):
        installation_statuses.append(status)

    def error_msg(error):
        # Should not enter here
        assert False

    def download_progress(progress, total):
        assert total != 0

    def finished():
        if sys.platform.startswith("linux"):
            expected_installation_status = [
                DOWNLOADING_SCRIPT,
                DOWNLOADING_INSTALLER,
                INSTALLING,
                FINISHED]
        else:
            expected_installation_status = [
                DOWNLOADING_INSTALLER,
                INSTALLING,
                FINISHED]

        # This status can be obtained the second time our tests are run
        if not installation_statuses == ['Installation finished']:
            assert installation_statuses == expected_installation_status

    install_manager.sig_installation_status.connect(installation_status)
    install_manager.sig_error_msg.connect(error_msg)
    install_manager.sig_download_progress.connect(download_progress)
    install_manager.finished.connect(finished)
    with qtbot.waitSignal(install_manager.finished, timeout=INSTALL_TIMEOUT):
        install_manager.install()

    assert check_if_kite_installed() and check_if_kite_running()


if __name__ == "__main__":
    pytest.main()
