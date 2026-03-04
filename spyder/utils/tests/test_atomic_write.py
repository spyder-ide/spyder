# Based on tests from https://github.com/untitaker/python-atomicwrites

import errno
import os

import pytest

from spyder.utils.encoding import atomic_write


def test_atomic_write(tmp_path):
    fname = tmp_path / 'ha'
    for i in range(2):
        with atomic_write(str(fname), overwrite=True, dir=tmp_path, mode='w') as f:
            f.write('hoho')

    with pytest.raises(OSError) as excinfo:
        with atomic_write(str(fname), overwrite=False, dir=tmp_path, mode='w') as f:
            f.write('haha')

    assert excinfo.value.errno == errno.EEXIST

    assert fname.read_text() == 'hoho'
    assert len(list(tmp_path.iterdir())) == 1


def test_teardown(tmp_path):
    fname = tmp_path / 'ha'
    with pytest.raises(AssertionError):
        with atomic_write(str(fname), overwrite=True, dir=tmp_path, mode='w'):
            assert False

    assert not list(tmp_path.iterdir())


def test_replace_simultaneously_created_file(tmp_path):
    fname = tmp_path / 'ha'
    with atomic_write(str(fname), overwrite=True, dir=tmp_path, mode='w') as f:
        f.write('hoho')
        fname.write_text('harhar')
        assert fname.read_text() == 'harhar'
    assert fname.read_text() == 'hoho'
    assert len(list(tmp_path.iterdir())) == 1


def test_dont_remove_simultaneously_created_file(tmp_path):
    fname = tmp_path / 'ha'
    with pytest.raises(OSError) as excinfo:
        with atomic_write(str(fname), overwrite=False, dir=tmp_path, mode='w') as f:
            f.write('hoho')
            fname.write_text('harhar')
            assert fname.read_text() == 'harhar'

    assert excinfo.value.errno == errno.EEXIST
    assert fname.read_text() == 'harhar'
    assert len(list(tmp_path.iterdir())) == 1


def test_open_reraise(tmp_path):
    """
    Verify that nested exceptions during rollback do not overwrite the initial
    exception that triggered a rollback.
    """
    fname = tmp_path / 'ha'
    with pytest.raises(AssertionError):
        aw = atomic_write(str(fname), overwrite=False, dir=tmp_path, mode='w')
        with aw:
            # Mess with internals, so commit will trigger a ValueError. We're
            # testing that the initial AssertionError triggered below is
            # propagated up the stack, not the second exception triggered
            # during commit.
            aw.rollback = lambda: 1 / 0
            # Now trigger our own exception.
            assert False, "Intentional failure for testing purposes"


def test_atomic_write_in_pwd(tmp_path):
    orig_curdir = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        fname = 'ha'
        for i in range(2):
            with atomic_write(str(fname), overwrite=True, dir=tmp_path, mode='w') as f:
                f.write('hoho')

        with pytest.raises(OSError) as excinfo:
            with atomic_write(str(fname), overwrite=False, dir=tmp_path, mode='w') as f:
                f.write('haha')

        assert excinfo.value.errno == errno.EEXIST

        assert open(fname).read() == 'hoho'
        assert len(list(tmp_path.iterdir())) == 1
    finally:
        os.chdir(orig_curdir)
