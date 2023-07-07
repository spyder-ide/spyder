# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for encodings.py"""

import os
import pathlib
import stat

from flaky import flaky
import pytest

from spyder.utils.encoding import is_text_file, get_coding, write
from spyder.py3compat import to_text_string

__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))


@pytest.mark.order(1)
def test_symlinks(tmpdir):
    """
    Check that modifying symlinks files changes source file and keeps symlinks.
    """
    base_dir = tmpdir.mkdir("symlinks")
    base_file = base_dir.join("symlinks_text.txt")
    base_file_path = to_text_string(base_file)

    # Write base file
    write("Some text for symlink", base_file_path)

    # Create symlink
    symlink_file = pathlib.Path(base_dir.join(
        'link-to-symlinks_text.txt'))
    symlink_file.symlink_to(base_file_path)
    symlink_file_path = to_text_string(symlink_file)

    # Assert the symlink was created
    assert os.path.islink(symlink_file_path)

    # Write using the symlink
    encoding = write("New text for symlink", symlink_file_path)

    # Assert symlink is valid and contents of the file
    assert os.path.islink(symlink_file_path)
    assert base_file.read_text(encoding) == symlink_file.read_text(encoding)
    assert symlink_file.read_text(encoding) == 'New text for symlink'


def test_permissions(tmpdir):
    """Check that file permissions are preserved."""
    p_file = tmpdir.mkdir("permissions").join("permissions_text.txt")
    p_file = to_text_string(p_file)

    # Write file and define execution permissions
    write("Some text", p_file)
    st = os.stat(p_file)
    mode = st.st_mode | stat.S_IEXEC
    os.chmod(p_file, mode)

    old_mode = os.stat(p_file).st_mode

    # Write the file and check permissions
    write("Some text and more", p_file)
    new_mode = os.stat(p_file).st_mode

    assert old_mode == new_mode


@flaky(max_runs=10)
def test_timestamp(tmpdir):
    """Check that the modification timestamp is preserved."""
    tmp_file = tmpdir.mkdir("timestamp").join('test_file.txt')
    tmp_file = to_text_string(tmp_file)

    # Write a file
    write("Test text", tmp_file)
    st = os.stat(tmp_file)
    actual_creation_time = st.st_atime

    # Write the file and check that creation time is preserved.
    write('New text', tmp_file)
    creation_time = os.stat(tmp_file).st_atime
    assert actual_creation_time == creation_time


def test_is_text_file(tmpdir):
    p = tmpdir.mkdir("sub").join("random_text.txt")
    p.write("Some random text")
    assert is_text_file(str(p)) == True


@pytest.mark.parametrize(
    'expected_encoding, text_file',
    [('utf-8', 'utf-8.txt'),
     ('windows-1252', 'windows-1252.txt'),
     ('ascii', 'ascii.txt'),
     ('Big5', 'Big5.txt'),
     ('KOI8-R', 'KOI8-R.txt'),
     ])
def test_files_encodings(expected_encoding, text_file):
    with open(os.path.join(__location__, text_file), 'rb') as f:
        text = f.read()
        assert get_coding(text).lower() == expected_encoding.lower()


if __name__ == '__main__':
    pytest.main()
