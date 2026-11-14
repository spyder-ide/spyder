# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Python formatting with black."""

from __future__ import annotations

# Local imports
from spyder.plugins.languageservices.api.formatting import (
    SubprocessFormatterProvider,
)
from spyder.utils.misc import get_python_executable


class BlackProvider(SubprocessFormatterProvider):
    """Formats Python documents with black, run by Spyder's interpreter."""

    NAME = "black"

    def command(self, path, line_length, line_range):
        import black

        command = [
            get_python_executable(), "-m", "black", "-q",
            "--stdin-filename", path,
        ]
        pyproject = black.find_pyproject_toml((path,))
        options = black.parse_pyproject_toml(pyproject) if pyproject else {}
        # A line length in the project configuration wins over Spyder's.
        if "line_length" not in options:
            command += ["--line-length", str(line_length)]
        if line_range is not None:
            command += ["--line-ranges", f"{line_range[0]}-{line_range[1]}"]
        return command + ["-"]
