# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Run code in a console and collect its results, for the console's exposed
methods (e.g. used by AI agents).
"""

# Standard library imports
from __future__ import annotations

import ast
import base64
from concurrent.futures import Future
import inspect
import json
import logging
import re
import shlex
import textwrap
from typing import TYPE_CHECKING

# Third-party imports
from qtpy.QtCore import QObject, QTimer
from qtpy.QtGui import QTextCursor
from spyder_kernels.utils.nsview import REMOTE_SETTINGS

# Local imports
from spyder.api.plugins import ExposedCallError, Image, current_caller
from spyder.plugins.ipythonconsole.utils.scheduler import (
    describe_caller,
    get_scheduler,
)

if TYPE_CHECKING:
    from spyder.plugins.ipythonconsole.widgets import ShellWidget

logger = logging.getLogger(__name__)

# Default time to wait for code to finish running.
DEFAULT_EXECUTE_TIMEOUT = 60

# Maximum number of images returned by a single execution.
MAX_IMAGES = 8

# Maximum length of a variable's value preview.
MAX_VIEW_CHARS = 300

# Time to wait for the kernel to answer requests.
KERNEL_REPLY_TIMEOUT = 15

# Time to wait for the kernel of a new console to start.
NEW_CONSOLE_TIMEOUT = 120

IMAGE_TYPES = ["image/png", "image/jpeg", "image/svg+xml"]

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Names of variables and objects that can be inspected (e.g. ``df`` or
# ``np.linspace``)
DOTTED_NAME = re.compile(r"[A-Za-z_]\w*(\.[A-Za-z_]\w*)*")


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes, e.g. from tracebacks."""
    return ANSI_ESCAPE.sub("", text)


def get_console_id(client) -> str:
    """Id of a console, e.g. ``1/A``."""
    return f"{client.id_['int_id']}/{client.id_['str_id']}"


def get_console_state(shellwidget: ShellWidget) -> str:
    """State of a console: starting, debugging, busy or idle."""
    if not shellwidget.spyder_kernel_ready:
        return "starting"
    if shellwidget.is_debugging():
        return "debugging"
    if shellwidget._executing:
        return "busy"
    return "idle"


def check_ready(shellwidget: ShellWidget | None, console_id: str | None):
    """Raise an error if the console doesn't exist or isn't ready."""
    if shellwidget is None:
        if console_id is None:
            raise ExposedCallError("There are no IPython consoles open.")
        raise ExposedCallError(
            f"No console with id {console_id!r}. Use list_consoles to get "
            f"the available ids."
        )
    if not shellwidget.spyder_kernel_ready:
        raise ExposedCallError("The console's kernel is not ready yet.")


def check_idle(shellwidget: ShellWidget) -> None:
    """Raise an error if the console can't answer requests right now."""
    check_not_debugging(shellwidget)
    if shellwidget._executing:
        activity = get_scheduler(shellwidget).describe_activity()
        raise ExposedCallError(
            f"The console is busy ({activity or 'it is running code'}). "
            f"Wait for it to finish."
        )


def check_not_debugging(shellwidget: ShellWidget) -> None:
    """Raise an error if the console is debugging."""
    if not shellwidget.is_debugging():
        return

    scheduler = get_scheduler(shellwidget)
    if not scheduler.is_running_outside_code():
        raise ExposedCallError(
            "The console is in debugging mode. Wait for the user to finish "
            "debugging, or use debug_command if they asked you to help."
        )

    caller = scheduler.get_running_caller()
    if caller is not None and caller == current_caller():
        raise ExposedCallError(
            "The console is debugging your code. Use debug_command to "
            "continue (c) or stop debugging (q) first."
        )
    raise ExposedCallError(
        f"The console is in debugging mode: {describe_caller(caller)} is "
        f"debugging in it. Use another console (see list_consoles and "
        f"new_console)."
    )


def run_code(shellwidget: ShellWidget, code: str, timeout: float) -> Future:
    """
    Run code for the current caller when the console is free, and collect
    its results with an :class:`ExecutionCollector`.

    Parameters
    ----------
    timeout : float
        Seconds to wait for the console to be free and the code to finish.
    """
    check_not_debugging(shellwidget)
    return get_scheduler(shellwidget).submit(
        current_caller(),
        lambda remaining: ExecutionCollector(shellwidget, remaining).run(code),
        timeout,
    )


def keep_typed_text(shellwidget: ShellWidget, typed: str) -> None:
    """
    Show ``typed`` at the prompt again when the code that is starting
    finishes. Executing replaces the text the user has at the prompt.
    """
    if typed and shellwidget._executing:
        shellwidget.input_buffer = typed


def restore_typed_text(shellwidget: ShellWidget, typed: str) -> None:
    """
    Restore the text kept with :func:`keep_typed_text` if the console didn't
    when the code finished, which happens at Pdb prompts: qtconsole drops it
    because it still considers the console to be executing.
    """
    if (
        typed
        and not shellwidget._executing
        and not shellwidget._get_input_buffer(force=True)
    ):
        shellwidget._input_buffer_pending = ""
        shellwidget.input_buffer = typed


# ---- Code execution
# -----------------------------------------------------------------------------
class ExecutionCollector(QObject):
    """
    Run code in a console and collect its outputs from the kernel messages.

    The code is executed through the console widget, so the user sees it
    and its output as if they had typed it.

    The result is a dict with the ``output`` text (stdout, stderr, results
    and tracebacks), whether the code ``raised_exception``, the ``images``
    it displayed and ``notes`` about how the execution ended.
    """

    # Keep a reference to running collectors so they're not garbage collected
    _running: set[ExecutionCollector] = set()

    def __init__(self, shellwidget: ShellWidget, timeout: float) -> None:
        super().__init__(shellwidget)
        self.shellwidget = shellwidget
        self.future: Future = Future()
        self.msg_id = None
        self.text: list[str] = []
        self.images: list[Image] = []
        self.raised_exception = False
        self.notes: list[str] = []
        self._typed = ""

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(int(timeout * 1000))
        self._timer.timeout.connect(self._on_timeout)

    def run(self, code: str) -> Future:
        kernel_client = self.shellwidget.kernel_client
        kernel_client.iopub_channel.message_received.connect(self._on_iopub)
        kernel_client.stdin_channel.message_received.connect(self._on_stdin)
        self.shellwidget.sig_pdb_prompt_ready.connect(self._on_pdb_prompt)

        # The msg_id of the execute request is only stored by the widget, so
        # look for the new one after executing.
        requests = self.shellwidget._request_info["execute"]
        before = set(requests)

        self._typed = self.shellwidget._get_input_buffer(force=True)
        self.shellwidget.execute(code)
        new = set(requests) - before
        keep_typed_text(self.shellwidget, self._typed)

        if len(new) != 1:
            self._disconnect()
            raise ExposedCallError("The code could not be sent to the kernel.")

        self.msg_id = new.pop()
        self._running.add(self)
        self._timer.start()
        return self.future

    # ---- Message handling
    def _on_iopub(self, msg: dict) -> None:
        if msg.get("parent_header", {}).get("msg_id") != self.msg_id:
            return

        msg_type = msg["header"]["msg_type"]
        content = msg["content"]

        if msg_type == "stream":
            self.text.append(content["text"])
        elif msg_type == "execute_result":
            data = content.get("data", {})
            if not self._add_image(data) and "text/plain" in data:
                self.text.append(
                    f"Out[{content.get('execution_count')}]: "
                    f"{data['text/plain']}\n"
                )
        elif msg_type == "display_data":
            data = content.get("data", {})
            if not self._add_image(data) and "text/plain" in data:
                self.text.append(data["text/plain"] + "\n")
        elif msg_type == "error":
            self.raised_exception = True
            self.text.append(strip_ansi("\n".join(content["traceback"])))
        elif (
            msg_type == "status"
            and content.get("execution_state") == "idle"
        ):
            if self.shellwidget._executing:
                # Finish when the console is free again, so the next calls
                # don't find it busy
                self.shellwidget.sig_prompt_ready.connect(self._finish)
            else:
                self._finish()

    def _on_stdin(self, msg: dict) -> None:
        if msg.get("parent_header", {}).get("msg_id") != self.msg_id:
            return
        if msg["header"]["msg_type"] == "input_request":
            self.notes.append(
                "The code is waiting for user input in the console "
                f"(prompt: {msg['content'].get('prompt', '')!r}). Ask the "
                "user to answer it or use interrupt_console."
            )
            self._finish()

    def _on_pdb_prompt(self) -> None:
        # The code stopped in the debugger (e.g. at a breakpoint)
        fname, lineno = self.shellwidget.get_pdb_last_step()
        location = f" at {fname}, line {lineno}" if fname else ""
        self.notes.append(
            f"The code stopped in the debugger{location}. Use debug_command "
            f"to continue."
        )
        self._finish()

    def _add_image(self, data: dict) -> bool:
        if len(self.images) >= MAX_IMAGES:
            return False

        for mime_type in IMAGE_TYPES:
            if mime_type in data:
                image = data[mime_type]
                if mime_type == "image/svg+xml":
                    image = image.encode("utf-8")
                else:
                    image = base64.b64decode(image)
                self.images.append(Image(image, mime_type))
                return True

        return False

    def _on_timeout(self) -> None:
        self.notes.append(
            f"The code is still running after "
            f"{self._timer.interval() // 1000} seconds. Its remaining output "
            f"will only be shown in the console. Use interrupt_console to "
            f"stop it."
        )
        self._finish()

    # ---- Finishing
    def _finish(self) -> None:
        self._timer.stop()
        self._disconnect()
        self._running.discard(self)
        restore_typed_text(self.shellwidget, self._typed)

        if not self.future.done():
            self.future.set_result(
                {
                    "output": "".join(self.text),
                    "raised_exception": self.raised_exception,
                    "images": self.images,
                    "notes": self.notes,
                }
            )
        self.deleteLater()

    def _disconnect(self) -> None:
        for signal, slot in [
            (self.shellwidget.sig_pdb_prompt_ready, self._on_pdb_prompt),
            (self.shellwidget.sig_prompt_ready, self._finish),
        ]:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass

        kernel_client = self.shellwidget.kernel_client
        if kernel_client is None:
            return
        for channel, slot in [
            (kernel_client.iopub_channel, self._on_iopub),
            (kernel_client.stdin_channel, self._on_stdin),
        ]:
            try:
                channel.message_received.disconnect(slot)
            except (TypeError, RuntimeError):
                pass


# ---- Debugger commands
# -----------------------------------------------------------------------------
class PdbCommandCollector(QObject):
    """
    Run a Pdb command in a console that is debugging and collect its output.

    Part of Pdb's output (e.g. the values of expressions) doesn't come
    through the kernel messages, so the output is the text the command adds
    to the console, as the user sees it.
    """

    _running: set[PdbCommandCollector] = set()

    def __init__(self, shellwidget: ShellWidget, timeout: float) -> None:
        super().__init__(shellwidget)
        self.shellwidget = shellwidget
        self.future: Future = Future()
        self.notes: list[str] = []
        self._start = None
        self._typed = ""

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(int(timeout * 1000))
        self._timer.timeout.connect(self._on_timeout)

    def run(self, command: str) -> Future:
        # Where the command is typed, after the prompt
        self._start = self.shellwidget._prompt_pos

        self.shellwidget.sig_pdb_prompt_ready.connect(self._finish)
        self.shellwidget.sig_prompt_ready.connect(self._finish)
        self._running.add(self)
        self._timer.start()

        self._typed = self.shellwidget._get_input_buffer(force=True)
        self.shellwidget.pdb_execute_command(command)
        keep_typed_text(self.shellwidget, self._typed)
        return self.future

    def _on_timeout(self) -> None:
        self.notes.append(
            f"The command is still running after "
            f"{self._timer.interval() // 1000} seconds. Use interrupt_console "
            f"to stop it."
        )
        self._finish()

    def _finish(self) -> None:
        self._timer.stop()
        for signal in [
            self.shellwidget.sig_pdb_prompt_ready,
            self.shellwidget.sig_prompt_ready,
        ]:
            try:
                signal.disconnect(self._finish)
            except (TypeError, RuntimeError):
                pass
        self._running.discard(self)

        # Text added after the prompt where the command was typed, without
        # the command itself and the new prompt
        cursor = QTextCursor(self.shellwidget._control.document())
        cursor.setPosition(self._start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        lines = cursor.selection().toPlainText().split("\n")[1:]
        if lines and (
            self.shellwidget.is_waiting_pdb_input()
            or not self.shellwidget.is_debugging()
        ):
            lines = lines[:-1]

        restore_typed_text(self.shellwidget, self._typed)

        if not self.future.done():
            self.future.set_result(
                {
                    "output": "\n".join(lines).strip("\n"),
                    "debugging": self.shellwidget.is_debugging(),
                    "location": get_pdb_location(self.shellwidget),
                    "notes": self.notes,
                }
            )
        self.deleteLater()


def get_pdb_location(shellwidget: ShellWidget) -> dict | None:
    """Current location of the debugger, if the console is debugging."""
    if not shellwidget.is_debugging():
        return None
    fname, lineno = shellwidget.get_pdb_last_step()
    if not fname:
        return None
    return {"filename": fname, "line": lineno}


# ---- Silent evaluation
# -----------------------------------------------------------------------------
def evaluate_silently(
    shellwidget: ShellWidget,
    expression: str,
    timeout: float = KERNEL_REPLY_TIMEOUT,
) -> Future:
    """
    Evaluate an expression in the kernel without showing it in the console
    or adding it to the history.

    Returns
    -------
    Future
        Resolved with the ``repr`` of the result, or with an
        :class:`ExposedCallError` if the expression raised an exception.
    """
    future: Future = Future()
    kernel_client = shellwidget.kernel_client
    timer = QTimer(shellwidget)
    timer.setSingleShot(True)

    def finish(result=None, error=None):
        timer.stop()
        timer.deleteLater()
        try:
            kernel_client.shell_channel.message_received.disconnect(
                on_reply
            )
        except (TypeError, RuntimeError):
            pass
        if future.done():
            return
        if error is not None:
            future.set_exception(ExposedCallError(error))
        else:
            future.set_result(result)

    def on_reply(msg):
        if msg.get("parent_header", {}).get("msg_id") != msg_id:
            return
        content = msg["content"]
        value = content.get("user_expressions", {}).get("result")
        if content.get("status") != "ok" or value is None:
            finish(error="The kernel couldn't evaluate the request.")
        elif value.get("status") == "ok":
            finish(result=value["data"].get("text/plain", ""))
        else:
            finish(error=f"{value.get('ename')}: {value.get('evalue')}")

    timer.timeout.connect(
        lambda: finish(error="The kernel didn't answer in time.")
    )
    kernel_client.shell_channel.message_received.connect(on_reply)
    msg_id = kernel_client.execute(
        "",
        silent=True,
        store_history=False,
        user_expressions={"result": expression},
    )
    timer.start(int(timeout * 1000))
    return future


def call_kernel_helper(
    shellwidget: ShellWidget, helper, *arguments: str
) -> Future:
    """
    Call a function from :mod:`kernel_helpers` in the kernel and get the
    JSON it returns.

    Parameters
    ----------
    helper : Callable
        Function to call. Its source is sent to the kernel, so it must be
        self-contained.
    arguments : str
        Python expressions for its arguments, evaluated in the console's
        namespace.

    Returns
    -------
    Future
        Resolved with the data returned by the helper.
    """
    source = textwrap.dedent(inspect.getsource(helper))
    expression = (
        f"(lambda __ns: (exec({source!r}, __ns), "
        f"__ns[{helper.__name__!r}]({', '.join(arguments)}))[1])({{}})"
    )

    result: Future = Future()

    def on_done(future):
        try:
            text = future.result()
            data = json.loads(ast.literal_eval(text))
        except ExposedCallError as error:
            result.set_exception(error)
        except Exception as error:
            result.set_exception(
                ExposedCallError(f"Unexpected reply from the kernel: {error}")
            )
        else:
            result.set_result(data)

    evaluate_silently(shellwidget, expression).add_done_callback(on_done)
    return result


def build_run_line(
    shellwidget: ShellWidget,
    filename: str,
    args: str = "",
    wdir: str | None = None,
    method: str = "runfile",
) -> str:
    """
    Build the magic that runs (``runfile``) or debugs (``debugfile``) a file,
    as Spyder's Run plugin does.
    """
    if shellwidget.is_spyder_kernel:
        arguments = [filename]
        if args:
            arguments += ["--args", args]
        if wdir is None:
            if not shellwidget.is_external_kernel:
                # Run in the file's directory
                arguments.append("--wdir")
        else:
            arguments += ["--wdir", wdir]
        return f"%{method} " + shlex.join(arguments)

    # Kernels that are not Spyder's
    arguments = ["-d"] if method == "debugfile" else []
    return "%run " + shlex.join(arguments + [filename] + shlex.split(args))


def check_name(name: str) -> None:
    """Raise an error if ``name`` isn't a (dotted) Python name."""
    if not DOTTED_NAME.fullmatch(name):
        raise ExposedCallError(
            f"{name!r} is not a variable name. Use names like 'df' or "
            f"'np.linspace', or execute_code for other expressions."
        )


# ---- Variables
# -----------------------------------------------------------------------------
def request_variables(shellwidget: ShellWidget) -> Future:
    """
    Get the variables in the console's namespace.

    Returns
    -------
    Future
        Resolved with a list of dicts with the ``name``, ``type``, ``size``
        and a preview of the ``value`` of each variable.
    """
    future: Future = Future()

    # Fail if the kernel doesn't answer, instead of waiting forever
    timer = QTimer(shellwidget)
    timer.setSingleShot(True)

    def on_timeout():
        if not future.done():
            future.set_exception(
                ExposedCallError("The kernel didn't answer in time.")
            )

    timer.timeout.connect(on_timeout)
    timer.start(KERNEL_REPLY_TIMEOUT * 1000)

    def on_namespace_view(view):
        timer.stop()
        timer.deleteLater()
        if future.done():
            return

        variables = []
        for name, props in (view or {}).items():
            value = props.get("view", "")
            if len(value) > MAX_VIEW_CHARS:
                value = value[:MAX_VIEW_CHARS] + "..."
            variables.append(
                {
                    "name": name,
                    "type": props.get("type"),
                    "size": props.get("size"),
                    "value": value,
                }
            )
        future.set_result(variables)

    # The kernel only computes the namespace view after the Variable Explorer
    # sends its settings, so send them if it hasn't (e.g. when it's disabled).
    if "namespace_view_settings" not in shellwidget._kernel_configuration:
        shellwidget.set_kernel_configuration(
            "namespace_view_settings",
            {
                name: shellwidget.get_conf(name, section="variable_explorer")
                for name in REMOTE_SETTINGS
            },
        )

    shellwidget.call_kernel(callback=on_namespace_view).get_namespace_view()
    return future
