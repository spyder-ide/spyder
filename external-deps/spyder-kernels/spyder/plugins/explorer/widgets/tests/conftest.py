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
from spyder.py3compat import to_text_string
from spyder.plugins.explorer.widgets.fileassociations import (
    FileAssociationsWidget)


@pytest.fixture(params=[
        ['script.py', 'dir1/dir2/dir3/dir4'],
        ['script.py', 'script1.py', 'testdir/dir1/script2.py'],
        ['subdir/innerdir/dir3/text.txt', 'dir1/dir2/dir3',
         'dir1/dir2/dir3/file.txt', 'dir1/dir2/dir3/dir4/python.py'],
    ]
)
def create_folders_files(tmpdir, request):
    """A project directory with dirs and files for testing."""
    project_dir = to_text_string(tmpdir.mkdir('project'))
    destination_dir = to_text_string(tmpdir.mkdir('destination'))
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
