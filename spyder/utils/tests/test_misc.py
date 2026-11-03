# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for misc.py
"""

# Standard library imports
import os

# Test library imports
import pytest
from qtpy.QtCore import QFile

# Local imports
from spyder.utils.misc import (
    get_common_path,
    move_file,
    move_to_trash,
    remove_file,
)


def test_get_common_path():
    """Test getting the common path."""
    if os.name == 'nt':
        assert get_common_path(['D:\\Python\\spyder-v21\\spyder\\widgets',
                                'D:\\Python\\spyder\\spyder\\utils',
                                'D:\\Python\\spyder\\spyder\\widgets',
                                'D:\\Python\\spyder-v21\\spyder\\utils',
                                ]) == 'D:\\Python'
    else:
        assert get_common_path(['/Python/spyder-v21/spyder.widgets',
                                '/Python/spyder/spyder.utils',
                                '/Python/spyder/spyder.widgets',
                                '/Python/spyder-v21/spyder.utils',
                                ]) == '/Python'


@pytest.mark.parametrize("trash_available", [True, False])
def test_move_file(tmp_path, monkeypatch, trash_available):
    """
    Test that moving files and folders doesn't leave the source behind.

    This is a regression test for spyder-ide/spyder#26432
    """
    if not trash_available:
        # Simulate a filesystem without a trash, like Windows network shares
        monkeypatch.setattr(
            QFile, "moveToTrash", lambda *args: (False, "")
        )

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # Move a Python file, which also removes its pyc file
    source = tmp_path / "script.py"
    source.write_text("print(1)")
    (tmp_path / "script.pyc").touch()
    move_file(str(source), str(dest_dir / "script.py"))
    assert not source.exists()
    assert not (tmp_path / "script.pyc").exists()
    assert (dest_dir / "script.py").read_text() == "print(1)"

    # Move a folder
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "file.txt").write_text("text")
    move_file(str(folder), str(dest_dir / "folder"))
    assert not folder.exists()
    assert (dest_dir / "folder" / "file.txt").read_text() == "text"


@pytest.mark.parametrize(
    "qt_result, expected",
    [
        ((True, "/trash/file.txt"), True),
        ((False, ""), False),
        (True, True),
        (False, False),
    ]
)
def test_move_to_trash_result(monkeypatch, qt_result, expected):
    """
    Test that move_to_trash handles the result of QFile.moveToTrash for
    different Qt bindings.

    This is a regression test for spyder-ide/spyder#26432
    """
    monkeypatch.setattr(QFile, "moveToTrash", lambda *args: qt_result)
    assert move_to_trash("file.txt") is expected


def test_remove_file(tmp_path, monkeypatch):
    """
    Test that remove_file reports when files can't be moved to the trash and
    that they can be removed permanently.

    This is a regression test for spyder-ide/spyder#26432
    """
    fname = tmp_path / "script.py"
    fname.write_text("print(1)")
    (tmp_path / "script.pyc").write_text("")

    # Simulate a filesystem without a trash, like Windows network shares
    monkeypatch.setattr(QFile, "moveToTrash", lambda *args: (False, ""))
    assert not remove_file(str(fname))
    assert fname.exists()
    assert (tmp_path / "script.pyc").exists()

    assert remove_file(str(fname), permanently=True)
    assert not fname.exists()
    assert not (tmp_path / "script.pyc").exists()


if __name__ == "__main__":
    pytest.main()
