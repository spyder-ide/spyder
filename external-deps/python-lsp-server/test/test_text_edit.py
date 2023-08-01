# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from pylsp.text_edit import OverLappingTextEditException, apply_text_edits
from pylsp import uris

DOC_URI = uris.from_fs_path(__file__)


def test_apply_text_edits_insert(pylsp):
    pylsp.workspace.put_document(DOC_URI, '012345678901234567890123456789')
    test_doc = pylsp.workspace.get_document(DOC_URI)

    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 0
            },
            "end": {
                "line": 0,
                "character": 0
            }
        },
        "newText": "Hello"
    }]) == 'Hello012345678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 1
            },
            "end": {
                "line": 0,
                "character": 1
            }
        },
        "newText": "Hello"
    }]) == '0Hello12345678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 1
            },
            "end": {
                "line": 0,
                "character": 1
            }
        },
        "newText": "Hello"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 1
            },
            "end": {
                "line": 0,
                "character": 1
            }
        },
        "newText": "World"
    }]) == '0HelloWorld12345678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 2
            },
            "end": {
                "line": 0,
                "character": 2
            }
        },
        "newText": "One"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 1
            },
            "end": {
                "line": 0,
                "character": 1
            }
        },
        "newText": "Hello"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 1
            },
            "end": {
                "line": 0,
                "character": 1
            }
        },
        "newText": "World"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 2
            },
            "end": {
                "line": 0,
                "character": 2
            }
        },
        "newText": "Two"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 2
            },
            "end": {
                "line": 0,
                "character": 2
            }
        },
        "newText": "Three"
    }]) == '0HelloWorld1OneTwoThree2345678901234567890123456789'


def test_apply_text_edits_replace(pylsp):
    pylsp.workspace.put_document(DOC_URI, '012345678901234567890123456789')
    test_doc = pylsp.workspace.get_document(DOC_URI)

    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "Hello"
    }]) == '012Hello678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "Hello"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 6
            },
            "end": {
                "line": 0,
                "character": 9
            }
        },
        "newText": "World"
    }]) == '012HelloWorld901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "Hello"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 6
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "World"
    }]) == '012HelloWorld678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 6
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "World"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "Hello"
    }]) == '012HelloWorld678901234567890123456789'
    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 3
            }
        },
        "newText": "World"
    }, {
        "range": {
            "start": {
                "line": 0,
                "character": 3
            },
            "end": {
                "line": 0,
                "character": 6
            }
        },
        "newText": "Hello"
    }]) == '012WorldHello678901234567890123456789'


def test_apply_text_edits_overlap(pylsp):
    pylsp.workspace.put_document(DOC_URI, '012345678901234567890123456789')
    test_doc = pylsp.workspace.get_document(DOC_URI)

    did_throw = False
    try:
        apply_text_edits(test_doc, [{
            "range": {
                "start": {
                    "line": 0,
                    "character": 3
                },
                "end": {
                    "line": 0,
                    "character": 6
                }
            },
            "newText": "Hello"
        }, {
            "range": {
                "start": {
                    "line": 0,
                    "character": 3
                },
                "end": {
                    "line": 0,
                    "character": 3
                }
            },
            "newText": "World"
        }])
    except OverLappingTextEditException:
        did_throw = True

    assert did_throw

    did_throw = False

    try:
        apply_text_edits(test_doc, [{
            "range": {
                "start": {
                    "line": 0,
                    "character": 3
                },
                "end": {
                    "line": 0,
                    "character": 6
                }
            },
            "newText": "Hello"
        }, {
            "range": {
                "start": {
                    "line": 0,
                    "character": 4
                },
                "end": {
                    "line": 0,
                    "character": 4
                }
            },
            "newText": "World"
        }])
    except OverLappingTextEditException:
        did_throw = True

    assert did_throw


def test_apply_text_edits_multiline(pylsp):
    pylsp.workspace.put_document(DOC_URI, '0\n1\n2\n3\n4')
    test_doc = pylsp.workspace.get_document(DOC_URI)

    assert apply_text_edits(test_doc, [{
        "range": {
            "start": {
                "line": 2,
                "character": 0
            },
            "end": {
                "line": 3,
                "character": 0
            }
        },
        "newText": "Hello"
    }, {
        "range": {
            "start": {
                "line": 1,
                "character": 1
            },
            "end": {
                "line": 1,
                "character": 1
            }
        },
        "newText": "World"
    }]) == '0\n1World\nHello3\n4'
