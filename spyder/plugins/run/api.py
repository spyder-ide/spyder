# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder Run API."""

# Standard library imports
import sys
from enum import Enum
from typing import Tuple, Dict, TypedDict, Any

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class RunActions:
    Run = 'run'
    Configure = 'configure'
    ReRun = 're-run last script'


class RunContextType(dict):
    def __init__(self, identifier: str):
        super().__init__()

        self.identifier = identifier

    def __setattr__(self, key: str, value: str) -> None:
        if key in self:
            raise KeyError(f'Run {self.identifier} {key} is already registered!')
        self[key] = value

    def __getattribute__(self, key: str) -> str:
        if key in self:
            return self[key]
        return super().__getattribute__(key)


RunContext = RunContextType('context')
RunResultDisplay = RunContextType('result display')

RunContext.File = 'file'
RunContext.Selection = 'selection'
RunContext.Cell = 'cell'


class RunInformation(TypedDict):
    """Type stubs for """

    # The context of the input provided. e.g., file, selection, cell, others.
    # This attribute can be customized by the `RunInputProvider` when
    # registering with the run plugin. The context can be compared against the
    # values of `RunContext`. e.g., `info['context'] == RunContext.File`
    context: str

    # Input to process by the executor. The executor is responsible of the
    # correct interpretation of the input type.
    run_input: Any

    # File extension or identifier of the input context
    input_extension: str


class RunResults(TypedDict):
    pass


class RunInputProvider:
    """
    Interface used to retrieve inputs to run on a code executor.

    This API needs to be implemented by any plugin that wants to provide
    an input/file to a code runner. e.g., Editor files/ to be executed into
    the IPythonConsole.
    """

    def get_run_input(self, context: str) -> RunInformation:
        """
        Return the run information for the specified context.

        Arguments
        ---------
        context: str
            The context for the run request. It must be a member of
            :data:`RunContext`.

        Returns
        -------
        information: RunInformation
            A dictionary containing the information required by the run
            executor.
        """
        raise NotImplementedError(f'{type(self)} must implement get_run_input')


class RunExecutorProvider:
    """
    Interface used to execute run context information.

    This API needs to be implemented by any plugin that wants to execute
    an input produced by a :class:`RunInputProvider`.
    """

    def run_input(self, input: RunInformation) -> :
