# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Text encoding utilities, text file I/O

Functions 'get_coding', 'decode', 'encode' and 'to_unicode' come from Eric4
source code (Utilities/__init___.py) Copyright © 2003-2009 Detlev Offenbach
"""

# Standard library imports
from codecs import BOM_UTF8, BOM_UTF16, BOM_UTF32
import tempfile
import locale
import re
import os
import os.path as osp
import sys
import time
import errno

# Third-party imports
from chardet.universaldetector import UniversalDetector
from atomicwrites import atomic_write

# Local imports
from spyder.py3compat import (is_string, to_text_string, is_binary_string,
                              is_unicode, PY2)
from spyder.utils.external.binaryornot.check import is_binary

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


PREFERRED_ENCODING = locale.getpreferredencoding()

def transcode(text, input=PREFERRED_ENCODING, output=PREFERRED_ENCODING):
    """Transcode a text string"""
    try:
        return text.decode("cp437").encode("cp1252")
    except UnicodeError:
        try:
            return text.decode("cp437").encode(output)
        except UnicodeError:
            return text

#------------------------------------------------------------------------------
#  Functions for encoding and decoding bytes that come from
#  the *file system*.
#------------------------------------------------------------------------------

# The default encoding for file paths and environment variables should be set
# to match the default encoding that the OS is using.
def getfilesystemencoding():
    """
    Query the filesystem for the encoding used to encode filenames
    and environment variables.
    """
    encoding = sys.getfilesystemencoding()
    if encoding is None:
        # Must be Linux or Unix and nl_langinfo(CODESET) failed.
        encoding = PREFERRED_ENCODING
    return encoding

FS_ENCODING = getfilesystemencoding()

def to_unicode_from_fs(string):
    """
    Return a unicode version of string decoded using the file system encoding.
    """
    if not is_string(string): # string is a QString
        string = to_text_string(string.toUtf8(), 'utf-8')
    else:
        if is_binary_string(string):
            try:
                unic = string.decode(FS_ENCODING)
            except (UnicodeError, TypeError):
                pass
            else:
                return unic
    return string

def to_fs_from_unicode(unic):
    """
    Return a byte string version of unic encoded using the file
    system encoding.
    """
    if is_unicode(unic):
        try:
            string = unic.encode(FS_ENCODING)
        except (UnicodeError, TypeError):
            pass
        else:
            return string
    return unic

#------------------------------------------------------------------------------
#  Functions for encoding and decoding *text data* itself, usually originating
#  from or destined for the *contents* of a file.
#------------------------------------------------------------------------------

# Codecs for working with files and text.
CODING_RE = re.compile(r"coding[:=]\s*([-\w_.]+)")
CODECS = ['utf-8', 'iso8859-1',  'iso8859-15', 'ascii', 'koi8-r', 'cp1251',
          'koi8-u', 'iso8859-2', 'iso8859-3', 'iso8859-4', 'iso8859-5',
          'iso8859-6', 'iso8859-7', 'iso8859-8', 'iso8859-9',
          'iso8859-10', 'iso8859-13', 'iso8859-14', 'latin-1',
          'utf-16']


def get_coding(text, force_chardet=False):
    """
    Function to get the coding of a text.
    @param text text to inspect (string)
    @return coding string
    """
    if not force_chardet:
        for line in text.splitlines()[:2]:
            try:
                result = CODING_RE.search(to_text_string(line))
            except UnicodeDecodeError:
                # This could fail because to_text_string assume the text
                # is utf8-like and we don't know the encoding to give
                # it to to_text_string
                pass
            else:
                if result:
                    codec = result.group(1)
                    # sometimes we find a false encoding that can
                    # result in errors
                    if codec in CODECS:
                        return codec

    # Fallback using chardet
    if is_binary_string(text):
        detector = UniversalDetector()
        for line in text.splitlines()[:2]:
            detector.feed(line)
            if detector.done: break

        detector.close()
        return detector.result['encoding']

    return None

def decode(text):
    """
    Function to decode a text.
    @param text text to decode (string)
    @return decoded text and encoding
    """
    try:
        if text.startswith(BOM_UTF8):
            # UTF-8 with BOM
            return to_text_string(text[len(BOM_UTF8):], 'utf-8'), 'utf-8-bom'
        elif text.startswith(BOM_UTF16):
            # UTF-16 with BOM
            return to_text_string(text[len(BOM_UTF16):], 'utf-16'), 'utf-16'
        elif text.startswith(BOM_UTF32):
            # UTF-32 with BOM
            return to_text_string(text[len(BOM_UTF32):], 'utf-32'), 'utf-32'
        coding = get_coding(text)
        if coding:
            return to_text_string(text, coding), coding
    except (UnicodeError, LookupError):
        pass
    # Assume UTF-8
    try:
        return to_text_string(text, 'utf-8'), 'utf-8-guessed'
    except (UnicodeError, LookupError):
        pass
    # Assume Latin-1 (behaviour before 3.7.1)
    return to_text_string(text, "latin-1"), 'latin-1-guessed'

def encode(text, orig_coding):
    """
    Function to encode a text.
    @param text text to encode (string)
    @param orig_coding type of the original coding (string)
    @return encoded text and encoding
    """
    if orig_coding == 'utf-8-bom':
        return BOM_UTF8 + text.encode("utf-8"), 'utf-8-bom'

    # Try saving with original encoding
    if orig_coding:
        try:
            return text.encode(orig_coding), orig_coding
        except (UnicodeError, LookupError):
            pass

    # Try declared coding spec
    coding = get_coding(text)
    if coding:
        try:
            return text.encode(coding), coding
        except (UnicodeError, LookupError):
            raise RuntimeError("Incorrect encoding (%s)" % coding)
    if orig_coding and orig_coding.endswith('-default') or \
      orig_coding.endswith('-guessed'):
        coding = orig_coding.replace("-default", "")
        coding = orig_coding.replace("-guessed", "")
        try:
            return text.encode(coding), coding
        except (UnicodeError, LookupError):
            pass

    # Save as UTF-8 without BOM
    return text.encode('utf-8'), 'utf-8'

def to_unicode(string):
    """Convert a string to unicode"""
    if not is_unicode(string):
        for codec in CODECS:
            try:
                unic = to_text_string(string, codec)
            except UnicodeError:
                pass
            except TypeError:
                break
            else:
                return unic
    return string


def write(text, filename, encoding='utf-8', mode='wb'):
    """
    Write 'text' to file ('filename') assuming 'encoding' in an atomic way
    Return (eventually new) encoding
    """
    text, encoding = encode(text, encoding)

    if os.name == 'nt':
        try:
            absolute_path_filename = pathlib.Path(filename).resolve()
            if absolute_path_filename.exists():
                absolute_filename = to_text_string(absolute_path_filename)
            else:
                absolute_filename = osp.realpath(filename)
        except (OSError, RuntimeError):
            absolute_filename = osp.realpath(filename)
    else:
        absolute_filename = osp.realpath(filename)

    if 'a' in mode:
        with open(absolute_filename, mode) as textfile:
            textfile.write(text)
    else:
        # Based in the solution at untitaker/python-atomicwrites#42.
        # Needed to fix file permissions overwriting.
        # See spyder-ide/spyder#9381.
        try:
            file_stat = os.stat(absolute_filename)
            original_mode = file_stat.st_mode
            creation = file_stat.st_atime
        except OSError:  # Change to FileNotFoundError for PY3
            # Creating a new file, emulate what os.open() does
            umask = os.umask(0)
            os.umask(umask)
            # Set base permission of a file to standard permissions.
            # See #spyder-ide/spyder#14112.
            original_mode = 0o666 & ~umask
            creation = time.time()
        try:
            # fixes issues with scripts in Dropbox leaving
            # temporary files in the folder, see spyder-ide/spyder#13041
            tempfolder = None
            if 'dropbox' in absolute_filename.lower():
                tempfolder = tempfile.gettempdir()
            with atomic_write(absolute_filename, overwrite=True,
                              mode=mode, dir=tempfolder) as textfile:
                textfile.write(text)
        except OSError as error:
            # Some filesystems don't support the option to sync directories
            # See untitaker/python-atomicwrites#17
            if error.errno != errno.EINVAL:
                with open(absolute_filename, mode) as textfile:
                    textfile.write(text)
        try:
            os.chmod(absolute_filename, original_mode)
            file_stat = os.stat(absolute_filename)
            # Preserve creation timestamps
            os.utime(absolute_filename, (creation, file_stat.st_mtime))
        except OSError:
            # Prevent error when chmod/utime is not allowed
            # See spyder-ide/spyder#11308
            pass
    return encoding


def writelines(lines, filename, encoding='utf-8', mode='wb'):
    """
    Write 'lines' to file ('filename') assuming 'encoding'
    Return (eventually new) encoding
    """
    return write(os.linesep.join(lines), filename, encoding, mode)

def read(filename, encoding='utf-8'):
    """
    Read text from file ('filename')
    Return text and encoding
    """
    text, encoding = decode( open(filename, 'rb').read() )
    return text, encoding

def readlines(filename, encoding='utf-8'):
    """
    Read lines from file ('filename')
    Return lines and encoding
    """
    text, encoding = read(filename, encoding)
    return text.split(os.linesep), encoding


def is_text_file(filename):
    """
    Test if the given path is a text-like file.
    """
    try:
        return not is_binary(filename)
    except (OSError, IOError):
        return False
