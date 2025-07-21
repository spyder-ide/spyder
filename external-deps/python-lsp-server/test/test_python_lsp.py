import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time

import pytest
import websockets

NUM_CLIENTS = 2
NUM_REQUESTS = 5
TEST_PORT = 5102
HOST = "127.0.0.1"
MAX_STARTUP_SECONDS = 5.0
CHECK_INTERVAL = 0.1


@pytest.fixture(scope="module", autouse=True)
def ws_server_subprocess():
    cmd = [
        sys.executable,
        "-m",
        "pylsp.__main__",
        "--ws",
        "--host",
        HOST,
        "--port",
        str(TEST_PORT),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )

    deadline = time.time() + MAX_STARTUP_SECONDS
    while True:
        try:
            with socket.create_connection(
                ("127.0.0.1", TEST_PORT), timeout=CHECK_INTERVAL
            ):
                break
        except (ConnectionRefusedError, OSError):
            if time.time() > deadline:
                proc.kill()
                out, err = proc.communicate(timeout=1)
                raise RuntimeError(
                    f"Server didn’t start listening on port {TEST_PORT} in time.\n"
                    f"STDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}"
                )
            time.sleep(CHECK_INTERVAL)

    yield  # run the tests

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()


TEST_DOC = """\
def test():
    '''Test documentation'''
test()
"""


def test_concurrent_ws_requests():
    errors = set()
    lock = threading.Lock()

    def thread_target(i: int):
        async def do_initialize(idx):
            uri = f"ws://{HOST}:{TEST_PORT}"
            async with websockets.connect(uri) as ws:
                # send initialize
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 4 * idx,
                    "method": "initialize",
                    "params": {},
                }
                did_open_request = {
                    "jsonrpc": "2.0",
                    "id": 4 * (idx + 1),
                    "method": "textDocument/didOpen",
                    "params": {
                        "textDocument": {
                            "uri": "test.py",
                            "languageId": "python",
                            "version": 0,
                            "text": TEST_DOC,
                        }
                    },
                }

                async def send_request(request: dict):
                    await asyncio.wait_for(
                        ws.send(json.dumps(request, ensure_ascii=False)), timeout=5
                    )

                async def get_json_reply():
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    obj = json.loads(raw)
                    return obj

                try:
                    await send_request(init_request)
                    await get_json_reply()
                    await send_request(did_open_request)
                    await get_json_reply()
                    requests = []
                    for i in range(NUM_REQUESTS):
                        hover_request = {
                            "jsonrpc": "2.0",
                            "id": 4 * (idx + 2 + i),
                            "method": "textDocument/definition",
                            "params": {
                                "textDocument": {
                                    "uri": "test.py",
                                },
                                "position": {
                                    "line": 3,
                                    "character": 2,
                                },
                            },
                        }
                        requests.append(send_request(hover_request))
                    # send many requests in parallel
                    await asyncio.gather(*requests)
                    # collect replies
                    for i in range(NUM_REQUESTS):
                        hover = await get_json_reply()
                        assert hover
                except (json.JSONDecodeError, asyncio.TimeoutError) as e:
                    return e
                return None

        error = asyncio.run(do_initialize(i))
        with lock:
            errors.add(error)

    # launch threads
    threads = []
    for i in range(1, NUM_CLIENTS + 1):
        t = threading.Thread(target=thread_target, args=(i,))
        t.start()
        threads.append(t)

    # wait for them all
    for t in threads:
        t.join(timeout=50)
        assert not t.is_alive(), f"Worker thread {t} hung!"

    assert not any(filter(bool, errors))
