# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the Spyder Remote Client plugin."""

# Third party imports
import pytest
from flaky import flaky
from qtpy.QtWidgets import QMessageBox

# Local imports
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.remoteclient.tests.conftest import (
    await_future,
    run_async,
    mark_remote_test,
)


# =============================================================================
# ---- Tests
# =============================================================================
@mark_remote_test
class TestNewServer:
    """Test the installation of the Spyder Remote Client plugin."""

    @flaky(max_runs=3, min_passes=1)
    def test_installation(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test the installation of the Spyder Remote Client plugin."""
        await_future(
            remote_client.ensure_remote_server(remote_client_id),
            timeout=180,  # longer timeout for installation
        )

        jupyter_api = remote_client.get_jupyter_api(remote_client_id)

        await_future(run_async(jupyter_api.connect), timeout=5)

        assert (
            await_future(run_async(jupyter_api.list_kernels), timeout=10) == []
        )


@mark_remote_test
class TestVersionCheck:
    def test_wrong_version(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
        monkeypatch,
        qtbot,
    ):
        monkeypatch.setattr(
            "spyder.plugins.remoteclient.api.manager.SPYDER_REMOTE_MAX_VERSION",
            "0.0.1",
        )
        monkeypatch.setattr(
            "spyder.plugins.remoteclient.widgets.container.SPYDER_REMOTE_MAX_VERSION",
            "0.0.1",
        )

        def mock_critical(parent, title, text, buttons):
            assert "spyder-remote-services" in text
            assert "0.0.1" in text
            assert "is newer than" in text
            return QMessageBox.Ok

        monkeypatch.setattr(
            "spyder.plugins.remoteclient.widgets.container.QMessageBox.critical",
            mock_critical,
        )

        with qtbot.waitSignal(
            remote_client.sig_version_mismatch,
            timeout=180000,
        ):
            remote_client.start_remote_server(remote_client_id)


if __name__ == "__main__":
    pytest.main()
