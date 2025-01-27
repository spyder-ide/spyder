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
from spyder.plugins.remoteclient.tests.conftest import await_future


# =============================================================================
# ---- Tests
# =============================================================================
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
        assert (
            await_future(
                remote_client.get_kernels(remote_client_id),
                timeout=10,
            )
            == []
        )

    def test_start_kernel_running_server(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test starting a kernel on a remote server."""
        started_kernel_info = await_future(
            remote_client._start_new_kernel(remote_client_id),
        )

        current_kernel_info = await_future(
            remote_client._get_kernel_info(
                remote_client_id,
                started_kernel_info["id"],
            ),
        )

        started_kernel_info.pop("last_activity")
        current_kernel_info.pop("last_activity")

        assert started_kernel_info == current_kernel_info

    def test_shutdown_kernel(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test shutting down a kernel on a remote server."""
        kernel_info = await_future(
            remote_client.get_kernels(remote_client_id),
            timeout=10,
        )[0]

        await_future(
            remote_client._shutdown_kernel(
                remote_client_id,
                kernel_info["id"],
            ),
        )

        assert (
            await_future(
                remote_client.get_kernels(remote_client_id),
            )
            == []
        )


class TestNewKerneLAndServer:
    """Test the installation of the Spyder Remote Client plugin."""

    @flaky(max_runs=3, min_passes=1)
    def test_new_kernel(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test starting a kernel with no remote server installed."""
        started_kernel_info = await_future(
            remote_client._start_new_kernel(remote_client_id),
            timeout=180,
        )

        current_kernel_info = await_future(
            remote_client._get_kernel_info(
                remote_client_id,
                started_kernel_info["id"],
            ),
        )

        started_kernel_info.pop("last_activity")
        current_kernel_info.pop("last_activity")

        assert started_kernel_info == current_kernel_info

    def test_restart_kernel(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test restarting a kernel on a remote server."""
        kernel_info = await_future(
            remote_client.get_kernels(remote_client_id),
            timeout=10,
        )[0]

        assert await_future(
            remote_client._restart_kernel(
                remote_client_id,
                kernel_info["id"],
            ),
        )

        assert (
            await_future(
                remote_client._get_kernel_info(
                    remote_client_id,
                    kernel_info["id"],
                ),
            )
            != []
        )

    def test_restart_server(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test restarting a remote server."""
        await_future(
            remote_client.stop_remote_server(remote_client_id),
        )

        await_future(
            remote_client.start_remote_server(remote_client_id),
        )

        assert (
            await_future(
                remote_client.get_kernels(remote_client_id),
            )
            == []
        )


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
