# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Class to control a file where stanbdard output can be written.
"""

# Standard library imports.
import codecs
import os
import os.path as osp

# Local imports
from spyder.py3compat import to_text_string
from spyder.utils.encoding import get_coding
from spyder.utils.programs import get_temp_dir


def std_filename(connection_file, extension, std_dir=None):
    """Filename to save kernel output."""
    json_file = osp.basename(connection_file)
    file = json_file.split('.json')[0] + extension
    if std_dir is not None:
        file = osp.join(std_dir, file)
    else:
        try:
            file = osp.join(get_temp_dir(), file)
        except (IOError, OSError):
            file = None
    return file


class StdFile:
    def __init__(self, connection_file, extension=None, std_dir=None):
        if extension is None:
            self.filename = connection_file
        else:
            self.filename = std_filename(connection_file, extension, std_dir)
        self._mtime = 0
        self._cursor = 0
        self._handle = None

    @property
    def handle(self):
        """Get handle to file."""
        if self._handle is None and self.filename is not None:
            # Needed to prevent any error that could appear.
            # See spyder-ide/spyder#6267.
            try:
                self._handle = codecs.open(
                    self.filename, 'w', encoding='utf-8')
            except Exception:
                pass
        return self._handle

    def remove(self):
        """Remove file associated with the client."""
        try:
            # Defer closing the handle until the client
            # is closed because jupyter_client needs it open
            # while it tries to restart the kernel
            if self._handle is not None:
                self._handle.close()
            os.remove(self.filename)
            self._handle = None
        except Exception:
            pass

    def get_contents(self):
        """Get the contents of the std kernel file."""
        try:
            with open(self.filename, 'rb') as f:
                # We need to read the file as bytes to be able to
                # detect its encoding with chardet
                text = f.read()

                # This is needed to avoid showing an empty error message
                # when the kernel takes too much time to start.
                # See spyder-ide/spyder#8581.
                if not text:
                    return ''

                # This is needed since the file could be encoded
                # in something different to utf-8.
                # See spyder-ide/spyder#4191.
                encoding = get_coding(text)
                text = to_text_string(text, encoding)
                return text
        except Exception:
            return None

    def poll_file_change(self):
        """Check if the std kernel file just changed."""
        if self._handle is not None and not self._handle.closed:
            self._handle.flush()
        try:
            mtime = os.stat(self.filename).st_mtime
        except Exception:
            return

        if mtime == self._mtime:
            return
        self._mtime = mtime
        text = self.get_contents()
        if text:
            ret_text = text[self._cursor:]
            self._cursor = len(text)
            return ret_text

    def copy(self):
        """Return a copy."""
        return StdFile(self.filename)
