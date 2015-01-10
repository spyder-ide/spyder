# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Text encoding utilities, text file I/O

Functions 'get_coding', 'decode', 'encode' and 'to_unicode' come from Eric4
source code (Utilities/__init___.py) Copyright © 2003-2009 Detlev Offenbach
"""

import re
import os
import locale
import sys
from codecs import BOM_UTF8, BOM_UTF16, BOM_UTF32

# Local imports
from spyderlib.py3compat import (is_string, to_text_string, is_binary_string,
                                 is_unicode)


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
CODECS = ['utf-8', 'iso8859-1',  'iso8859-15', 'koi8-r',
          'koi8-u', 'iso8859-2', 'iso8859-3', 'iso8859-4', 'iso8859-5', 
          'iso8859-6', 'iso8859-7', 'iso8859-8', 'iso8859-9', 
          'iso8859-10', 'iso8859-13', 'iso8859-14', 'latin-1', 
          'utf-16']

def get_coding(text):
    """
    Function to get the coding of a text.
    @param text text to inspect (string)
    @return coding string
    """
    for line in text.splitlines()[:2]:
        result = CODING_RE.search(to_text_string(line))
        if result:
            return result.group(1)
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
    
    # Try saving as ASCII
    try:
        return text.encode('ascii'), 'ascii'
    except UnicodeError:
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
    Write 'text' to file ('filename') assuming 'encoding'
    Return (eventually new) encoding
    """
    text, encoding = encode(text, encoding)
    with open(filename, mode) as textfile:
        textfile.write(text)
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
    
    Adapted from: http://stackoverflow.com/a/3002505
    
    Original Authors: Trent Mick <TrentM@ActiveState.com>
                      Jorge Orpinel <jorge@orpinel.com>
    """
    try:
        open(filename)
    except Exception:
        return False
    with open(filename, 'rb') as fid:
        try:
            CHUNKSIZE = 1024
            chunk = fid.read(CHUNKSIZE)
            # check for a UTF BOM
            for bom in [BOM_UTF8, BOM_UTF16, BOM_UTF32]:
                if chunk.startswith(bom):
                    return True
            chunk = chunk.decode('utf-8')
            while 1:
                if '\0' in chunk: # found null byte
                    return False
                if len(chunk) < CHUNKSIZE:
                    break # done
                chunk = fid.read(CHUNKSIZE).decode('utf-8')
        except UnicodeDecodeError:
            return False
        except Exception:
            pass
    return True
