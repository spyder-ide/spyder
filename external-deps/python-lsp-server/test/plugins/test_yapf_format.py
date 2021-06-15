# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp import uris
from pylsp.plugins.yapf_format import pylsp_format_document, pylsp_format_range
from pylsp.workspace import Document

DOC_URI = uris.from_fs_path(__file__)
DOC = """A = [
    'h',   'w',

    'a'
      ]

B = ['h',


'w']
"""

GOOD_DOC = """A = ['hello', 'world']\n"""


def test_format(workspace):
    doc = Document(DOC_URI, workspace, DOC)
    res = pylsp_format_document(doc)

    assert len(res) == 1
    assert res[0]['newText'] == "A = ['h', 'w', 'a']\n\nB = ['h', 'w']\n"


def test_range_format(workspace):
    doc = Document(DOC_URI, workspace, DOC)

    def_range = {
        'start': {'line': 0, 'character': 0},
        'end': {'line': 4, 'character': 10}
    }
    res = pylsp_format_range(doc, def_range)

    assert len(res) == 1

    # Make sure B is still badly formatted
    assert res[0]['newText'] == "A = ['h', 'w', 'a']\n\nB = ['h',\n\n\n'w']\n"


def test_no_change(workspace):
    doc = Document(DOC_URI, workspace, GOOD_DOC)
    assert not pylsp_format_document(doc)


def test_config_file(tmpdir, workspace):
    # a config file in the same directory as the source file will be used
    conf = tmpdir.join('.style.yapf')
    conf.write('[style]\ncolumn_limit = 14')
    src = tmpdir.join('test.py')
    doc = Document(uris.from_fs_path(src.strpath), workspace, DOC)

    # A was split on multiple lines because of column_limit from config file
    assert pylsp_format_document(doc)[0]['newText'] == "A = [\n    'h', 'w',\n    'a'\n]\n\nB = ['h', 'w']\n"
