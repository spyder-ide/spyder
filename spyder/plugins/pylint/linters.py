# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import importlib.util
import json
import os
import os.path as osp
import re
import sys
from dataclasses import dataclass
from typing import ClassVar, Final

# Third party imports
from qtpy.QtCore import QProcessEnvironment
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from .utils import get_pylintrc_path
from spyder.config.manager import CONF
from spyder.utils.misc import (
    get_home_dir,
    get_python_executable,
    getcwd_or_home,
)


@dataclass
class LinterMessage:
    line: int
    message: str  # e.g. "`zip()` without an explicit `strict=` parameter"

    # at least one of the two should be set
    rule_id: str = ""  # e.g. "B905"
    rule_name: str = ""  # e.g. "zip-without-explicit-strict"

    # column: int | None = None
    # end_line: int | None = None
    # end_column: int | None = None


class Linter:
    name: ClassVar[str]

    @classmethod
    def is_available(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def get_command(cls, file: str, project_dir: str) -> list[str]:
        raise NotImplementedError

    @classmethod
    def get_environment(cls) -> QProcessEnvironment:
        env = QProcessEnvironment()

        pythonpaths = CONF.get(
            "pythonpath_manager", "spyder_pythonpath", default=[]
        )
        if pythonpaths:
            env.insert("PYTHONPATH", os.pathsep.join(pythonpaths))

        return env

    @classmethod
    def get_working_dir(cls, file: str) -> str:
        return osp.dirname(file)

    @classmethod
    def parse_output(cls, output: str, file: str) -> list[LinterMessage]:
        raise NotImplementedError

    @classmethod
    def exit_code_is_fatal(cls, code: int) -> bool:
        raise NotImplementedError


class RuffLinter(Linter):
    name = "ruff"

    @classmethod
    def is_available(cls) -> bool:
        return True  # Spyder dependency

    @classmethod
    def get_command(cls, file: str, project_dir: str) -> list[str]:
        return [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--exit-zero",
            "--output-format=json",
            file,
        ]

    @classmethod
    def parse_output(cls, output: str, file: str) -> list[LinterMessage]:
        return [
            LinterMessage(
                line=message["location"]["row"],
                message=message["message"],
                rule_id=message["code"],
                # rule_name=  # requires "sarif" output
            )
            for message in json.loads(output)
        ]

    @classmethod
    def exit_code_is_fatal(cls, code: int) -> bool:
        return code != 0  # requires "--exit-zero"


class MypyLinter(Linter):
    name = "mypy"

    @classmethod
    def is_available(cls) -> bool:
        return importlib.util.find_spec("mypy") is not None

    @classmethod
    def get_command(cls, file: str, project_dir: str) -> list[str]:
        return [
            sys.executable,
            "-m",
            "mypy",
            "--output=json",
            file,
        ]

    @classmethod
    def get_environment(cls) -> QProcessEnvironment:
        env = super().get_environment()
        if env.contains("PYTHONPATH"):
            env.insert("MYPYPATH", env.value("PYTHONPATH"))

        return env

    @classmethod
    def parse_output(cls, output: str, file: str) -> list[LinterMessage]:
        filename = osp.basename(file)

        def filter_(message_file: str) -> bool:
            if osp.isabs(message_file):
                return message_file == file
            else:
                return message_file == filename

        return [
            LinterMessage(
                line=message["line"],
                message=message["message"],
                rule_name=message["code"],
            )
            for message in (json.loads(line) for line in output.splitlines() if line)
            if filter_(message["file"])
        ]

    @classmethod
    def exit_code_is_fatal(cls, code: int) -> bool:
        return code not in (0, 1)


class PylintLinter(Linter):
    name = "Pylint"

    # --- Linter API
    @classmethod
    def is_available(cls) -> bool:
        return True  # Spyder dependency

    @classmethod
    def get_command(cls, file: str, project_dir: str) -> list[str]:
        command_args = [
            sys.executable,
            "-m",
            "pylint",
            "--exit-zero",
            "--output-format=text",
            '--msg-template={msg_id}:{symbol}:{line:3d},{column}: {msg}"',
        ]

        path_of_custom_interpreter = (
            PylintLinter._test_for_custom_interpreter()
        )
        if path_of_custom_interpreter is not None:
            command_args += [
                "--init-hook="
                "import pylint_venv; \
                    pylint_venv.inithook('{}',\
                    force_venv_activation=True)".format(
                    path_of_custom_interpreter.replace("\\", "\\\\")
                ),
            ]

        pylintrc_path = PylintLinter._get_pylintrc_path(file, project_dir)
        if pylintrc_path is not None:
            command_args += ["--rcfile={}".format(pylintrc_path)]

        command_args.append(file)
        return command_args

    @classmethod
    def get_environment(cls) -> QProcessEnvironment:
        """Get evironment variables for pylint command."""
        process_environment = QProcessEnvironment()

        process_environment.insert("PYTHONIOENCODING", "utf8")

        pythonpaths = CONF.get(
            "pythonpath_manager", "spyder_pythonpath", default=[]
        )
        if pythonpaths:
            pypath = os.pathsep.join(pythonpaths)
            # See PR spyder-ide/spyder#21891
            process_environment.insert("PYTHONPATH", pypath)

        if os.name == "nt":
            # Needed due to changes in Pylint 2.14.0
            # See spyder-ide/spyder#18175
            home_dir = get_home_dir()
            user_profile = os.environ.get("USERPROFILE", home_dir)
            process_environment.insert("USERPROFILE", user_profile)
            # Needed for Windows installations using standalone Python and pip.
            # See spyder-ide/spyder#19385
            if not is_conda_env(sys.prefix):
                process_environment.insert(
                    "APPDATA", os.environ.get("APPDATA")
                )

        return process_environment

    @classmethod
    def get_working_dir(cls, file: str) -> str:
        return getcwd_or_home()

    @classmethod
    def parse_output(cls, output: str, file: str) -> list[LinterMessage]:
        """
        Parse output and return current revious rate and results.
        """
        txt_module: Final = "************* Module "
        results: list[LinterMessage] = []

        module = ""  # Should not be needed - just in case something goes wrong
        for line in output.splitlines():
            if line.startswith(txt_module):
                # New module
                module = line[len(txt_module) :]
                continue
            # Supporting option include-ids: ("R3873:" instead of "R:")
            if not re.match(r"^[CRWE]+([0-9]{4})?:", line):
                continue

            items = {}
            idx_0 = 0
            idx_1 = 0
            key_names = ["msg_id", "message_name", "line_nb", "message"]
            for key_idx, key_name in enumerate(key_names):
                if key_idx == len(key_names) - 1:
                    idx_1 = len(line)
                else:
                    idx_1 = line.find(":", idx_0)

                if idx_1 < 0:
                    break

                item = line[(idx_0):idx_1]
                if not item:
                    break

                if key_name == "line_nb":
                    item = int(item.split(",")[0])

                items[key_name] = item
                idx_0 = idx_1 + 1
            else:
                linter_message = LinterMessage(
                    line=items["line_nb"],
                    message=items["message"],
                    rule_id=items["msg_id"],
                    rule_name=items["message_name"],
                )
                results.append(linter_message)

        return results

    @classmethod
    def exit_code_is_fatal(cls, code: int) -> bool:
        return code != 0  # requires "--exit-zero"

    # --- prive API
    @staticmethod
    def _get_pylintrc_path(filename: str, project_dir: str) -> str | None:
        """
        Get the path to the most proximate pylintrc config to the file.
        """
        search_paths = [
            # File"s directory
            osp.dirname(filename),
            # Working directory
            getcwd_or_home(),
            # Project directory
            project_dir,
            # Home directory
            osp.expanduser("~"),
            # directory of this file
            osp.dirname(__file__),
        ]

        return get_pylintrc_path(search_paths=search_paths)

    @staticmethod
    def _test_for_custom_interpreter() -> str | None:
        """
        Check if custom interpreter is active and if so, return path for the
        environment that contains it.
        """
        custom_interpreter = osp.normpath(
            CONF.get(option="executable", section="main_interpreter")
        )

        if (
            CONF.get(option="default", section="main_interpreter")
            or get_python_executable() == custom_interpreter
        ):
            path_of_custom_interpreter = None
        else:
            # Check if custom interpreter is still present
            if osp.isfile(custom_interpreter):
                # Pylint-venv requires the root path to a virtualenv, but what
                # we save in Preferences is the path to its Python interpreter.
                # So, we need to make the following adjustments here to get the
                # right path to pass to it.
                if os.name == "nt":
                    path_of_custom_interpreter = osp.dirname(
                        custom_interpreter
                    )
                else:
                    path_of_custom_interpreter = osp.dirname(
                        osp.dirname(custom_interpreter)
                    )
            else:
                path_of_custom_interpreter = None

        return path_of_custom_interpreter


# NOTE Update spyder/config/main.py when the list is changed
LINTERS = (PylintLinter, RuffLinter, MypyLinter)
LINTER_FOR_NAME = {linter.name: linter for linter in LINTERS}
