# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Remote Client API.
"""
from typing import Optional, TypedDict, Union, Sequence


class KernelsList(TypedDict):
    kernels: list[str]

class KernelInfo(TypedDict):
    alive: bool
    pid: int

class DeleteKernel(TypedDict):
    success: bool

class KernelConnectionInfo(TypedDict):
    shell_port: int
    iopub_port: int
    stdin_port: int
    control_port: int
    hb_port: int
    ip: str
    key: str
    transport: str
    signature_scheme: str
    kernel_name: str

class SSHClientOptions(TypedDict):
    host: str
    port: Optional[int]
    username: str
    password: Optional[str]
    client_keys: Optional[Union[str, Sequence[str]]]
    known_hosts: Optional[Union[str, Sequence[str]]]
    config: Optional[Sequence[str]]
    platform: Optional[str]

class ConnectionStatus:
    Inactive = "inactive"
    Connecting = "connecting"
    Active = "active"
    Error = "error"
