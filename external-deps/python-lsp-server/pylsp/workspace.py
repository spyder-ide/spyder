# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import functools
import io
import logging
import os
import re
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from threading import RLock
from typing import Callable, Optional

import jedi

from . import _utils, lsp, uris

log = logging.getLogger(__name__)

DEFAULT_AUTO_IMPORT_MODULES = ["numpy"]

# TODO: this is not the best e.g. we capture numbers
RE_START_WORD = re.compile("[A-Za-z_0-9]*$")
RE_END_WORD = re.compile("^[A-Za-z_0-9]*")


def lock(method):
    """Define an atomic region over a method."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class Workspace:
    M_PUBLISH_DIAGNOSTICS = "textDocument/publishDiagnostics"
    M_PROGRESS = "$/progress"
    M_INITIALIZE_PROGRESS = "window/workDoneProgress/create"
    M_APPLY_EDIT = "workspace/applyEdit"
    M_SHOW_MESSAGE = "window/showMessage"
    M_LOG_MESSAGE = "window/logMessage"

    def __init__(self, root_uri, endpoint, config=None) -> None:
        self._config = config
        self._root_uri = root_uri
        self._endpoint = endpoint
        self._root_uri_scheme = uris.urlparse(self._root_uri)[0]
        self._root_path = uris.to_fs_path(self._root_uri)
        self._docs = {}

        # Cache jedi environments
        self._environments = {}

        # Whilst incubating, keep rope private
        self.__rope = None
        self.__rope_config = None
        self.__rope_autoimport = None

    def _rope_autoimport(
        self,
        rope_config: Optional,
        memory: bool = False,
    ):
        from rope.contrib.autoimport.sqlite import AutoImport

        if self.__rope_autoimport is None:
            project = self._rope_project_builder(rope_config)
            self.__rope_autoimport = AutoImport(project, memory=memory)
        return self.__rope_autoimport

    def _rope_project_builder(self, rope_config):
        from rope.base.project import Project

        # TODO: we could keep track of dirty files and validate only those
        if self.__rope is None or self.__rope_config != rope_config:
            rope_folder = rope_config.get("ropeFolder")
            if "ropeFolder" in rope_config:
                self.__rope = Project(self._root_path, ropefolder=rope_folder)
            else:
                self.__rope = Project(self._root_path)
            self.__rope.prefs.set(
                "extension_modules", rope_config.get("extensionModules", [])
            )
            self.__rope.prefs.set("ignore_syntax_errors", True)
            self.__rope.prefs.set("ignore_bad_imports", True)
        self.__rope.validate()
        return self.__rope

    @property
    def documents(self):
        return self._docs

    @property
    def root_path(self):
        return self._root_path

    @property
    def root_uri(self):
        return self._root_uri

    def is_local(self):
        return (self._root_uri_scheme in ["", "file"]) and os.path.exists(
            self._root_path
        )

    def get_document(self, doc_uri):
        """Return a managed document if-present, else create one pointing at disk.

        See https://github.com/Microsoft/language-server-protocol/issues/177
        """
        return self._docs.get(doc_uri) or self._create_document(doc_uri)

    def get_cell_document(self, doc_uri):
        return self._docs.get(doc_uri)

    def get_maybe_document(self, doc_uri):
        return self._docs.get(doc_uri)

    def put_document(self, doc_uri, source, version=None) -> None:
        self._docs[doc_uri] = self._create_document(
            doc_uri, source=source, version=version
        )

    def put_notebook_document(
        self, doc_uri, notebook_type, cells, version=None, metadata=None
    ) -> None:
        self._docs[doc_uri] = self._create_notebook_document(
            doc_uri, notebook_type, cells, version, metadata
        )

    @contextmanager
    def temp_document(self, source, path=None) -> None:
        if path is None:
            path = self.root_path
        uri = uris.from_fs_path(os.path.join(path, str(uuid.uuid4())))
        try:
            self.put_document(uri, source)
            yield uri
        finally:
            self.rm_document(uri)

    def add_notebook_cells(self, doc_uri, cells, start) -> None:
        self._docs[doc_uri].add_cells(cells, start)

    def remove_notebook_cells(self, doc_uri, start, delete_count) -> None:
        self._docs[doc_uri].remove_cells(start, delete_count)

    def update_notebook_metadata(self, doc_uri, metadata) -> None:
        self._docs[doc_uri].metadata = metadata

    def put_cell_document(
        self, doc_uri, notebook_uri, language_id, source, version=None
    ) -> None:
        self._docs[doc_uri] = self._create_cell_document(
            doc_uri, notebook_uri, language_id, source, version
        )

    def rm_document(self, doc_uri) -> None:
        self._docs.pop(doc_uri)

    def update_document(self, doc_uri, change, version=None) -> None:
        self._docs[doc_uri].apply_change(change)
        self._docs[doc_uri].version = version

    def update_config(self, settings):
        self._config.update((settings or {}).get("pylsp", {}))
        for doc_uri in self.documents:
            if isinstance(document := self.get_document(doc_uri), Notebook):
                # Notebook documents don't have a config. The config is
                # handled at the cell level.
                return
            document.update_config(settings)

    def apply_edit(self, edit):
        return self._endpoint.request(self.M_APPLY_EDIT, {"edit": edit})

    def publish_diagnostics(self, doc_uri, diagnostics, doc_version=None) -> None:
        params = {
            "uri": doc_uri,
            "diagnostics": diagnostics,
        }

        if doc_version:
            params["version"] = doc_version

        self._endpoint.notify(
            self.M_PUBLISH_DIAGNOSTICS,
            params=params,
        )

    @contextmanager
    def report_progress(
        self,
        title: str,
        message: Optional[str] = None,
        percentage: Optional[int] = None,
        skip_token_initialization: bool = False,
    ) -> Generator[Callable[[str, Optional[int]], None], None, None]:
        """
        Report progress to the editor / client.

        ``skip_token_initialization` is necessary due to some current
        limitations of our LSP implementation. When `report_progress`
        is used from a synchronous LSP handler, the token initialization
        will time out because we can't receive the response.

        Many editors will still correctly show the progress messages though, which
        is why we are giving progress users the option to skip the initialization
        of the progress token.
        """
        if self._config:
            client_supports_progress_reporting = self._config.capabilities.get(
                "window", {}
            ).get("workDoneProgress", False)
        else:
            client_supports_progress_reporting = False

        if client_supports_progress_reporting:
            token = self._progress_begin(
                title, message, percentage, skip_token_initialization
            )

            def progress_message(
                message: str, percentage: Optional[int] = None
            ) -> None:
                self._progress_report(token, message, percentage)

            try:
                yield progress_message
            finally:
                self._progress_end(token)

            return

        # FALLBACK:
        # If the client doesn't support progress reporting, we have a dummy method
        # for the caller to use.
        def dummy_progress_message(
            message: str, percentage: Optional[int] = None
        ) -> None:
            pass

        yield dummy_progress_message

    def _progress_begin(
        self,
        title: str,
        message: Optional[str] = None,
        percentage: Optional[int] = None,
        skip_token_initialization: bool = False,
    ) -> str:
        token = str(uuid.uuid4())

        if not skip_token_initialization:
            try:
                self._endpoint.request(
                    self.M_INITIALIZE_PROGRESS, {"token": token}
                ).result(timeout=1.0)
            except Exception:
                log.warning(
                    "There was an error while trying to initialize progress reporting."
                    "Likely progress reporting was used in a synchronous LSP handler, "
                    "which is not supported by progress reporting yet. "
                    "To prevent waiting for the timeout you can set "
                    "`skip_token_initialization=True`. "
                    "Not every editor will show progress then, but many will.",
                    exc_info=True,
                )

        value = {
            "kind": "begin",
            "title": title,
        }
        if message is not None:
            value["message"] = message
        if percentage is not None:
            value["percentage"] = percentage

        self._endpoint.notify(
            self.M_PROGRESS,
            params={
                "token": token,
                "value": value,
            },
        )
        return token

    def _progress_report(
        self,
        token: str,
        message: Optional[str] = None,
        percentage: Optional[int] = None,
    ) -> None:
        value = {
            "kind": "report",
        }
        if message:
            value["message"] = message
        if percentage:
            value["percentage"] = percentage

        self._endpoint.notify(
            self.M_PROGRESS,
            params={
                "token": token,
                "value": value,
            },
        )

    def _progress_end(self, token: str, message: Optional[str] = None) -> None:
        value = {
            "kind": "end",
        }
        if message:
            value["message"] = message

        self._endpoint.notify(
            self.M_PROGRESS,
            params={
                "token": token,
                "value": value,
            },
        )

    def log_message(self, message, msg_type=lsp.MessageType.Info):
        self._endpoint.notify(
            self.M_LOG_MESSAGE, params={"type": msg_type, "message": message}
        )

    def show_message(self, message, msg_type=lsp.MessageType.Info) -> None:
        self._endpoint.notify(
            self.M_SHOW_MESSAGE, params={"type": msg_type, "message": message}
        )

    def source_roots(self, document_path):
        """Return the source roots for the given document."""
        files = (
            _utils.find_parents(
                self._root_path, document_path, ["setup.py", "pyproject.toml"]
            )
            or []
        )
        return list({os.path.dirname(project_file) for project_file in files}) or [
            self._root_path
        ]

    def _create_document(self, doc_uri, source=None, version=None):
        path = uris.to_fs_path(doc_uri)
        return Document(
            doc_uri,
            self,
            source=source,
            version=version,
            extra_sys_path=self.source_roots(path),
            rope_project_builder=self._rope_project_builder,
        )

    def _create_notebook_document(
        self, doc_uri, notebook_type, cells, version=None, metadata=None
    ):
        return Notebook(
            doc_uri,
            notebook_type,
            self,
            cells=cells,
            version=version,
            metadata=metadata,
        )

    def _create_cell_document(
        self, doc_uri, notebook_uri, language_id, source=None, version=None
    ):
        # TODO: remove what is unnecessary here.
        path = uris.to_fs_path(doc_uri)
        return Cell(
            doc_uri,
            notebook_uri=notebook_uri,
            language_id=language_id,
            workspace=self,
            source=source,
            version=version,
            extra_sys_path=self.source_roots(path),
            rope_project_builder=self._rope_project_builder,
        )

    def close(self) -> None:
        if self.__rope_autoimport:
            self.__rope_autoimport.close()


class Document:
    def __init__(
        self,
        uri,
        workspace,
        source=None,
        version=None,
        local=True,
        extra_sys_path=None,
        rope_project_builder=None,
    ) -> None:
        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)
        self.dot_path = _utils.path_to_dot_name(self.path)
        self.filename = os.path.basename(self.path)
        self.shared_data = {}

        self._config = workspace._config
        self._workspace = workspace
        self._local = local
        self._source = source
        self._extra_sys_path = extra_sys_path or []
        self._rope_project_builder = rope_project_builder
        self._lock = RLock()

    def __str__(self):
        return str(self.uri)

    def _rope_resource(self, rope_config):
        from rope.base import libutils

        return libutils.path_to_resource(
            self._rope_project_builder(rope_config), self.path
        )

    @property
    @lock
    def lines(self):
        return self.source.splitlines(True)

    @property
    @lock
    def source(self):
        if self._source is None:
            with open(self.path, encoding="utf-8") as f:
                return f.read()
        return self._source

    def update_config(self, settings) -> None:
        self._config.update((settings or {}).get("pylsp", {}))

    @lock
    def apply_change(self, change):
        """Apply a change to the document."""
        text = change["text"]
        change_range = change.get("range")

        if not change_range:
            # The whole file has changed
            self._source = text
            return

        start_line = change_range["start"]["line"]
        start_col = change_range["start"]["character"]
        end_line = change_range["end"]["line"]
        end_col = change_range["end"]["character"]

        # Check for an edit occuring at the very end of the file
        lines = self.lines
        if start_line == len(lines):
            self._source = self.source + text
            return

        new = io.StringIO()

        # Iterate over the existing document until we hit the edit range,
        # at which point we write the new text, then loop until we hit
        # the end of the range and continue writing.
        for i, line in enumerate(lines):
            if i < start_line:
                new.write(line)
                continue

            if i > end_line:
                new.write(line)
                continue

            if i == start_line:
                new.write(line[:start_col])
                new.write(text)

            if i == end_line:
                new.write(line[end_col:])

        self._source = new.getvalue()

    def offset_at_position(self, position):
        """Return the byte-offset pointed at by the given position."""
        return position["character"] + len("".join(self.lines[: position["line"]]))

    def word_at_position(self, position):
        """Get the word under the cursor returning the start and end positions."""
        lines = self.lines
        if position["line"] >= len(lines):
            return ""

        line = lines[position["line"]]
        i = position["character"]
        # Split word in two
        start = line[:i]
        end = line[i:]

        # Take end of start and start of end to find word
        # These are guaranteed to match, even if they match the empty string
        m_start = RE_START_WORD.findall(start)
        m_end = RE_END_WORD.findall(end)

        return m_start[0] + m_end[-1]

    @lock
    def jedi_names(self, all_scopes=False, definitions=True, references=False):
        script = self.jedi_script()
        return script.get_names(
            all_scopes=all_scopes, definitions=definitions, references=references
        )

    @lock
    def jedi_script(self, position=None, use_document_path=False):
        extra_paths = []
        environment_path = None
        env_vars = None
        prioritize_extra_paths = False

        if self._config:
            jedi_settings = self._config.plugin_settings(
                "jedi", document_path=self.path
            )
            jedi.settings.auto_import_modules = jedi_settings.get(
                "auto_import_modules", DEFAULT_AUTO_IMPORT_MODULES
            )
            environment_path = jedi_settings.get("environment")
            # Jedi itself cannot deal with homedir-relative paths.
            # On systems, where it is expected, expand the home directory.
            if environment_path and os.name != "nt":
                environment_path = os.path.expanduser(environment_path)

            extra_paths = jedi_settings.get("extra_paths") or []
            env_vars = jedi_settings.get("env_vars")
            prioritize_extra_paths = jedi_settings.get("prioritize_extra_paths")

        # Drop PYTHONPATH from env_vars before creating the environment to
        # ensure that Jedi can startup properly without module name collision.
        if env_vars is None:
            env_vars = os.environ.copy()
        env_vars.pop("PYTHONPATH", None)

        environment = self.get_enviroment(environment_path, env_vars=env_vars)
        sys_path = self.sys_path(
            environment_path, env_vars, prioritize_extra_paths, extra_paths
        )

        project_path = self._workspace.root_path

        # Extend sys_path with document's path if requested
        if use_document_path:
            sys_path += [os.path.normpath(os.path.dirname(self.path))]

        kwargs = {
            "code": self.source,
            "path": self.path,
            "environment": environment if environment_path else None,
            "project": jedi.Project(path=project_path, sys_path=sys_path),
        }

        if position:
            # Deprecated by Jedi to use in Script() constructor
            kwargs += _utils.position_to_jedi_linecolumn(self, position)

        return jedi.Script(**kwargs)

    def get_enviroment(self, environment_path=None, env_vars=None):
        # TODO(gatesn): #339 - make better use of jedi environments, they seem pretty powerful
        if environment_path is None:
            environment = jedi.api.environment.get_cached_default_environment()
        else:
            if environment_path in self._workspace._environments:
                environment = self._workspace._environments[environment_path]
            else:
                environment = jedi.api.environment.create_environment(
                    path=environment_path, safe=False, env_vars=env_vars
                )
                self._workspace._environments[environment_path] = environment

        return environment

    def sys_path(
        self,
        environment_path=None,
        env_vars=None,
        prioritize_extra_paths=False,
        extra_paths=[],
    ):
        # Copy our extra sys path
        path = list(self._extra_sys_path)
        environment = self.get_enviroment(
            environment_path=environment_path, env_vars=env_vars
        )
        path.extend(environment.get_sys_path())
        if prioritize_extra_paths:
            path = extra_paths + path
        else:
            path = path + extra_paths

        return path


class Notebook:
    """Represents a notebook."""

    def __init__(
        self, uri, notebook_type, workspace, cells=None, version=None, metadata=None
    ) -> None:
        self.uri = uri
        self.notebook_type = notebook_type
        self.workspace = workspace
        self.version = version
        self.cells = cells or []
        self.metadata = metadata or {}
        self._lock = RLock()

    def __str__(self):
        return "Notebook with URI '%s'" % str(self.uri)

    def add_cells(self, new_cells: list, start: int) -> None:
        self.cells[start:start] = new_cells

    def remove_cells(self, start: int, delete_count: int) -> None:
        del self.cells[start : start + delete_count]

    def cell_data(self):
        """Extract current cell data.

        Returns a dict (ordered by cell position) where the key is the cell uri and the
        value is a dict with line_start, line_end, and source attributes.
        """
        cell_data = {}
        offset = 0
        for cell in self.cells:
            cell_uri = cell["document"]
            cell_document = self.workspace.get_cell_document(cell_uri)
            num_lines = cell_document.line_count
            cell_data[cell_uri] = {
                "line_start": offset,
                "line_end": offset + num_lines - 1,
                "source": cell_document.source,
            }
            offset += num_lines
        return cell_data

    @lock
    def jedi_names(
        self,
        up_to_cell_uri: Optional[str] = None,
        all_scopes=False,
        definitions=True,
        references=False,
    ):
        """
        Get the names in the notebook up to a certain cell.

        Parameters
        ----------
        up_to_cell_uri: str, optional
            The cell uri to stop at. If None, all cells are considered.
        """
        names = set()
        for cell in self.cells:
            cell_uri = cell["document"]
            cell_document = self.workspace.get_cell_document(cell_uri)
            names.update(cell_document.jedi_names(all_scopes, definitions, references))
            if cell_uri == up_to_cell_uri:
                break
        return {name.name for name in names}


class Cell(Document):
    """
    Represents a cell in a notebook.

    Notes
    -----
    We inherit from Document for now to get the same API. However, a cell document differs from text documents in that
    they have a language id.
    """

    def __init__(
        self,
        uri,
        notebook_uri,
        language_id,
        workspace,
        source=None,
        version=None,
        local=True,
        extra_sys_path=None,
        rope_project_builder=None,
    ) -> None:
        super().__init__(
            uri, workspace, source, version, local, extra_sys_path, rope_project_builder
        )
        self.language_id = language_id
        self.notebook_uri = notebook_uri

    @property
    @lock
    def line_count(self):
        """ "Return the number of lines in the cell document."""
        return len(self.source.split("\n"))
