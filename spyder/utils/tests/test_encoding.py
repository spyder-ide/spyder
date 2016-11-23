# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License

"""Tests for encodings.py"""

import pytest

from spyder.utils.encoding import is_text_file


def test_is_text_file(tmpdir):
    p = tmpdir.mkdir("sub").join("random_text.txt")
    p.write("Some random text")
    assert is_text_file(str(p)) == True


if __name__ == '__main__':
    pytest.main()
