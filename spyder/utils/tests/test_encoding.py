# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for encodings.py"""

import pytest
import os
import stat

from spyder.utils.encoding import is_text_file, get_coding, write
from spyder.py3compat import to_text_string

__location__ = os.path.realpath(os.path.join(os.getcwd(),
                                             os.path.dirname(__file__)))


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
