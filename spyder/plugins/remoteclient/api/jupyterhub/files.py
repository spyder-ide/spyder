import json
import requests
import base64
from websockets.sync.client import connect

from fsspec.utils import stringify_path
from fsspec.spec import AbstractBufferedFile, AbstractFileSystem


class RemoteBufferedFile(AbstractBufferedFile):
    """
    A buffered file-like object for reading/writing over the
    WebSocket protocol. Inherit from AbstractBufferedFile, which
    handles the high-level read/write logic, and only supply the
    low-level chunk ops:
      - _fetch_range()
      - _initiate_upload()
      - _upload_chunk()
      - _finalize_upload()
    """

    def _fetch_range(self, start, end, **kwargs):
        """
        Download and return [start:end] of the underlying file, as bytes.
        Open a sync WebSocket, send a read_block request, then gather.
        """
        length = end - start
        if length < 0:
            return b""

        # Connect to the server’s WebSocket
        with connect(self.fs.ws_url) as ws:
            # Send JSON request: method=read_block
            # Note: if offset or length is 0, the server should handle gracefully.
            msg = {
                "method": "read_block",
                "args": [self.path, start, length],
                "kwargs": {}  # e.g. delimiter, if needed
            }
            ws.send_or_raise(self.fs._encode_json(msg))

            # Now collect base64 chunks
            data = b""
            while True:
                resp_raw = ws.recv()
                resp = self._decode_json(resp_raw)

                if "error" in resp:
                    raise RuntimeError(f"Server error: {resp['error']}")
                msg_type = resp.get("type")

                if msg_type == "data":
                    chunk_b = base64.b64decode(resp["data"])
                    data += chunk_b
                elif msg_type == "eof":
                    break
                else:
                    raise ValueError(f"Unexpected message type: {msg_type}")
            return data

    def _initiate_upload(self):
        """
        Called once when opening in write mode before writing the first data.
        Open a new WebSocket, announce "write_file", and keep the socket open
        for streaming chunks. Store the socket in self._ws.
        """
        self._ws = connect(self.fs.ws_url)
        # Announce write_file
        msg = {
            "method": "write_file",
            "args": [self.path],
            "kwargs": {}
        }
        self._ws.send_or_raise(self.fs._encode_json(msg))

    def _upload_chunk(self, final=False):
        """
        Called when the buffer is flushed to the backend. Encode self.buffer and
        send it as {"type": "data", "data": <base64>}. If `final=True`, don't do
        anything special here; the final call is in _finalize_upload().
        """
        if not self.buffer:
            return
        chunk_b64 = base64.b64encode(self.buffer).decode()
        msg = {"type": "data", "data": chunk_b64}
        self._ws.send_or_raise(self._encode_json(msg))

    def _finalize_upload(self):
        """
        Called once after all writing is done. Send 'eof',
        then wait for "write_complete".
        """
        # Send 'eof'
        eof_msg = {"type": "eof"}
        self._ws.send_or_raise(self._encode_json(eof_msg))

        # Wait for server's final response
        while True:
            try:
                resp_raw = self._ws.recv()
            except:
                break  # socket closed?
            resp = self._decode_json(resp_raw)
            if "error" in resp:
                raise RuntimeError(f"Server error: {resp['error']}")
            if resp.get("type") == "write_complete":
                break

        # Close the socket
        self._ws.close()

    def close(self):
        """
        Overridden close to ensure final flush (if writing).
        """
        super().close()  # calls self.flush(force=True) -> calls _finalize_upload()
        # Additional logic if needed

    def _encode_json(data: dict) -> str:
        """
        Encode a JSON-serializable dict as a string.
        """
        return json.dumps(data)
    
    def _decode_json(data: str) -> dict:
        """
        Decode a JSON string to a dict.
        """
        return json.loads(data)

class RemoteFileSystem(AbstractFileSystem):
    """
    An example custom FileSystem that:
      - uses REST endpoints for all metadata operations
      - uses a WebSocket for chunked read/write
    """
    cachable = False

    def __init__(self, rest_url, ws_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rest_url = rest_url.rstrip("/")
        self.ws_url = ws_url

        # Typically you’d keep a session for performance
        self._session = requests.Session()

    # ----------------------------------------------------------------
    # Internally used helper for REST calls
    # ----------------------------------------------------------------
    def _rest_get(self, endpoint, params=None):
        url = f"{self.rest_url}/{endpoint}"
        r = self._session.get(url, params=params)
        r.raise_for_status()
        return r.json()

    def _rest_post(self, endpoint, params=None):
        url = f"{self.rest_url}/{endpoint}"
        r = self._session.post(url, params=params)
        r.raise_for_status()
        return r.json()

    def _rest_delete(self, endpoint, params=None):
        url = f"{self.rest_url}/{endpoint}"
        r = self._session.delete(url, params=params)
        r.raise_for_status()
        return r.json()

    # ----------------------------------------------------------------
    # fsspec-required API: metadata
    # ----------------------------------------------------------------
    def ls(self, path, detail=True, **kwargs):
        """List files at a path."""
        params = {"path": path, "detail": str(detail).lower()}
        out = self._rest_get("ls", params=params)
        return out

    def info(self, path, **kwargs):
        """Get info about a single file/directory."""
        params = {"path": path}
        out = self._rest_get("info", params=params)
        return out

    def isfile(self, path):
        params = {"path": path}
        out = self._rest_get("isfile", params=params)
        return out["isfile"]

    def isdir(self, path):
        params = {"path": path}
        out = self._rest_get("isdir", params=params)
        return out["isdir"]

    def exists(self, path):
        params = {"path": path}
        out = self._rest_get("exists", params=params)
        return out["exists"]

    def mkdir(self, path, create_parents=True, **kwargs):
        params = {
            "path": path,
            "create_parents": str(bool(create_parents)).lower(),
            "exist_ok": str(bool(kwargs.get("exist_ok", False))).lower()
        }
        out = self._rest_post("mkdir", params=params)
        return out

    def rmdir(self, path):
        params = {"path": path}
        out = self._rest_delete("rmdir", params=params)
        return out

    def rm_file(self, path, missing_ok=False):
        params = {"path": path, "missing_ok": str(bool(missing_ok)).lower()}
        out = self._rest_delete("file", params=params)
        return out

    def touch(self, path, truncate=True, **kwargs):
        params = {"path": path, "truncate": str(bool(truncate)).lower()}
        out = self._rest_post("touch", params=params)
        return out

    # ----------------------------------------------------------------
    # fsspec open/read/write
    # ----------------------------------------------------------------
    def _open(self, path, mode="rb", block_size=2**20, **kwargs):
        """
        Return a file-like object that handles reading/writing with WebSocket.

        Parameters
        ----------
        path : str
            Path to the file.
        mode : str
            File mode, e.g., 'rb', 'wb', 'ab', 'r+b', etc.
        block_size : int
            Chunk size for reading/writing. Default is 1MB.
        """
        return RemoteBufferedFile(
            fs=self,
            path=stringify_path(path),
            mode=mode,
            block_size=block_size,
            **kwargs
        )

    def cat_file(self, path, start=None, end=None, **kwargs):
        """
        Read entire file (or partial range) from WebSocket and return bytes.
        """
        # A straightforward approach: open in read mode, read the data
        with self._open(path, mode="rb") as f:
            if start:
                f.seek(start)
            length = None
            if end is not None and start is not None:
                length = end - start
            out = f.read(length)
        return out

    def pipe_file(self, path, data, **kwargs):
        """Write bytes to a file (full overwrite)."""
        with self._open(path, mode="wb") as f:
            f.write(data)
