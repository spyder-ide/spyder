# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Tests for the exposed methods that need several plugins (Editor, Debugger,
IPython console), in a full Spyder window.
"""

# Standard library imports
from concurrent.futures import Future
import json
import os.path as osp

# Third-party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# Local imports
from spyder.api.plugins.exposed import CallContext, Caller, calling_as
from spyder.plugins.ipythonconsole.tests.conftest import SHELL_TIMEOUT
from spyder.plugins.mcpserver.api import ToolCall
from spyder.plugins.mcpserver.focus import call_tool_keeping_focus


@pytest.fixture
def tools(main_window, qtbot):
    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell._prompt_html is not None, timeout=SHELL_TIMEOUT
    )
    mcp_server = main_window.get_plugin("mcp_server")
    return {tool.name: tool for tool in mcp_server.get_tools()}


def call_tool(qtbot, tool, keep_focus=False, **arguments):
    """Call ``tool`` and wait for its result."""
    results = []

    def on_done(content, is_error):
        results.append((content, is_error))

    if keep_focus:
        # As agents call tools through the server
        call_tool_keeping_focus(tool, arguments, on_done)
    else:
        tool.call(ToolCall(arguments, on_done))
    qtbot.waitUntil(lambda: len(results) > 0, timeout=SHELL_TIMEOUT)

    # Let deferred focus changes happen
    qtbot.wait(200)
    return results[0]


def focus(qtbot, widget):
    """Give focus to ``widget`` like the user would."""
    widget.window().activateWindow()
    widget.setFocus()
    qtbot.waitUntil(lambda: QApplication.focusWidget() is widget)


def call_tool_json(qtbot, tool, keep_focus=False, **arguments):
    content, is_error = call_tool(qtbot, tool, keep_focus, **arguments)
    assert not is_error, content
    text = content[0]["text"]
    if text == "Done.":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Plain strings are sent as they are
        return text


def test_collected_tools(tools):
    """All the plugins' exposed methods are available to agents."""
    for name in [
        "execute_code",
        "edit_file",
        "get_figure",
        "set_breakpoint",
        "get_workdir",
    ]:
        assert name in tools


def test_edit_and_save_file(main_window, tools, qtbot, tmp_path):
    filename = str(tmp_path / "script.py")
    with open(filename, "w") as f:
        f.write("x = 1\nprint(x)\nprint(x)\n")

    # The file is opened and edited in the Editor, not on disk
    result = call_tool_json(
        qtbot,
        tools["edit_file"],
        filename=filename,
        old_text="x = 1",
        new_text="x = 2",
    )
    assert result["replacements"] == 1
    assert result["unsaved_changes"]

    editor = main_window.get_plugin("editor")
    codeeditor = editor.get_codeeditor_for_filename(filename)
    assert codeeditor.toPlainText().startswith("x = 2\n")
    with open(filename) as f:
        assert f.read().startswith("x = 1\n")

    # The change can be undone in a single step
    codeeditor.undo()
    assert codeeditor.toPlainText().startswith("x = 1\n")
    codeeditor.redo()

    # Ambiguous replacements are refused unless all are replaced
    content, is_error = call_tool(
        qtbot,
        tools["edit_file"],
        filename=filename,
        old_text="print(x)",
        new_text="print(x * 2)",
    )
    assert is_error
    assert "appears 2 times" in content[0]["text"]

    result = call_tool_json(
        qtbot,
        tools["edit_file"],
        filename=filename,
        old_text="print(x)",
        new_text="print(x * 2)",
        replace_all=True,
    )
    assert result["replacements"] == 2

    call_tool_json(qtbot, tools["save_file"], filename=filename)
    with open(filename) as f:
        assert f.read() == "x = 2\nprint(x * 2)\nprint(x * 2)\n"
    assert not codeeditor.document().isModified()

    # New files are created in the Editor but can't be saved without asking
    # the user where
    new_name = call_tool_json(
        qtbot, tools["new_editor_file"], text="answer = 42\n"
    )
    assert "untitled" in osp.basename(new_name)
    assert editor.get_current_editor().toPlainText() == "answer = 42\n"
    content, is_error = call_tool(qtbot, tools["save_file"], filename=new_name)
    assert is_error
    assert "never saved" in content[0]["text"]


def test_run_cell(main_window, tools, qtbot, tmp_path):
    filename = str(tmp_path / "cells.py")
    with open(filename, "w") as f:
        f.write("# %%\na = 10\n\n# %% Double\nprint(a * 2)\n")

    result = call_tool_json(
        qtbot, tools["run_cell"], filename=filename, cell=0
    )
    assert not result["raised_exception"]

    # Cells can also be run by name
    result = call_tool_json(
        qtbot, tools["run_cell"], filename=filename, cell="Double"
    )
    assert result["output"] == "20\n"


def test_debugging(main_window, tools, qtbot, tmp_path):
    filename = str(tmp_path / "debug_me.py")
    with open(filename, "w") as f:
        f.write(
            "def double(value):\n"
            "    result = value * 2\n"
            "    return result\n"
            "\n"
            "\n"
            "total = double(21)\n"
            "print(total)\n"
        )

    # Breakpoints can't be set on blank lines
    content, is_error = call_tool(
        qtbot, tools["set_breakpoint"], filename=filename, line=4
    )
    assert is_error

    call_tool_json(qtbot, tools["set_breakpoint"], filename=filename, line=3)
    breakpoints = call_tool_json(qtbot, tools["list_breakpoints"])
    assert {
        "filename": osp.normcase(filename),
        "line": 3,
        "condition": None,
    } in breakpoints

    # Debugging stops at the breakpoint
    result = call_tool_json(
        qtbot, tools["start_debugging"], filename=filename
    )
    assert "stopped in the debugger" in result["notes"][0]

    state = call_tool_json(qtbot, tools["get_debug_state"])
    assert state["debugging"]
    assert state["location"]["line"] == 3
    assert state["stack"][state["current_frame"]]["function"] == "double"

    result = call_tool_json(
        qtbot, tools["debug_command"], command="p result"
    )
    assert result["output"] == "42"
    assert result["debugging"]

    call_tool_json(
        qtbot, tools["remove_breakpoint"], filename=filename, line=3
    )
    assert call_tool_json(qtbot, tools["list_breakpoints"]) == []

    result = call_tool_json(qtbot, tools["debug_command"], command="c")
    assert not result["debugging"]
    assert result["location"] is None
    assert "42" in result["output"]

    # Without breakpoints, it stops at the first line
    call_tool_json(qtbot, tools["start_debugging"], filename=filename)
    state = call_tool_json(qtbot, tools["get_debug_state"])
    assert state["location"]["line"] == 1

    result = call_tool_json(qtbot, tools["debug_command"], command="q")
    assert not result["debugging"]


def test_debugging_belongs_to_its_agent(main_window, tools, qtbot, tmp_path):
    """
    Only the agent that started debugging sends debugger commands, and the
    text the user has at the prompt is kept.
    """
    filename = str(tmp_path / "debug_me.py")
    with open(filename, "w") as f:
        f.write("value = 1\nvalue += 1\n")

    agent_1 = Caller("agent-1", "Agent 1")
    agent_2 = Caller("agent-2", "Agent 2")

    with calling_as(agent_1):
        call_tool_json(qtbot, tools["start_debugging"], filename=filename)

    with calling_as(agent_2):
        content, is_error = call_tool(
            qtbot, tools["debug_command"], command="n"
        )
    assert is_error
    assert "Agent 1 is debugging" in content[0]["text"]

    shell = main_window.ipyconsole.get_current_shellwidget()
    qtbot.keyClicks(shell._control, "p 'mine'")
    with calling_as(agent_1):
        result = call_tool_json(
            qtbot, tools["debug_command"], command="p 40 + 2"
        )
    assert result["output"] == "42"
    qtbot.waitUntil(lambda: shell.input_buffer == "p 'mine'")

    shell.input_buffer = ""
    with calling_as(agent_1):
        result = call_tool_json(qtbot, tools["debug_command"], command="q")
    assert not result["debugging"]


def test_profiling(main_window, tools, qtbot, tmp_path):
    """Agents can profile code and files and drill into the results."""
    result = call_tool_json(
        qtbot,
        tools["profile_code"],
        code=(
            "def slow():\n"
            "    return sum(i * i for i in range(300_000))\n"
            "\n"
            "def main():\n"
            "    for _ in range(3):\n"
            "        slow()\n"
            "    print('done')\n"
            "\n"
            "main()"
        ),
    )
    assert result["output"] == "done\n"
    functions = {f["function"]: f for f in result["profile"]["functions"]}
    assert functions["slow"]["calls"] == 3
    assert not functions["slow"]["library"]
    assert functions["<built-in method builtins.sum>"]["library"]

    # The results are in the Profiler pane too
    profiler = main_window.get_plugin("profiler")
    shell = main_window.ipyconsole.get_current_shellwidget()
    data_tree = profiler.get_widget().get_widget_for_shellwidget(
        shell
    ).data_tree
    assert data_tree.profdata is not None

    details = call_tool_json(
        qtbot, tools["get_profile_results"], function="main"
    )
    (main,) = details["matches"]
    assert [callee["function"] for callee in main["callees"]][:1] == ["slow"]

    user_code = call_tool_json(
        qtbot,
        tools["get_profile_results"],
        sort="total",
        include_libraries=False,
    )
    assert all(not f["library"] for f in user_code["functions"])

    content, is_error = call_tool(
        qtbot, tools["get_profile_results"], function="missing"
    )
    assert is_error

    # Files are profiled with their path, like with Run > Profile
    filename = str(tmp_path / "profile_me.py")
    with open(filename, "w") as f:
        f.write(
            "def work():\n"
            "    return sorted(range(100_000), reverse=True)\n"
            "\n"
            "for _ in range(5):\n"
            "    work()\n"
        )
    result = call_tool_json(
        qtbot, tools["profile_file"], filename=filename
    )
    functions = {f["function"]: f for f in result["profile"]["functions"]}
    assert functions["work"]["calls"] == 5
    assert osp.normcase(functions["work"]["file"]) == osp.normcase(filename)
    assert not functions["work"]["library"]


class AnsweringContext(CallContext):
    """Call context of a client whose user answers with ``answer``."""

    can_ask_user = True

    def __init__(self, answer):
        self.answer = answer
        self.questions = []

    def ask_user(self, message, choices, title="", default=None):
        self.questions.append((message, choices))
        future = Future()
        future.set_result(
            next(choice for choice in choices if self.answer in choice)
        )
        return future


def test_project_tools(main_window, tools, qtbot, tmp_path):
    """Agents open and close projects after the user confirms it."""
    mcp_server = main_window.get_plugin("mcp_server")
    projects = main_window.get_plugin("project_explorer")
    mcp_server.register_client("agent-1", "Agent 1")
    mcp_server.register_client("agent-2", "Agent 2")
    agent = Caller("agent-1", "Agent 1")
    folder = tmp_path / "analysis"
    folder.mkdir()

    # It needs the user's confirmation
    with calling_as(agent):
        content, is_error = call_tool(
            qtbot, tools["open_project"], path=str(folder)
        )
    assert is_error
    assert "confirmation" in content[0]["text"]

    declining = AnsweringContext("Don't")
    with calling_as(agent, declining):
        content, is_error = call_tool(
            qtbot, tools["open_project"], path=str(folder)
        )
    assert is_error
    assert projects.get_active_project_path() is None

    # The folder becomes a project
    accepting = AnsweringContext("Open")
    with calling_as(agent, accepting):
        result = call_tool_json(
            qtbot, tools["open_project"], path=str(folder)
        )
    assert result == {"project": str(folder), "created": True}
    message = accepting.questions[0][0]
    assert message.startswith("Agent 1 wants to open")
    assert "restarts all IPython consoles" in message
    assert projects.get_active_project_path() == str(folder)

    # Other agents are told, but not the one that did it
    notes = mcp_server._dispatcher.take_notes("agent-2")
    assert len(notes) == 1
    assert notes[0].startswith(f"Agent 1 opened the project {folder}")
    assert mcp_server._dispatcher.take_notes("agent-1") == []

    with calling_as(agent):
        sessions = call_tool_json(qtbot, tools["list_agent_sessions"])
    assert sessions == [
        {"name": "Agent 1", "you": True, "busy": False},
        {"name": "Agent 2", "you": False, "busy": False},
    ]

    with calling_as(agent, AnsweringContext("Close")):
        result = call_tool_json(qtbot, tools["close_project"])
    assert result == {"project": str(folder)}
    assert projects.get_active_project_path() is None
    notes = mcp_server._dispatcher.take_notes("agent-2")
    assert len(notes) == 1
    assert notes[0].startswith(f"Agent 1 closed the project {folder}.")


def test_console_notes(main_window, tools, qtbot):
    """
    Agents are told when a console they used restarts, dies or closes.
    """
    mcp_server = main_window.get_plugin("mcp_server")
    ipyconsole = main_window.ipyconsole
    agent_1 = {"id": "agent-1", "name": "Agent 1"}
    mcp_server.register_client("agent-1", "Agent 1")
    mcp_server.register_client("agent-2", "Agent 2")
    notes = mcp_server._dispatcher._notes

    def run(code, console_id=None, timeout=60):
        arguments = {"code": code, "timeout": timeout}
        if console_id:
            arguments["console_id"] = console_id
        results = []
        mcp_server._dispatcher.call(
            "execute_code",
            arguments,
            agent_1,
            lambda content, is_error: results.append(
                [item.get("text") for item in content]
            ),
        )
        qtbot.waitUntil(lambda: bool(results), timeout=SHELL_TIMEOUT)
        return results[0]

    # Agent 1 uses the selected console, 1/A
    run("x = 1")
    shell = ipyconsole.get_current_shellwidget()

    ipyconsole.restart_kernel()
    qtbot.waitUntil(lambda: bool(notes.get("agent-1")), timeout=SHELL_TIMEOUT)
    assert notes["agent-1"] == [
        "The user restarted console 1/A in Spyder, so the variables, "
        "imports and figures created in it before are gone."
    ]
    assert "agent-2" not in notes

    # It gets the note with its next call's result
    qtbot.waitUntil(lambda: shell.spyder_kernel_ready, timeout=SHELL_TIMEOUT)
    qtbot.wait(1000)
    texts = run("y = 2")
    assert texts[0].startswith("Since your last call, in Spyder:")
    assert "The user restarted console 1/A" in texts[0]

    # A kernel that dies. It may die while the call that killed it is still
    # running, so the note can come with that call's result.
    texts = run("import os; os._exit(1)", timeout=5)

    def told_about_death():
        told = texts + notes.get("agent-1", [])
        return any("The kernel of console 1/A died" in t for t in told)

    qtbot.waitUntil(told_about_death, timeout=SHELL_TIMEOUT)
    notes.pop("agent-1", None)
    qtbot.waitUntil(lambda: shell.spyder_kernel_ready, timeout=SHELL_TIMEOUT)

    # A console of its own that is closed
    console = call_tool_json(qtbot, tools["new_console"], name="Agent 1")
    run("z = 3", console_id=console["id"])
    client = [
        c for c in ipyconsole.get_clients()
        if c.shellwidget is ipyconsole.get_console_shellwidget(console["id"])
    ][0]
    ipyconsole.get_widget().close_client(client=client, ask_recursive=False)
    qtbot.waitUntil(lambda: bool(notes.get("agent-1")), timeout=SHELL_TIMEOUT)
    assert notes.pop("agent-1") == [
        f"The user closed console {console['id']}, which you used. Use "
        f"list_consoles to choose another console, or new_console to open "
        f"one."
    ]
    assert "agent-2" not in notes


def test_diagnostics(main_window, tools, qtbot, tmp_path):
    filename = str(tmp_path / "lint_me.py")
    with open(filename, "w") as f:
        f.write("import os\n")
    main_window.get_plugin("editor").load(filename)

    def unused_import_reported():
        content, is_error = call_tool(
            qtbot, tools["get_diagnostics"], filename=filename
        )
        return not is_error and "imported but unused" in content[0]["text"]

    qtbot.waitUntil(unused_import_reported, timeout=60000)
    diagnostics = call_tool_json(
        qtbot, tools["get_diagnostics"], filename=filename
    )
    assert diagnostics[0]["line"] == 1
    assert diagnostics[0]["severity"] == "warning"


def test_tools_keep_focus(main_window, tools, qtbot, tmp_path):
    """Tools don't take the keyboard focus from the user."""
    shell = main_window.ipyconsole.get_current_shellwidget()
    console = shell._control
    editor = main_window.get_plugin("editor")
    first = str(tmp_path / "first.py")
    second = str(tmp_path / "second.py")
    for filename in [first, second]:
        with open(filename, "w") as f:
            f.write("value = 1\n")

    # Without the guard, opening a file gives focus to the Editor
    focus(qtbot, console)
    call_tool(qtbot, tools["open_file"], filename=first)
    assert QApplication.focusWidget() is editor.get_current_editor()

    # Tool calls from agents keep it in the console
    focus(qtbot, console)
    call_tool(qtbot, tools["open_file"], keep_focus=True, filename=second)
    assert editor.get_current_filename() == second
    assert QApplication.focusWidget() is console


def test_focus_follows_user(main_window, tools, qtbot):
    """If the user moves the focus while a tool runs, it stays there."""
    shell = main_window.ipyconsole.get_current_shellwidget()
    codeeditor = main_window.get_plugin("editor").get_current_editor()
    focus(qtbot, shell._control)

    results = []
    call_tool_keeping_focus(
        tools["execute_code"],
        {"code": "import time; time.sleep(3)"},
        lambda content, is_error: results.append(is_error),
    )

    # The user clicks in the Editor while the code runs
    qtbot.wait(500)
    qtbot.mouseClick(codeeditor.viewport(), Qt.LeftButton)
    qtbot.waitUntil(lambda: QApplication.focusWidget() is codeeditor)

    qtbot.waitUntil(lambda: len(results) > 0, timeout=SHELL_TIMEOUT)
    qtbot.wait(200)
    assert QApplication.focusWidget() is codeeditor


def test_debugger_keeps_focus(main_window, tools, qtbot, tmp_path):
    """The console doesn't take the focus when the debugger stops."""
    filename = str(tmp_path / "debug_focus.py")
    with open(filename, "w") as f:
        f.write("a = 1\nb = 2\n")

    editor = main_window.get_plugin("editor")
    focus(qtbot, editor.get_current_editor())
    result = call_tool_json(
        qtbot, tools["start_debugging"], keep_focus=True, filename=filename
    )
    assert "stopped in the debugger" in result["notes"][0]

    # The Editor shows the debugged file and keeps the focus
    assert editor.get_current_filename() == filename
    assert QApplication.focusWidget() is editor.get_current_editor()

    call_tool_json(qtbot, tools["debug_command"], keep_focus=True, command="n")
    assert QApplication.focusWidget() is editor.get_current_editor()

    call_tool_json(qtbot, tools["debug_command"], keep_focus=True, command="q")
