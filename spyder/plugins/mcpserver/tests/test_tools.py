# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tests for the IPython console methods exposed as MCP tools."""

# Standard library imports
import base64
import json
import sys

# Third-party imports
import pytest

# Local imports
from spyder.api.plugins.exposed import Caller, calling_as
from spyder.plugins.ipythonconsole.tests.conftest import SHELL_TIMEOUT
from spyder.plugins.mcpserver.api import ToolCall
from spyder.plugins.mcpserver.exposed import tools_from_plugin

# A 1x1 PNG image
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChw"
    "GA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def tools(ipyconsole):
    return {tool.name: tool for tool in tools_from_plugin(ipyconsole)}


AGENT_1 = Caller("agent-1", "Agent 1")
AGENT_2 = Caller("agent-2", "Agent 2")


def start_tool(tool, caller=None, **arguments):
    """
    Call ``tool`` on behalf of ``caller`` without waiting for it. Returns
    the list its result is added to.
    """
    results = []
    with calling_as(caller):
        tool.call(
            ToolCall(
                arguments,
                lambda content, is_error: results.append((content, is_error)),
            )
        )
    return results


def call_tool(qtbot, tool, caller=None, **arguments):
    """Call ``tool`` and wait for its result."""
    results = start_tool(tool, caller, **arguments)
    qtbot.waitUntil(lambda: len(results) > 0, timeout=SHELL_TIMEOUT)
    return results[0]


def call_tool_json(qtbot, tool, caller=None, **arguments):
    """Call ``tool`` and return the data in its first content block."""
    content, is_error = call_tool(qtbot, tool, caller, **arguments)
    assert not is_error, content
    return json.loads(content[0]["text"]), content


def wait_idle(qtbot, ipyconsole):
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: not shell._executing, timeout=SHELL_TIMEOUT)


def test_list_consoles(ipyconsole, tools, qtbot):
    consoles, _ = call_tool_json(qtbot, tools["list_consoles"])
    assert len(consoles) == 1
    assert consoles[0]["id"] == "1/A"
    assert consoles[0]["state"] == "idle"
    assert consoles[0]["current"]

    # The working directory, where relative paths in its code are resolved
    shell = ipyconsole.get_current_shellwidget()
    assert consoles[0]["cwd"] == shell.get_cwd()
    assert consoles[0]["cwd"]


def test_execute_code_output(ipyconsole, tools, qtbot):
    """Test that stdout and results are captured."""
    result, _ = call_tool_json(
        qtbot, tools["execute_code"], code="print('hello')\n40 + 2"
    )
    assert result == {
        "output": "hello\nOut[1]: 42\n",
        "raised_exception": False,
        "images": [],
        "notes": [],
    }

    # The code and its output are shown in the console
    control = ipyconsole.get_current_shellwidget()._control
    assert "print('hello')" in control.toPlainText()


def test_execute_code_error(ipyconsole, tools, qtbot):
    """Test that tracebacks are returned without color codes."""
    result, _ = call_tool_json(qtbot, tools["execute_code"], code="1/0")

    # User code errors are results the agent can act on, not tool errors
    assert result["raised_exception"]
    assert "ZeroDivisionError" in result["output"]
    assert "\x1b[" not in result["output"]


def test_execute_code_images(ipyconsole, tools, qtbot):
    """Test that displayed images are returned as image content."""
    code = (
        "import base64\n"
        "from IPython.display import Image, display\n"
        f"display(Image(data=base64.b64decode({base64.b64encode(PNG)!r})))"
    )
    result, content = call_tool_json(qtbot, tools["execute_code"], code=code)
    assert result["images"] == ["<image 1>"]
    images = [item for item in content if item["type"] == "image"]
    assert len(images) == 1
    assert images[0]["mimeType"] == "image/png"
    assert base64.b64decode(images[0]["data"]) == PNG


def test_execute_code_timeout(ipyconsole, tools, qtbot):
    """Test long running code, busy consoles and interrupting them."""
    result, _ = call_tool_json(
        qtbot,
        tools["execute_code"],
        code="import time\nprint('start')\ntime.sleep(30)",
        timeout=1,
    )
    assert result["output"] == "start\n"
    assert "still running" in result["notes"][0]

    # More code waits while the console is busy, but not past its timeout
    content, is_error = call_tool(
        qtbot, tools["execute_code"], code="1", timeout=1
    )
    assert is_error
    assert "didn't run" in content[0]["text"]
    assert "busy" in content[0]["text"]

    content, is_error = call_tool(qtbot, tools["interrupt_console"])
    assert not is_error
    wait_idle(qtbot, ipyconsole)

    content, is_error = call_tool(qtbot, tools["execute_code"], code="1")
    assert not is_error


def test_execute_code_input(ipyconsole, tools, qtbot):
    """Test that waiting for user input is reported."""
    result, _ = call_tool_json(
        qtbot, tools["execute_code"], code="name = input('Name: ')"
    )
    assert "waiting for user input" in result["notes"][0]

    # Answer the prompt like the user would
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(lambda: shell._reading, timeout=SHELL_TIMEOUT)
    shell._control.insertPlainText("Spyder")
    qtbot.keyClick(shell._control, "\r")
    wait_idle(qtbot, ipyconsole)
    assert shell.get_value("name") == "Spyder"


def test_list_variables(ipyconsole, tools, qtbot):
    call_tool(qtbot, tools["execute_code"], code="answer = 42")

    variables, _ = call_tool_json(qtbot, tools["list_variables"])
    assert {
        "name": "answer",
        "type": "int",
        "size": 1,
        "value": "42",
    } in variables


def test_unknown_console(ipyconsole, tools, qtbot):
    content, is_error = call_tool(
        qtbot, tools["execute_code"], code="1", console_id="9/Z"
    )
    assert is_error
    assert "No console with id '9/Z'" in content[0]["text"]


def test_inspect_variable(ipyconsole, tools, qtbot):
    """Test that variables are summarized without running code visibly."""
    call_tool(
        qtbot,
        tools["execute_code"],
        code=(
            "import numpy as np\nimport pandas as pd\n"
            "arr = np.arange(10.0)\n"
            "df = pd.DataFrame({'a': [1, 2, None], 'b': ['x', 'y', 'z']})"
        ),
    )
    control = ipyconsole.get_current_shellwidget()._control
    console_text = control.toPlainText()

    summary, _ = call_tool_json(qtbot, tools["inspect_variable"], name="arr")
    assert summary["type"] == "numpy.ndarray"
    assert summary["shape"] == [10]
    assert (summary["min"], summary["max"], summary["mean"]) == (0, 9, 4.5)

    summary, _ = call_tool_json(qtbot, tools["inspect_variable"], name="df")
    assert summary["shape"] == [3, 2]
    # pandas 3 gives string columns their own dtype
    assert summary["columns"]["a"] == "float64"
    assert summary["columns"]["b"] in ("object", "str")
    assert summary["missing_values"] == {"a": 1}
    assert "x" in summary["head"]

    # Attributes can be inspected too
    summary, _ = call_tool_json(
        qtbot, tools["inspect_variable"], name="df.columns"
    )
    assert "Index" in summary["type"]

    # Nothing was shown in the console
    assert control.toPlainText() == console_text

    content, is_error = call_tool(
        qtbot, tools["inspect_variable"], name="missing"
    )
    assert is_error
    assert "There's no variable called 'missing'" in content[0]["text"]

    content, is_error = call_tool(
        qtbot, tools["inspect_variable"], name="arr + 1"
    )
    assert is_error
    assert "is not a variable name" in content[0]["text"]


def test_get_object_help(ipyconsole, tools, qtbot):
    """Test help for objects that aren't imported in the console."""
    info, _ = call_tool_json(
        qtbot, tools["get_object_help"], name="json.dumps"
    )
    assert info["signature"].startswith("json.dumps(obj")
    assert "Serialize" in info["doc"]
    assert info["module"] == "json"


def test_get_console_history(ipyconsole, tools, qtbot):
    call_tool(qtbot, tools["execute_code"], code="first = 1")
    call_tool(qtbot, tools["execute_code"], code="second = 2")
    call_tool(qtbot, tools["inspect_variable"], name="first")

    history, _ = call_tool_json(qtbot, tools["get_console_history"], count=2)
    assert [entry["input"] for entry in history] == ["first = 1", "second = 2"]


def test_run_file(ipyconsole, tools, qtbot, tmp_path):
    script = tmp_path / "script.py"
    script.write_text(
        "import os, sys\nprint('args:', sys.argv[1:])\nprint(os.getcwd())\n"
    )

    result, _ = call_tool_json(
        qtbot, tools["run_file"], filename=str(script), args="--fast 3"
    )
    assert not result["raised_exception"]
    assert "args: ['--fast', '3']" in result["output"]

    # It runs in the file's directory by default
    assert str(tmp_path) in result["output"]

    content, is_error = call_tool(
        qtbot, tools["run_file"], filename=str(tmp_path / "missing.py")
    )
    assert is_error


def test_run_cell_needs_editor(
    ipyconsole, tools, qtbot, tmp_path, monkeypatch
):
    # The Editor isn't available in these tests
    monkeypatch.setattr(
        ipyconsole, "get_plugin", lambda name, error=True: None
    )
    script = tmp_path / "cells.py"
    script.write_text("# %%\na = 1\n")
    content, is_error = call_tool(
        qtbot, tools["run_cell"], filename=str(script), cell=0
    )
    assert is_error
    assert "needs Spyder's Editor" in content[0]["text"]


def test_breakpoint_and_pdb_commands(ipyconsole, tools, qtbot):
    """Test code stopping in the debugger and running Pdb commands."""
    from spyder.plugins.ipythonconsole.utils.execution import (
        PdbCommandCollector,
    )

    shell = ipyconsole.get_current_shellwidget()
    result, _ = call_tool_json(
        qtbot,
        tools["execute_code"],
        code=(
            "def f():\n"
            "    x = 3\n"
            "    breakpoint()\n"
            "    return x * 2\n"
            "\n"
            "y = f()"
        ),
    )
    assert "stopped in the debugger" in result["notes"][0]
    assert shell.is_debugging()

    def run_pdb(command):
        future = PdbCommandCollector(shell, 30).run(command)
        qtbot.waitUntil(future.done, timeout=SHELL_TIMEOUT)
        return future.result()

    result = run_pdb("p x")
    assert result["output"] == "3"
    assert result["debugging"]
    # Since Python 3.13, breakpoint() stops on its own line instead of the
    # next one
    line = 3 if sys.version_info >= (3, 13) else 4
    assert result["location"]["line"] == line

    # Running code is refused while debugging
    content, is_error = call_tool(qtbot, tools["execute_code"], code="1")
    assert is_error
    assert "debugging" in content[0]["text"]

    result = run_pdb("c")
    assert not result["debugging"]
    assert result["location"] is None
    wait_idle(qtbot, ipyconsole)
    assert shell.get_value("y") == 6


def test_new_console(ipyconsole, tools, qtbot, tmp_path):
    """Agents can open their own console without changing the user's."""
    user_shell = ipyconsole.get_current_shellwidget()
    call_tool(qtbot, tools["execute_code"], code="owner = 'user'")

    console, _ = call_tool_json(
        qtbot, tools["new_console"], name="Agent", wdir=str(tmp_path)
    )
    assert console["id"] != "1/A"
    assert "Agent" in console["name"]

    # The user's console is still the selected one
    assert ipyconsole.get_current_shellwidget() is user_shell
    consoles, _ = call_tool_json(qtbot, tools["list_consoles"])
    assert [c["id"] for c in consoles if c["current"]] == ["1/A"]

    # The new console has its own namespace and working directory
    result, _ = call_tool_json(
        qtbot,
        tools["execute_code"],
        console_id=console["id"],
        code="import os\nprint('owner' in globals(), os.getcwd())",
    )
    assert result["output"] == f"False {tmp_path}\n"
    assert user_shell.get_value("owner") == "user"

    consoles, _ = call_tool_json(qtbot, tools["list_consoles"])
    new = [c for c in consoles if c["id"] == console["id"]][0]
    assert new["cwd"] == str(tmp_path)

    content, is_error = call_tool(
        qtbot, tools["new_console"], wdir=str(tmp_path / "missing")
    )
    assert is_error


def test_runs_wait_for_each_other(ipyconsole, tools, qtbot):
    """Agents sharing a console run their code one after the other."""
    first = start_tool(
        tools["execute_code"],
        AGENT_1,
        code="import time\ntime.sleep(2)\nshared = 1",
    )
    second = start_tool(tools["execute_code"], AGENT_2, code="print(shared)")

    # The second agent sees who is running code
    consoles, _ = call_tool_json(qtbot, tools["list_consoles"], AGENT_2)
    assert consoles[0]["running_for"] == "Agent 1"
    assert consoles[0]["waiting_runs"] == 1
    consoles, _ = call_tool_json(qtbot, tools["list_consoles"], AGENT_1)
    assert consoles[0]["running_for"] == "you"

    qtbot.waitUntil(
        lambda: bool(first and second), timeout=SHELL_TIMEOUT
    )
    assert not first[0][1]
    result = json.loads(second[0][0][0]["text"])
    assert result["output"] == "1\n"
    assert "waited" in result["notes"][0]


def test_user_goes_first(ipyconsole, tools, qtbot):
    """
    Agent code doesn't start while the user types, and what they typed is
    kept.
    """
    shell = ipyconsole.get_current_shellwidget()
    qtbot.keyClicks(shell._control, "typed = 1")

    results = start_tool(tools["execute_code"], AGENT_1, code="agent = 2")
    qtbot.wait(1000)
    assert not results
    assert not shell._executing

    # It runs once the user stops typing, and their text comes back
    qtbot.waitUntil(lambda: bool(results), timeout=SHELL_TIMEOUT)
    assert not results[0][1]
    wait_idle(qtbot, ipyconsole)
    qtbot.waitUntil(lambda: shell.input_buffer == "typed = 1")
    assert shell.get_value("agent") == 2

    # The user's text is still theirs to run
    prompts = len(shell._prompt_blocks)
    qtbot.keyClick(shell._control, "\r")
    qtbot.waitUntil(
        lambda: len(shell._prompt_blocks) > prompts, timeout=SHELL_TIMEOUT
    )
    assert shell.get_value("typed") == 1


def test_interrupt_own_code_only(ipyconsole, tools, qtbot):
    """Agents can only interrupt their own code."""
    result, _ = call_tool_json(
        qtbot,
        tools["execute_code"],
        AGENT_1,
        code="import time\ntime.sleep(30)",
        timeout=1,
    )
    assert "still running" in result["notes"][0]

    content, is_error = call_tool(qtbot, tools["interrupt_console"], AGENT_2)
    assert is_error
    assert "Agent 1 is running code" in content[0]["text"]

    # Interrupting cancels the agent's own code that is waiting
    waiting = start_tool(tools["execute_code"], AGENT_2, code="never = 1")
    content, is_error = call_tool(qtbot, tools["interrupt_console"], AGENT_2)
    assert not is_error
    assert "Cancelled 1" in content[0]["text"]
    assert waiting and waiting[0][1]
    assert "cancelled" in waiting[0][0][0]["text"]

    content, is_error = call_tool(qtbot, tools["interrupt_console"], AGENT_1)
    assert not is_error
    assert "Interrupted" in content[0]["text"]
    wait_idle(qtbot, ipyconsole)

    shell = ipyconsole.get_current_shellwidget()
    assert not shell.is_defined("never")


def test_debugging_belongs_to_its_agent(ipyconsole, tools, qtbot):
    """Only the agent whose code stopped in the debugger can run code."""
    result, _ = call_tool_json(
        qtbot,
        tools["execute_code"],
        AGENT_1,
        code="def f():\n    breakpoint()\n\nf()",
    )
    assert "stopped in the debugger" in result["notes"][0]

    content, is_error = call_tool(
        qtbot, tools["execute_code"], AGENT_2, code="1"
    )
    assert is_error
    assert "Agent 1 is debugging" in content[0]["text"]

    content, is_error = call_tool(
        qtbot, tools["execute_code"], AGENT_1, code="1"
    )
    assert is_error
    assert "debugging your code" in content[0]["text"]

    consoles, _ = call_tool_json(qtbot, tools["list_consoles"], AGENT_2)
    assert consoles[0]["state"] == "debugging"
    assert consoles[0]["running_for"] == "Agent 1"
