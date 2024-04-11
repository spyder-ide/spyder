# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Remote Client API.
"""
from __future__ import annotations
from datetime import datetime
import logging
import typing


class KernelsList(typing.TypedDict):
    kernels: list[str]

class KernelInfo(typing.TypedDict):
    alive: bool
    pid: int

class DeleteKernel(typing.TypedDict):
    success: bool

class KernelConnectionInfo(typing.TypedDict):
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

class SSHClientOptions(typing.TypedDict):
    host: str
    port: int | None
    username: str
    password: str | None
    client_keys: str | typing.Sequence[str] | None
    known_hosts: str | typing.Sequence[str] | None
    config: typing.Sequence[str] | None
    platform: str | None

class ConnectionStatus:
    Inactive = "inactive"
    Connecting = "connecting"
    Active = "active"
    Error = "error"

class ConnectionInfo(typing.TypedDict):
    id: str
    status: ConnectionStatus
    message: str

class RemoteClientLog(typing.TypedDict):
    id: str
    message: str
    level: logging.DEBUG | logging.INFO | logging.WARNING | logging.ERROR | logging.CRITICAL
    created: float
