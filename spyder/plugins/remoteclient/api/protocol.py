# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder Remote Client API.
"""

from __future__ import annotations
import logging
import typing


class KernelInfo(typing.TypedDict):
    id: str
    name: str
    last_activity: str
    execution_state: str
    connections: int
    connection_info: KernelConnectionInfo


class KernelConnectionInfo(typing.TypedDict):
    transport: str
    ip: str
    shell_port: int
    iopub_port: int
    stdin_port: int
    hb_port: int
    control_port: int
    signature_scheme: str
    key: str


class SSHClientOptions(typing.TypedDict):
    host: str
    port: int | None
    username: str
    password: str | None
    client_keys: typing.Sequence[str] | None
    passphrase: str | None
    known_hosts: str | typing.Sequence[str] | None
    config: typing.Sequence[str] | None
    platform: str | None


class ConnectionStatus:
    Inactive = "inactive"
    Connecting = "connecting"
    Active = "active"
    Stopping = "stopping"
    Error = "error"


class ConnectionInfo(typing.TypedDict):
    id: str
    status: ConnectionStatus
    message: str


class RemoteClientLog(typing.TypedDict):
    id: str
    message: str
    level: (
        logging.DEBUG
        | logging.INFO
        | logging.WARNING
        | logging.ERROR
        | logging.CRITICAL
    )
    created: float
