# From https://github.com/untitaker/python-atomicwrites/blob/4183999d9b7e81af85dee070d5311299bdf5164c/tests/test_atomicwrites.py

import errno
import os

from spyder.utils.encoding import atomic_write

import pytest


def test_atomic_write(tmpdir):
    fname = tmpdir.join('ha')
    for i in range(2):
        with atomic_write(str(fname), overwrite=True, dir=tmpdir, mode='w') as f:
            f.write('hoho')

    with pytest.raises(OSError) as excinfo:
        with atomic_write(str(fname), overwrite=False, dir=tmpdir, mode='w') as f:
            f.write('haha')

    assert excinfo.value.errno == errno.EEXIST

    assert fname.read() == 'hoho'
    assert len(tmpdir.listdir()) == 1


def test_teardown(tmpdir):
    fname = tmpdir.join('ha')
    with pytest.raises(AssertionError):
        with atomic_write(str(fname), overwrite=True, dir=tmpdir, mode='w'):
            assert False

    assert not tmpdir.listdir()


def test_replace_simultaneously_created_file(tmpdir):
    fname = tmpdir.join('ha')
    with atomic_write(str(fname), overwrite=True, dir=tmpdir, mode='w') as f:
        f.write('hoho')
        fname.write('harhar')
        assert fname.read() == 'harhar'
    assert fname.read() == 'hoho'
    assert len(tmpdir.listdir()) == 1


def test_dont_remove_simultaneously_created_file(tmpdir):
    fname = tmpdir.join('ha')
    with pytest.raises(OSError) as excinfo:
        with atomic_write(str(fname), overwrite=False, dir=tmpdir, mode='w') as f:
            f.write('hoho')
            fname.write('harhar')
            assert fname.read() == 'harhar'

    assert excinfo.value.errno == errno.EEXIST
    assert fname.read() == 'harhar'
    assert len(tmpdir.listdir()) == 1


# Verify that nested exceptions during rollback do not overwrite the initial
# exception that triggered a rollback.
def test_open_reraise(tmpdir):
    fname = tmpdir.join('ha')
    with pytest.raises(AssertionError):
        aw = atomic_write(str(fname), overwrite=False, dir=tmpdir, mode='w')
        with aw:
            # Mess with internals, so commit will trigger a ValueError. We're
            # testing that the initial AssertionError triggered below is
            # propagated up the stack, not the second exception triggered
            # during commit.
            aw.rollback = lambda: 1 / 0
            # Now trigger our own exception.
            assert False, "Intentional failure for testing purposes"


def test_atomic_write_in_pwd(tmpdir):
    orig_curdir = os.getcwd()
    try:
        os.chdir(str(tmpdir))
        fname = 'ha'
        for i in range(2):
            with atomic_write(str(fname), overwrite=True, dir=tmpdir, mode='w') as f:
                f.write('hoho')

        with pytest.raises(OSError) as excinfo:
            with atomic_write(str(fname), overwrite=False, dir=tmpdir, mode='w') as f:
                f.write('haha')

        assert excinfo.value.errno == errno.EEXIST

        assert open(fname).read() == 'hoho'
        assert len(tmpdir.listdir()) == 1
    finally:
        os.chdir(orig_curdir)
