# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

from test import unix_only, windows_only
import pytest
from pylsp import uris


@unix_only
@pytest.mark.parametrize('uri,path', [
    ('file:///foo/bar#frag', '/foo/bar'),
    ('file:/foo/bar#frag', '/foo/bar'),
    ('file:/foo/space%20%3Fbar#frag', '/foo/space ?bar'),
])
def test_to_fs_path(uri, path):
    assert uris.to_fs_path(uri) == path


@windows_only
@pytest.mark.parametrize('uri,path', [
    ('file:///c:/far/boo', 'c:\\far\\boo'),
    ('file:///C:/far/boo', 'c:\\far\\boo'),
    ('file:///C:/far/space%20%3Fboo', 'c:\\far\\space ?boo'),
])
def test_win_to_fs_path(uri, path):
    assert uris.to_fs_path(uri) == path


@unix_only
@pytest.mark.parametrize('path,uri', [
    ('/foo/bar', 'file:///foo/bar'),
    ('/foo/space ?bar', 'file:///foo/space%20%3Fbar'),
])
def test_from_fs_path(path, uri):
    assert uris.from_fs_path(path) == uri


@windows_only
@pytest.mark.parametrize('path,uri', [
    ('c:\\far\\boo', 'file:///c:/far/boo'),
    ('C:\\far\\space ?boo', 'file:///c:/far/space%20%3Fboo')
])
def test_win_from_fs_path(path, uri):
    assert uris.from_fs_path(path) == uri


@pytest.mark.parametrize('uri,kwargs,new_uri', [
    ('file:///foo/bar', {'path': '/baz/boo'}, 'file:///baz/boo'),
    ('file:///D:/hello%20world.py', {'path': 'D:/hello universe.py'}, 'file:///d:/hello%20universe.py')
])
def test_uri_with(uri, kwargs, new_uri):
    assert uris.uri_with(uri, **kwargs) == new_uri
