# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Files and Remote client integration tests."""

# Third party imports
import pytest
from qtpy.QtWidgets import QDialog

# Local imports
from spyder.plugins.remoteclient.tests.conftest import (
    run_async,
    mark_remote_test,
)
from spyder.plugins.explorer.widgets.remote_dialog import RemoteFileDialog


@mark_remote_test
def test_remote_directory(
    remote_explorer, remote_client, remote_client_id, monkeypatch
):
    remote_files_manager = run_async(
        remote_client.get_file_api(remote_client_id)().connect
    ).result()
    expected_directory = "/home/ubuntu"

    monkeypatch.setattr(QDialog, "exec_", lambda *args: QDialog.Accepted)

    directory = RemoteFileDialog.get_remote_directory(
        "Test server",
        remote_client_id,
        remote_files_manager,
        expected_directory,
        parent=remote_explorer,
    )

    assert directory == expected_directory


if __name__ == "__main__":
    pytest.main()
