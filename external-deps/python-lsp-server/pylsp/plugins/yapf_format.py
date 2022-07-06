# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import os

from yapf.yapflib import file_resources
from yapf.yapflib.yapf_api import FormatCode

from pylsp import hookimpl
from pylsp._utils import get_eol_chars

log = logging.getLogger(__name__)


@hookimpl
def pylsp_format_document(document):
    return _format(document)


@hookimpl
def pylsp_format_range(document, range):  # pylint: disable=redefined-builtin
    # First we 'round' the range up/down to full lines only
    range['start']['character'] = 0
    range['end']['line'] += 1
    range['end']['character'] = 0

    # From Yapf docs:
    # lines: (list of tuples of integers) A list of tuples of lines, [start, end],
    #   that we want to format. The lines are 1-based indexed. It can be used by
    #   third-party code (e.g., IDEs) when reformatting a snippet of code rather
    #   than a whole file.

    # Add 1 for 1-indexing vs LSP's 0-indexing
    lines = [(range['start']['line'] + 1, range['end']['line'] + 1)]
    return _format(document, lines=lines)


def _format(document, lines=None):
    # Yapf doesn't work with CRLF/CR line endings, so we replace them by '\n'
    # and restore them below.
    replace_eols = False
    source = document.source
    eol_chars = get_eol_chars(source)
    if eol_chars in ['\r', '\r\n']:
        replace_eols = True
        source = source.replace(eol_chars, '\n')

    new_source, changed = FormatCode(
        source,
        lines=lines,
        filename=document.filename,
        style_config=file_resources.GetDefaultStyleForDir(
            os.path.dirname(document.path)
        )
    )

    if not changed:
        return []

    if replace_eols:
        new_source = new_source.replace('\n', eol_chars)

    # I'm too lazy at the moment to parse diffs into TextEdit items
    # So let's just return the entire file...
    return [{
        'range': {
            'start': {'line': 0, 'character': 0},
            # End char 0 of the line after our document
            'end': {'line': len(document.lines), 'character': 0}
        },
        'newText': new_source
    }]
