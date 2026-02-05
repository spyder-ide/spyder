# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Fixture to create files folders.
"""

# Standard imports
import os
import os.path as osp
import sys

# Third party imports
import pytest

# Local imports
from spyder.api.plugins.tests import *  # noqa
from spyder.plugins.explorer.widgets.fileassociations import (
    FileAssociationsWidget
)
from spyder.plugins.explorer.plugin import Explorer
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.remoteclient.tests.conftest import await_future
from spyder.plugins.remoteclient.tests.fixtures import *  # noqa


@pytest.fixture(params=[
        ['script.py', 'dir1/dir2/dir3/dir4'],
        ['script.py', 'script1.py', 'testdir/dir1/script2.py'],
        ['subdir/innerdir/dir3/text.txt', 'dir1/dir2/dir3',
         'dir1/dir2/dir3/file.txt', 'dir1/dir2/dir3/dir4/python.py'],
    ]
)
def create_folders_files(tmpdir, request):
    """A project directory with dirs and files for testing."""
    project_dir = str(tmpdir.mkdir('project'))
    destination_dir = str(tmpdir.mkdir('destination'))
    top_folder = osp.join(project_dir, 'top_folder_in_proj')
    if not osp.exists(top_folder):
        os.mkdir(top_folder)
    list_paths = []
    for item in request.param:
        if osp.splitext(item)[1]:
            if osp.split(item)[0]:
                dirs, fname = osp.split(item)
                dirpath = osp.join(top_folder, dirs)
                if not osp.exists(dirpath):
                    os.makedirs(dirpath)
                    item_path = osp.join(dirpath, fname)
            else:
                item_path = osp.join(top_folder, item)
        else:
            dirpath = osp.join(top_folder, item)
            if not osp.exists(dirpath):
                os.makedirs(dirpath)
                item_path = dirpath
        if not osp.isdir(item_path):
            with open(item_path, 'w') as fh:
                fh.write("File Path:\n" + str(item_path).replace(os.sep, '/'))
        list_paths.append(item_path)
    return list_paths, project_dir, destination_dir, top_folder


@pytest.fixture
def file_assoc_widget(qtbot, tmp_path):
    widget = FileAssociationsWidget()
    qtbot.addWidget(widget)
    if os.name == 'nt':
        ext = '.exe'
        path_obj = tmp_path / ('app 2' + ext)
        path_obj.write_bytes(b'Binary file contents')
        fpath = str(path_obj)
    elif sys.platform == 'darwin':
        ext = '.app'
        path_obj = tmp_path / ('app 2' + ext)
        path_obj.mkdir()
        fpath = str(path_obj)
    else:
        ext = '.desktop'
        path_obj = tmp_path / ('app 2' + ext)
        path_obj.write_text(u'Text file contents')
        fpath = str(path_obj)

    data = {
        '*.csv':
            [
                ('App name 1', '/path/to/app 1' + ext),
                ('App name 2', fpath),
            ],
        '*.txt':
            [
                ('App name 2', fpath),
                ('App name 3', '/path/to/app 3' + ext),
            ],
    }
    widget.load_values(data)
    widget.show()
    widget.test_data = data
    return qtbot, widget


@pytest.fixture(scope="session")
def plugins_cls():
    yield [("remote_client", RemoteClient), ("explorer", Explorer)]


@pytest.fixture
def remote_explorer(explorer, remote_client, remote_client_id, qtbot):
    """Create a remote explorer widget."""
    # Wait until Spyder remote services is fully up
    await_future(
        remote_client.ensure_remote_server(remote_client_id),
        timeout=100,
    )

    # Move to remote home
    widget = explorer.get_widget()
    widget.chdir("/home/ubuntu", server_id=remote_client_id)

    # Wait until the remote explorer is populated
    qtbot.waitUntil(lambda: widget.remote_treewidget.model.rowCount() > 0)

    # Make the widget visible. This is useful to run one test at a time
    # locally, but fails on CIs.
    # widget.resize(640, 480)
    # explorer.main.resize(640, 480)
    # qtbot.addWidget(explorer.main)
    # explorer.main.show()

    yield widget

    # Close remote file API connection
    explorer.on_close()
