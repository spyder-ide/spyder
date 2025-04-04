# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp.workspace import Document
from test.fixtures import DOC, DOC_URI


def test_document_props(doc) -> None:
    assert doc.uri == DOC_URI
    assert doc.source == DOC


def test_document_lines(doc) -> None:
    assert len(doc.lines) == 4
    assert doc.lines[0] == "import sys\n"


def test_document_source_unicode(workspace) -> None:
    document_mem = Document(DOC_URI, workspace, "my source")
    document_disk = Document(DOC_URI, workspace)
    assert isinstance(document_mem.source, type(document_disk.source))


def test_offset_at_position(doc) -> None:
    assert doc.offset_at_position({"line": 0, "character": 8}) == 8
    assert doc.offset_at_position({"line": 1, "character": 5}) == 16
    assert doc.offset_at_position({"line": 2, "character": 0}) == 12
    assert doc.offset_at_position({"line": 2, "character": 4}) == 16
    assert doc.offset_at_position({"line": 4, "character": 0}) == 51


def test_word_at_position(doc) -> None:
    """Return the position under the cursor (or last in line if past the end)"""
    # import sys
    assert doc.word_at_position({"line": 0, "character": 8}) == "sys"
    # Past end of import sys
    assert doc.word_at_position({"line": 0, "character": 1000}) == "sys"
    # Empty line
    assert doc.word_at_position({"line": 1, "character": 5}) == ""
    # def main():
    assert doc.word_at_position({"line": 2, "character": 0}) == "def"
    # Past end of file
    assert doc.word_at_position({"line": 4, "character": 0}) == ""


def test_document_empty_edit(workspace) -> None:
    doc = Document("file:///uri", workspace, "")
    doc.apply_change(
        {
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 0, "character": 0},
            },
            "text": "f",
        }
    )
    assert doc.source == "f"


def test_document_line_edit(workspace) -> None:
    doc = Document("file:///uri", workspace, "itshelloworld")
    doc.apply_change(
        {
            "text": "goodbye",
            "range": {
                "start": {"line": 0, "character": 3},
                "end": {"line": 0, "character": 8},
            },
        }
    )
    assert doc.source == "itsgoodbyeworld"


def test_document_multiline_edit(workspace) -> None:
    old = ["def hello(a, b):\n", "    print a\n", "    print b\n"]
    doc = Document("file:///uri", workspace, "".join(old))
    doc.apply_change(
        {
            "text": "print a, b",
            "range": {
                "start": {"line": 1, "character": 4},
                "end": {"line": 2, "character": 11},
            },
        }
    )
    assert doc.lines == ["def hello(a, b):\n", "    print a, b\n"]


def test_document_end_of_file_edit(workspace) -> None:
    old = ["print 'a'\n", "print 'b'\n"]
    doc = Document("file:///uri", workspace, "".join(old))
    doc.apply_change(
        {
            "text": "o",
            "range": {
                "start": {"line": 2, "character": 0},
                "end": {"line": 2, "character": 0},
            },
        }
    )
    assert doc.lines == [
        "print 'a'\n",
        "print 'b'\n",
        "o",
    ]
