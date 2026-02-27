# Copyright 2017-2020 Palantir Technologies, Inc.
# Copyright 2021- Python Language Server Contributors.

import logging
import os
import socketserver
import sys
import threading
import uuid
from functools import partial
from typing import Any

try:
    import ujson as json
except Exception:
    import json

from pylsp_jsonrpc.dispatchers import MethodDispatcher
from pylsp_jsonrpc.endpoint import Endpoint
from pylsp_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import _utils, lsp, uris
from ._version import __version__
from .config import config
from .workspace import Cell, Document, Notebook, Workspace

log = logging.getLogger(__name__)


LINT_DEBOUNCE_S = 0.5  # 500 ms
PARENT_PROCESS_WATCH_INTERVAL = 10  # 10 s
MAX_WORKERS = 64
PYTHON_FILE_EXTENSIONS = (".py", ".pyi")
CONFIG_FILEs = ("pycodestyle.cfg", "setup.cfg", "tox.ini", ".flake8")


class _StreamHandlerWrapper(socketserver.StreamRequestHandler):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None

    def setup(self) -> None:
        super().setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self) -> None:
        try:
            self.delegate.start()
        except OSError as e:
            if os.name == "nt":
                # Catch and pass on ConnectionResetError when parent process
                # dies
                if isinstance(e, WindowsError) and e.winerror == 10054:
                    pass

        self.SHUTDOWN_CALL()


def start_tcp_lang_server(bind_addr, port, check_parent_process, handler_class) -> None:
    if not issubclass(handler_class, PythonLSPServer):
        raise ValueError("Handler class must be an instance of PythonLSPServer")

    def shutdown_server(check_parent_process, *args):
        if check_parent_process:
            log.debug("Shutting down server")
            # Shutdown call must be done on a thread, to prevent deadlocks
            stop_thread = threading.Thread(target=server.shutdown)
            stop_thread.start()

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + "Handler",
        (_StreamHandlerWrapper,),
        {
            # We need to wrap this in staticmethod due to the changes to
            # functools.partial in Python 3.14+
            "DELEGATE_CLASS": staticmethod(
                partial(handler_class, check_parent_process=check_parent_process)
            )
            if sys.version_info >= (3, 14)
            else partial(handler_class, check_parent_process=check_parent_process),
            "SHUTDOWN_CALL": partial(shutdown_server, check_parent_process),
        },
    )

    server = socketserver.TCPServer(
        (bind_addr, port), wrapper_class, bind_and_activate=False
    )
    server.allow_reuse_address = True

    try:
        server.server_bind()
        server.server_activate()
        log.info("Serving %s on (%s, %s)", handler_class.__name__, bind_addr, port)
        server.serve_forever()
    finally:
        log.info("Shutting down")
        server.server_close()


def start_io_lang_server(rfile, wfile, check_parent_process, handler_class) -> None:
    if not issubclass(handler_class, PythonLSPServer):
        raise ValueError("Handler class must be an instance of PythonLSPServer")
    log.info("Starting %s IO language server", handler_class.__name__)
    server = handler_class(rfile, wfile, check_parent_process)
    server.start()


def start_ws_lang_server(port, check_parent_process, handler_class) -> None:
    if not issubclass(handler_class, PythonLSPServer):
        raise ValueError("Handler class must be an instance of PythonLSPServer")

    # imports needed only for websockets based server
    try:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        import websockets
    except ImportError as e:
        raise ImportError(
            "websocket modules missing. Please run: pip install 'python-lsp-server[websockets]'"
        ) from e

    with ThreadPoolExecutor(max_workers=10) as tpool:
        send_queue = None
        loop = None

        async def pylsp_ws(websocket):
            log.debug("Creating LSP object")

            # creating a partial function and suppling the websocket connection
            response_handler = partial(send_message, websocket=websocket)

            # Not using default stream reader and writer.
            # Instead using a consumer based approach to handle processed requests
            pylsp_handler = handler_class(
                rx=None,
                tx=None,
                consumer=response_handler,
                check_parent_process=check_parent_process,
            )

            async for message in websocket:
                try:
                    log.debug("consuming payload and feeding it to LSP handler")
                    request = json.loads(message)
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(tpool, pylsp_handler.consume, request)
                except Exception as e:
                    log.exception("Failed to process request %s, %s", message, str(e))

        def send_message(message, websocket):
            """Handler to send responses of  processed requests to respective web socket clients"""
            try:
                payload = json.dumps(message, ensure_ascii=False)
                loop.call_soon_threadsafe(send_queue.put_nowait, (payload, websocket))
            except Exception as e:
                log.exception("Failed to write message %s, %s", message, str(e))

        async def run_server():
            nonlocal send_queue, loop
            send_queue = asyncio.Queue()
            loop = asyncio.get_running_loop()

            async with websockets.serve(pylsp_ws, port=port):
                while 1:
                    # Wait until payload is available for sending
                    payload, websocket = await send_queue.get()
                    await websocket.send(payload)

        asyncio.run(run_server())


class PythonLSPServer(MethodDispatcher):
    """Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md
    """

    def __init__(
        self, rx, tx, check_parent_process=False, consumer=None, *, endpoint_cls=None
    ) -> None:
        self.workspace = None
        self.config = None
        self.root_uri = None
        self.watching_thread = None
        self.workspaces = {}
        self.uri_workspace_mapper = {}

        self._check_parent_process = check_parent_process

        if rx is not None:
            self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        else:
            self._jsonrpc_stream_reader = None

        if tx is not None:
            self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        else:
            self._jsonrpc_stream_writer = None

        endpoint_cls = endpoint_cls or Endpoint

        # if consumer is None, it is assumed that the default streams-based approach is being used
        if consumer is None:
            self._endpoint = endpoint_cls(
                self, self._jsonrpc_stream_writer.write, max_workers=MAX_WORKERS
            )
        else:
            self._endpoint = endpoint_cls(self, consumer, max_workers=MAX_WORKERS)

        self._dispatchers = []
        self._shutdown = False

    def start(self) -> None:
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def consume(self, message) -> None:
        """Entry point for consumer based server. Alternative to stream listeners."""
        # assuming message will be JSON
        self._endpoint.consume(message)

    def __getitem__(self, item):
        """Override getitem to fallback through multiple dispatchers."""
        if self._shutdown and item != "exit":
            # exit is the only allowed method during shutdown
            log.debug("Ignoring non-exit method during shutdown: %s", item)
            item = "invalid_request_after_shutdown"

        try:
            return super().__getitem__(item)
        except KeyError:
            # Fallback through extra dispatchers
            for dispatcher in self._dispatchers:
                try:
                    return dispatcher[item]
                except KeyError:
                    continue

        raise KeyError()

    def m_shutdown(self, **_kwargs) -> None:
        for workspace in self.workspaces.values():
            workspace.close()
        self._hook("pylsp_shutdown")
        self._shutdown = True

    def m_invalid_request_after_shutdown(self, **_kwargs):
        return {
            "error": {
                "code": lsp.ErrorCodes.InvalidRequest,
                "message": "Requests after shutdown are not valid",
            }
        }

    def m_exit(self, **_kwargs) -> None:
        self._endpoint.shutdown()
        if self._jsonrpc_stream_reader is not None:
            self._jsonrpc_stream_reader.close()
        if self._jsonrpc_stream_writer is not None:
            self._jsonrpc_stream_writer.close()

    def _match_uri_to_workspace(self, uri):
        workspace_uri = _utils.match_uri_to_workspace(uri, self.workspaces)
        return self.workspaces.get(workspace_uri, self.workspace)

    def _hook(self, hook_name, doc_uri=None, **kwargs):
        """Calls hook_name and returns a list of results from all registered handlers"""
        workspace = self._match_uri_to_workspace(doc_uri)
        doc = workspace.get_document(doc_uri) if doc_uri else None
        hook_handlers = self.config.plugin_manager.subset_hook_caller(
            hook_name, self.config.disabled_plugins
        )
        return hook_handlers(
            config=self.config, workspace=workspace, document=doc, **kwargs
        )

    def capabilities(self):
        server_capabilities = {
            "codeActionProvider": True,
            "codeLensProvider": {
                "resolveProvider": False,  # We may need to make this configurable
            },
            "completionProvider": {
                "resolveProvider": True,  # We could know everything ahead of time, but this takes time to transfer
                "triggerCharacters": ["."],
            },
            "documentFormattingProvider": True,
            "documentHighlightProvider": True,
            "documentRangeFormattingProvider": True,
            "documentSymbolProvider": True,
            "definitionProvider": True,
            "typeDefinitionProvider": True,
            "executeCommandProvider": {
                "commands": flatten(self._hook("pylsp_commands"))
            },
            "hoverProvider": True,
            "referencesProvider": True,
            "renameProvider": True,
            "foldingRangeProvider": True,
            "signatureHelpProvider": {"triggerCharacters": ["(", ",", "="]},
            "textDocumentSync": {
                "change": lsp.TextDocumentSyncKind.INCREMENTAL,
                "save": {
                    "includeText": True,
                },
                "openClose": True,
            },
            "notebookDocumentSync": {
                "notebookSelector": [{"cells": [{"language": "python"}]}]
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
            "experimental": merge(self._hook("pylsp_experimental_capabilities")),
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_initialize(
        self,
        processId=None,
        rootUri=None,
        rootPath=None,
        initializationOptions=None,
        workspaceFolders=None,
        **_kwargs,
    ):
        log.debug(
            "Language server initialized with %s %s %s %s",
            processId,
            rootUri,
            rootPath,
            initializationOptions,
        )
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ""

        self.workspaces.pop(self.root_uri, None)
        self.root_uri = rootUri
        self.config = config.Config(
            rootUri,
            initializationOptions or {},
            processId,
            _kwargs.get("capabilities", {}),
        )
        self.workspace = Workspace(rootUri, self._endpoint, self.config)
        self.workspaces[rootUri] = self.workspace
        if workspaceFolders:
            for folder in workspaceFolders:
                uri = folder["uri"]
                if uri == rootUri:
                    # Already created
                    continue
                workspace_config = config.Config(
                    uri,
                    self.config._init_opts,
                    self.config._process_id,
                    self.config._capabilities,
                )
                workspace_config.update(self.config._settings)
                self.workspaces[uri] = Workspace(uri, self._endpoint, workspace_config)

        self._dispatchers = self._hook("pylsp_dispatchers")
        self._hook("pylsp_initialize")

        if (
            self._check_parent_process
            and processId is not None
            and self.watching_thread is None
        ):

            def watch_parent_process(pid):
                # exit when the given pid is not alive
                if not _utils.is_process_alive(pid):
                    log.info("parent process %s is not alive, exiting!", pid)
                    self.m_exit()
                else:
                    threading.Timer(
                        PARENT_PROCESS_WATCH_INTERVAL, watch_parent_process, args=[pid]
                    ).start()

            self.watching_thread = threading.Thread(
                target=watch_parent_process, args=(processId,)
            )
            self.watching_thread.daemon = True
            self.watching_thread.start()
        # Get our capabilities
        return {
            "capabilities": self.capabilities(),
            "serverInfo": {
                "name": "pylsp",
                "version": __version__,
            },
        }

    def m_initialized(self, **_kwargs) -> None:
        self._hook("pylsp_initialized")

    def code_actions(self, doc_uri: str, range: dict, context: dict):
        return flatten(
            self._hook("pylsp_code_actions", doc_uri, range=range, context=context)
        )

    def code_lens(self, doc_uri):
        return flatten(self._hook("pylsp_code_lens", doc_uri))

    def completions(self, doc_uri, position):
        workspace = self._match_uri_to_workspace(doc_uri)
        document = workspace.get_document(doc_uri)
        ignored_names = None
        if isinstance(document, Cell):
            # We need to get the ignored names from the whole notebook document
            notebook_document = workspace.get_maybe_document(document.notebook_uri)
            ignored_names = notebook_document.jedi_names(doc_uri)
        completions = self._hook(
            "pylsp_completions", doc_uri, position=position, ignored_names=ignored_names
        )
        return {"isIncomplete": False, "items": flatten(completions)}

    def completion_item_resolve(self, completion_item):
        doc_uri = completion_item.get("data", {}).get("doc_uri", None)
        return self._hook(
            "pylsp_completion_item_resolve", doc_uri, completion_item=completion_item
        )

    def definitions(self, doc_uri, position):
        return flatten(self._hook("pylsp_definitions", doc_uri, position=position))

    def type_definition(self, doc_uri, position):
        return self._hook("pylsp_type_definition", doc_uri, position=position)

    def document_symbols(self, doc_uri):
        return flatten(self._hook("pylsp_document_symbols", doc_uri))

    def document_did_save(self, doc_uri):
        return self._hook("pylsp_document_did_save", doc_uri)

    def execute_command(self, command, arguments):
        return self._hook("pylsp_execute_command", command=command, arguments=arguments)

    def format_document(self, doc_uri, options):
        return lambda: self._hook("pylsp_format_document", doc_uri, options=options)

    def format_range(self, doc_uri, range, options):
        return self._hook("pylsp_format_range", doc_uri, range=range, options=options)

    def highlight(self, doc_uri, position):
        return (
            flatten(self._hook("pylsp_document_highlight", doc_uri, position=position))
            or None
        )

    def hover(self, doc_uri, position):
        return self._hook("pylsp_hover", doc_uri, position=position) or {"contents": ""}

    @_utils.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved) -> None:
        # Since we're debounced, the document may no longer be open
        workspace = self._match_uri_to_workspace(doc_uri)
        document_object = workspace.documents.get(doc_uri, None)
        if isinstance(document_object, Document):
            self._lint_text_document(
                doc_uri, workspace, is_saved, document_object.version
            )
        elif isinstance(document_object, Notebook):
            self._lint_notebook_document(document_object, workspace)

    def _lint_text_document(
        self, doc_uri, workspace, is_saved, doc_version=None
    ) -> None:
        workspace.publish_diagnostics(
            doc_uri,
            flatten(self._hook("pylsp_lint", doc_uri, is_saved=is_saved)),
            doc_version,
        )

    def _lint_notebook_document(self, notebook_document, workspace) -> None:
        """
        Lint a notebook document.

        This is a bit more complicated than linting a text document, because we need to
        send the entire notebook document to the pylsp_lint hook, but we need to send
        the diagnostics back to the client on a per-cell basis.
        """

        # First, we create a temp TextDocument that represents the whole notebook
        # contents. We'll use this to send to the pylsp_lint hook.
        random_uri = str(uuid.uuid4())

        # cell_list helps us map the diagnostics back to the correct cell later.
        cell_list: list[dict[str, Any]] = []

        offset = 0
        total_source = ""
        for cell in notebook_document.cells:
            cell_uri = cell["document"]
            cell_document = workspace.get_cell_document(cell_uri)

            num_lines = cell_document.line_count

            data = {
                "uri": cell_uri,
                "line_start": offset,
                "line_end": offset + num_lines - 1,
                "source": cell_document.source,
            }

            cell_list.append(data)
            if offset == 0:
                total_source = cell_document.source
            else:
                total_source += "\n" + cell_document.source

            offset += num_lines

        workspace.put_document(random_uri, total_source)

        try:
            document_diagnostics = flatten(
                self._hook("pylsp_lint", random_uri, is_saved=True)
            )

            # Now we need to map the diagnostics back to the correct cell and publish them.
            # Note: this is O(n*m) in the number of cells and diagnostics, respectively.
            for cell in cell_list:
                cell_diagnostics = []
                for diagnostic in document_diagnostics:
                    start_line = diagnostic["range"]["start"]["line"]
                    end_line = diagnostic["range"]["end"]["line"]

                    if start_line > cell["line_end"] or end_line < cell["line_start"]:
                        continue
                    diagnostic["range"]["start"]["line"] = (
                        start_line - cell["line_start"]
                    )
                    diagnostic["range"]["end"]["line"] = end_line - cell["line_start"]
                    cell_diagnostics.append(diagnostic)

                workspace.publish_diagnostics(cell["uri"], cell_diagnostics)
        finally:
            workspace.rm_document(random_uri)

    def references(self, doc_uri, position, exclude_declaration):
        return flatten(
            self._hook(
                "pylsp_references",
                doc_uri,
                position=position,
                exclude_declaration=exclude_declaration,
            )
        )

    def rename(self, doc_uri, position, new_name):
        return self._hook("pylsp_rename", doc_uri, position=position, new_name=new_name)

    def signature_help(self, doc_uri, position):
        return self._hook("pylsp_signature_help", doc_uri, position=position)

    def folding(self, doc_uri):
        return flatten(self._hook("pylsp_folding_range", doc_uri))

    def m_completion_item__resolve(self, **completionItem):
        return self.completion_item_resolve(completionItem)

    def m_notebook_document__did_open(
        self, notebookDocument=None, cellTextDocuments=None, **_kwargs
    ) -> None:
        workspace = self._match_uri_to_workspace(notebookDocument["uri"])
        workspace.put_notebook_document(
            notebookDocument["uri"],
            notebookDocument["notebookType"],
            cells=notebookDocument["cells"],
            version=notebookDocument.get("version"),
            metadata=notebookDocument.get("metadata"),
        )
        for cell in cellTextDocuments or []:
            workspace.put_cell_document(
                cell["uri"],
                notebookDocument["uri"],
                cell["languageId"],
                cell["text"],
                version=cell.get("version"),
            )
        self.lint(notebookDocument["uri"], is_saved=True)

    def m_notebook_document__did_close(
        self, notebookDocument=None, cellTextDocuments=None, **_kwargs
    ) -> None:
        workspace = self._match_uri_to_workspace(notebookDocument["uri"])
        for cell in cellTextDocuments or []:
            workspace.publish_diagnostics(cell["uri"], [])
            workspace.rm_document(cell["uri"])
        workspace.rm_document(notebookDocument["uri"])

    def m_notebook_document__did_change(
        self, notebookDocument=None, change=None, **_kwargs
    ) -> None:
        """
        Changes to the notebook document.

        This could be one of the following:
        1. Notebook metadata changed
        2. Cell(s) added
        3. Cell(s) deleted
        4. Cell(s) data changed
            4.1 Cell metadata changed
            4.2 Cell source changed
        """
        workspace = self._match_uri_to_workspace(notebookDocument["uri"])

        if change.get("metadata"):
            # Case 1
            workspace.update_notebook_metadata(
                notebookDocument["uri"], change.get("metadata")
            )

        cells = change.get("cells")
        if cells:
            # Change to cells
            structure = cells.get("structure")
            if structure:
                # Case 2 or 3
                notebook_cell_array_change = structure["array"]
                start = notebook_cell_array_change["start"]
                cell_delete_count = notebook_cell_array_change["deleteCount"]
                if cell_delete_count == 0:
                    # Case 2
                    # Cell documents
                    for cell_document in structure["didOpen"]:
                        workspace.put_cell_document(
                            cell_document["uri"],
                            notebookDocument["uri"],
                            cell_document["languageId"],
                            cell_document["text"],
                            cell_document.get("version"),
                        )
                    # Cell metadata which is added to Notebook
                    workspace.add_notebook_cells(
                        notebookDocument["uri"],
                        notebook_cell_array_change["cells"],
                        start,
                    )
                else:
                    # Case 3
                    # Cell documents
                    for cell_document in structure["didClose"]:
                        workspace.rm_document(cell_document["uri"])
                        workspace.publish_diagnostics(cell_document["uri"], [])
                    # Cell metadata which is removed from Notebook
                    workspace.remove_notebook_cells(
                        notebookDocument["uri"], start, cell_delete_count
                    )

            data = cells.get("data")
            if data:
                # Case 4.1
                for cell in data:
                    # update NotebookDocument.cells properties
                    pass

            text_content = cells.get("textContent")
            if text_content:
                # Case 4.2
                for cell in text_content:
                    cell_uri = cell["document"]["uri"]
                    # Even though the protocol says that `changes` is an array, we assume that it's always a single
                    # element array that contains the last change to the cell source.
                    workspace.update_document(cell_uri, cell["changes"][0])
        self.lint(notebookDocument["uri"], is_saved=True)

    def m_text_document__did_close(self, textDocument=None, **_kwargs) -> None:
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        workspace.publish_diagnostics(textDocument["uri"], [])
        workspace.rm_document(textDocument["uri"])

    def m_text_document__did_open(self, textDocument=None, **_kwargs) -> None:
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        workspace.put_document(
            textDocument["uri"],
            textDocument["text"],
            version=textDocument.get("version"),
        )
        self._hook("pylsp_document_did_open", textDocument["uri"])
        self.lint(textDocument["uri"], is_saved=True)

    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ) -> None:
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        for change in contentChanges:
            workspace.update_document(
                textDocument["uri"], change, version=textDocument.get("version")
            )
        self.lint(textDocument["uri"], is_saved=False)

    def m_text_document__did_save(self, textDocument=None, **_kwargs) -> None:
        self.lint(textDocument["uri"], is_saved=True)
        self.document_did_save(textDocument["uri"])

    def m_text_document__code_action(
        self, textDocument=None, range=None, context=None, **_kwargs
    ):
        return self.code_actions(textDocument["uri"], range, context)

    def m_text_document__code_lens(self, textDocument=None, **_kwargs):
        return self.code_lens(textDocument["uri"])

    def _cell_document__completion(self, cellDocument, position=None, **_kwargs):
        workspace = self._match_uri_to_workspace(cellDocument.notebook_uri)
        notebookDocument = workspace.get_maybe_document(cellDocument.notebook_uri)
        if notebookDocument is None:
            raise ValueError("Invalid notebook document")

        cell_data = notebookDocument.cell_data()

        # Concatenate all cells to be a single temporary document
        total_source = "\n".join(data["source"] for data in cell_data.values())
        with workspace.temp_document(total_source) as temp_uri:
            # update position to be the position in the temp document
            if position is not None:
                position["line"] += cell_data[cellDocument.uri]["line_start"]

            completions = self.completions(temp_uri, position)

            # Translate temp_uri locations to cell document locations
            for item in completions.get("items", []):
                if item.get("data", {}).get("doc_uri") == temp_uri:
                    item["data"]["doc_uri"] = cellDocument.uri

            # Copy LAST_JEDI_COMPLETIONS to cell document so that completionItem/resolve will work
            tempDocument = workspace.get_document(temp_uri)
            cellDocument.shared_data["LAST_JEDI_COMPLETIONS"] = (
                tempDocument.shared_data.get("LAST_JEDI_COMPLETIONS", None)
            )

            return completions

    def m_text_document__completion(self, textDocument=None, position=None, **_kwargs):
        # textDocument here is just a dict with a uri
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        document = workspace.get_document(textDocument["uri"])
        if isinstance(document, Cell):
            return self._cell_document__completion(document, position, **_kwargs)
        return self.completions(textDocument["uri"], position)

    def _cell_document__definition(self, cellDocument, position=None, **_kwargs):
        workspace = self._match_uri_to_workspace(cellDocument.notebook_uri)
        notebookDocument = workspace.get_maybe_document(cellDocument.notebook_uri)
        if notebookDocument is None:
            raise ValueError("Invalid notebook document")

        cell_data = notebookDocument.cell_data()

        # Concatenate all cells to be a single temporary document
        total_source = "\n".join(data["source"] for data in cell_data.values())
        with workspace.temp_document(total_source) as temp_uri:
            # update position to be the position in the temp document
            if position is not None:
                position["line"] += cell_data[cellDocument.uri]["line_start"]

            definitions = self.definitions(temp_uri, position)

            # Translate temp_uri locations to cell document locations
            for definition in definitions:
                if definition["uri"] == temp_uri:
                    # Find the cell the start line is in and adjust the uri and line numbers
                    for cell_uri, data in cell_data.items():
                        if (
                            data["line_start"]
                            <= definition["range"]["start"]["line"]
                            <= data["line_end"]
                        ):
                            definition["uri"] = cell_uri
                            definition["range"]["start"]["line"] -= data["line_start"]
                            definition["range"]["end"]["line"] -= data["line_start"]
                            break

            return definitions

    def m_text_document__definition(self, textDocument=None, position=None, **_kwargs):
        # textDocument here is just a dict with a uri
        workspace = self._match_uri_to_workspace(textDocument["uri"])
        document = workspace.get_document(textDocument["uri"])
        if isinstance(document, Cell):
            return self._cell_document__definition(document, position, **_kwargs)
        return self.definitions(textDocument["uri"], position)

    def m_text_document__type_definition(
        self, textDocument=None, position=None, **_kwargs
    ):
        return self.type_definition(textDocument["uri"], position)

    def m_text_document__document_highlight(
        self, textDocument=None, position=None, **_kwargs
    ):
        return self.highlight(textDocument["uri"], position)

    def m_text_document__hover(self, textDocument=None, position=None, **_kwargs):
        return self.hover(textDocument["uri"], position)

    def m_text_document__document_symbol(self, textDocument=None, **_kwargs):
        return self.document_symbols(textDocument["uri"])

    def m_text_document__formatting(self, textDocument=None, options=None, **_kwargs):
        return self.format_document(textDocument["uri"], options)

    def m_text_document__rename(
        self, textDocument=None, position=None, newName=None, **_kwargs
    ):
        return self.rename(textDocument["uri"], position, newName)

    def m_text_document__folding_range(self, textDocument=None, **_kwargs):
        return self.folding(textDocument["uri"])

    def m_text_document__range_formatting(
        self, textDocument=None, range=None, options=None, **_kwargs
    ):
        return self.format_range(textDocument["uri"], range, options)

    def m_text_document__references(
        self, textDocument=None, position=None, context=None, **_kwargs
    ):
        exclude_declaration = not context["includeDeclaration"]
        return self.references(textDocument["uri"], position, exclude_declaration)

    def m_text_document__signature_help(
        self, textDocument=None, position=None, **_kwargs
    ):
        return self.signature_help(textDocument["uri"], position)

    def m_workspace__did_change_configuration(self, settings=None) -> None:
        if self.config is not None:
            self.config.update((settings or {}).get("pylsp", {}))
        for workspace in self.workspaces.values():
            workspace.update_config(settings)
            self._hook("pylsp_workspace_configuration_changed")
            for doc_uri in workspace.documents:
                self.lint(doc_uri, is_saved=False)

    def m_workspace__did_change_workspace_folders(self, event=None, **_kwargs):
        if event is None:
            return
        added = event.get("added", [])
        removed = event.get("removed", [])

        for removed_info in removed:
            if "uri" in removed_info:
                removed_uri = removed_info["uri"]
                self.workspaces.pop(removed_uri, None)

        for added_info in added:
            if "uri" in added_info:
                added_uri = added_info["uri"]
                workspace_config = config.Config(
                    added_uri,
                    self.config._init_opts,
                    self.config._process_id,
                    self.config._capabilities,
                )
                workspace_config.update(self.config._settings)
                self.workspaces[added_uri] = Workspace(
                    added_uri, self._endpoint, workspace_config
                )

        root_workspace_removed = any(
            removed_info["uri"] == self.root_uri for removed_info in removed
        )
        workspace_added = len(added) > 0 and "uri" in added[0]
        if root_workspace_removed and workspace_added:
            added_uri = added[0]["uri"]
            self.root_uri = added_uri
            new_root_workspace = self.workspaces[added_uri]
            self.config = new_root_workspace._config
            self.workspace = new_root_workspace
        elif root_workspace_removed:
            # NOTE: Removing the root workspace can only happen when the server
            # is closed, thus the else condition of this if can never happen.
            if self.workspaces:
                log.debug("Root workspace deleted!")
                available_workspaces = sorted(self.workspaces)
                first_workspace = available_workspaces[0]
                new_root_workspace = self.workspaces[first_workspace]
                self.root_uri = first_workspace
                self.config = new_root_workspace._config
                self.workspace = new_root_workspace

        # Migrate documents that are on the root workspace and have a better
        # match now
        doc_uris = list(self.workspace._docs.keys())
        for uri in doc_uris:
            doc = self.workspace._docs.pop(uri)
            new_workspace = self._match_uri_to_workspace(uri)
            new_workspace._docs[uri] = doc

    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        changed_py_files = set()
        config_changed = False
        for d in changes or []:
            if d["uri"].endswith(PYTHON_FILE_EXTENSIONS):
                changed_py_files.add(d["uri"])
            elif d["uri"].endswith(CONFIG_FILEs):
                config_changed = True

        if config_changed:
            self.config.settings.cache_clear()
        elif not changed_py_files:
            # Only externally changed python files and lint configs may result in changed diagnostics.
            return

        for workspace in self.workspaces.values():
            for doc_uri in workspace.documents:
                # Changes in doc_uri are already handled by m_text_document__did_save
                if doc_uri not in changed_py_files:
                    self.lint(doc_uri, is_saved=False)

    def m_workspace__execute_command(self, command=None, arguments=None):
        return self.execute_command(command, arguments)


def flatten(list_of_lists):
    return [item for lst in list_of_lists for item in lst]


def merge(list_of_dicts):
    return {k: v for dictionary in list_of_dicts for k, v in dictionary.items()}
