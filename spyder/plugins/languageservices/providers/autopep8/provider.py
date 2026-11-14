# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Python formatting with autopep8."""

from __future__ import annotations

# Local imports
from spyder.plugins.languageservices.api.formatting import (
    SubprocessFormatterProvider,
)
from spyder.utils.misc import get_python_executable


class Autopep8Provider(SubprocessFormatterProvider):
    """Formats Python documents with autopep8, run by Spyder's interpreter.

    autopep8 returns its input unchanged on a syntax error, so the text is
    compiled first and the ``SyntaxError`` propagates instead.
    """

    NAME = "autopep8"

    def command(self, path, line_length, line_range):
        command = [
            get_python_executable(), "-m", "autopep8",
            "--max-line-length", str(line_length),
        ]
        if line_range is not None:
            command += ["--line-range", str(line_range[0]), str(line_range[1])]
        return command + ["-"]

    async def format_text(self, text, path, line_length, line_range=None):
        compile(text, path, "exec")
        return await super().format_text(text, path, line_length, line_range)
