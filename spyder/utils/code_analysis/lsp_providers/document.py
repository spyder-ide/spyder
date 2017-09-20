# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Language Server Protocol Client document handler routines."""

import os.path as osp

from spyder.py3compat import PY2
from spyder.utils.code_analysis import LSPRequestTypes
from spyder.utils.code_analysis.decorators import handles, send_request

if PY2:
    import pathlib2 as pathlib
else:
    import pathlib


def path_as_uri(path):
    return pathlib.Path(osp.abspath(path)).as_uri()


class DocumentProvider:
    def register_file(self, filename, signal):
        filename = path_as_uri(filename)
        if filename not in self.watched_files:
            self.watched_files[filename] = []
        self.watched_files[filename].append(signal)

    @handles(LSPRequestTypes.DOCUMENT_PUBLISH_DIAGNOSTICS)
    def process_document_diagnostics(self, response):
        print(response)

    @send_request(method=LSPRequestTypes.DOCUMENT_DID_OPEN)
    def document_open(self, editor_params):
        params = {
            'textDocument': {
                'uri': path_as_uri(editor_params['file']),
                'languageId': editor_params['language'],
                'version': editor_params['version'],
                'text': editor_params['text']
            }
        }

        return params
