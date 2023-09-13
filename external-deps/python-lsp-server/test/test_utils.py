# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import multiprocessing
import os
import sys
from threading import Thread
import time
from unittest import mock

from flaky import flaky

from pylsp import _utils
from pylsp.python_lsp import PythonLSPServer, start_io_lang_server


def start(obj):
    obj.start()


class ClientServerPair:
    """
    A class to setup a client/server pair.

    args:
        start_server_in_process: if True, the server will be started in a process.
        check_parent_process: if True, the server_process will check if the parent process is alive.
    """

    def __init__(self, start_server_in_process=False, check_parent_process=False):
        # Client to Server pipe
        csr, csw = os.pipe()
        # Server to client pipe
        scr, scw = os.pipe()

        if start_server_in_process:
            ParallelKind = self._get_parallel_kind()
            self.server_process = ParallelKind(
                target=start_io_lang_server,
                args=(
                    os.fdopen(csr, "rb"),
                    os.fdopen(scw, "wb"),
                    check_parent_process,
                    PythonLSPServer,
                ),
            )
            self.server_process.start()
        else:
            self.server = PythonLSPServer(os.fdopen(csr, "rb"), os.fdopen(scw, "wb"))
            self.server_thread = Thread(target=start, args=[self.server])
            self.server_thread.start()

        self.client = PythonLSPServer(os.fdopen(scr, "rb"), os.fdopen(csw, "wb"))
        self.client_thread = Thread(target=start, args=[self.client])
        self.client_thread.start()

    def _get_parallel_kind(self):
        if os.name == "nt":
            return Thread

        if sys.version_info[:2] >= (3, 8):
            return multiprocessing.get_context("fork").Process

        return multiprocessing.Process


@flaky(max_runs=6, min_passes=1)
def test_debounce():
    interval = 0.1
    obj = mock.Mock()

    @_utils.debounce(0.1)
    def call_m():
        obj()

    assert not obj.mock_calls

    call_m()
    call_m()
    call_m()
    assert not obj.mock_calls

    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 1

    call_m()
    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 2


@flaky(max_runs=6, min_passes=1)
def test_debounce_keyed_by():
    interval = 0.1
    obj = mock.Mock()

    @_utils.debounce(0.1, keyed_by="key")
    def call_m(key):
        obj(key)

    assert not obj.mock_calls

    call_m(1)
    call_m(2)
    call_m(3)
    assert not obj.mock_calls

    time.sleep(interval * 2)
    obj.assert_has_calls(
        [
            mock.call(1),
            mock.call(2),
            mock.call(3),
        ],
        any_order=True,
    )
    assert len(obj.mock_calls) == 3

    call_m(1)
    call_m(1)
    call_m(1)
    time.sleep(interval * 2)
    assert len(obj.mock_calls) == 4


def test_list_to_string():
    assert _utils.list_to_string("string") == "string"
    assert _utils.list_to_string(["a", "r", "r", "a", "y"]) == "a,r,r,a,y"


def test_find_parents(tmpdir):
    subsubdir = tmpdir.ensure_dir("subdir", "subsubdir")
    path = subsubdir.ensure("path.py")
    test_cfg = tmpdir.ensure("test.cfg")

    assert _utils.find_parents(tmpdir.strpath, path.strpath, ["test.cfg"]) == [
        test_cfg.strpath
    ]


def test_merge_dicts():
    assert _utils.merge_dicts(
        {"a": True, "b": {"x": 123, "y": {"hello": "world"}}},
        {"a": False, "b": {"y": [], "z": 987}},
    ) == {"a": False, "b": {"x": 123, "y": [], "z": 987}}


def test_clip_column():
    assert _utils.clip_column(0, [], 0) == 0
    assert _utils.clip_column(2, ["123"], 0) == 2
    assert _utils.clip_column(3, ["123"], 0) == 3
    assert _utils.clip_column(5, ["123"], 0) == 3
    assert _utils.clip_column(0, ["\n", "123"], 0) == 0
    assert _utils.clip_column(1, ["\n", "123"], 0) == 0
    assert _utils.clip_column(2, ["123\n", "123"], 0) == 2
    assert _utils.clip_column(3, ["123\n", "123"], 0) == 3
    assert _utils.clip_column(4, ["123\n", "123"], 1) == 3
