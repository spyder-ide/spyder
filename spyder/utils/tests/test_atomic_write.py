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


def test_tempfile_is_created_next_to_dest(tmp_path):
    """
    When no directory is given, the temporary file must be created in the
    destination's own directory.

    Creating it anywhere else (e.g. in the system temporary directory, which is
    what `tempfile.mkstemp(dir=None)` does) makes the final rename hand the
    destination the temporary file's permissions instead of the ones the
    destination inherits from the directory it lives in. On Windows that
    silently strips every inherited NTFS ACE from the saved file.

    See spyder-ide/spyder#26315.
    """
    dest_dir = tmp_path / 'dest'
    dest_dir.mkdir()
    fname = dest_dir / 'ha'

    with atomic_write(str(fname), overwrite=True, dir=None, mode='w') as f:
        f.write('hoho')

        # The temporary file is next to the destination, and only it is there
        # (the destination does not exist yet).
        entries = list(dest_dir.iterdir())
        assert len(entries) == 1
        assert entries[0] != fname
        assert entries[0].name.startswith('ha')

    assert fname.read_text() == 'hoho'
    assert len(list(dest_dir.iterdir())) == 1


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
