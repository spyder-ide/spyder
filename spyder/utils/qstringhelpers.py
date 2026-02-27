# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""QString compatibility."""


def qstring_length(text):
    """
    Tries to compute what the length of an utf16-encoded QString would be.
    """
    # `surrogatepass` is necessary to deal with unicode emojis that don't fit
    # in 16 bits.
    # See https://stackoverflow.com/a/54549874/438386.
    # Fixes spyder-ide/spyder#24713.
    utf16_text = text.encode('utf16', 'surrogatepass')
    length = len(utf16_text) // 2

    # Remove Byte order mark.
    # TODO: All unicode Non-characters should be removed
    if utf16_text[:2] in [b'\xff\xfe', b'\xff\xff', b'\xfe\xff']:
        length -= 1
    return length
