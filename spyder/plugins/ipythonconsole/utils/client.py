# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Kernel Client subclass."""

# Standard library imports
import socket

# Third party imports
import asyncssh
from qtpy.QtCore import Signal
from qtconsole.client import QtKernelClient, QtZMQSocketChannel
from traitlets import Type

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.api.translations import _
from spyder.plugins.ipythonconsole import SpyderKernelError


class KernelClientTunneler:
    """Class to handle SSH tunneling for a kernel connection."""

    def __init__(self, ssh_connection, *, _close_conn_on_exit=False):
        self.ssh_connection = ssh_connection
        self._port_forwarded = {}
        self._close_conn_on_exit = _close_conn_on_exit

    def __del__(self):
        """Close all port forwarders and the connection if required."""
        for forwarder in self._port_forwarded.values():
            forwarder.close()

        if self._close_conn_on_exit:
            self.ssh_connection.close()

    @classmethod
    @AsyncDispatcher.dispatch(loop="asyncssh", early_return=False)
    async def new_connection(cls, *args, **kwargs):
        """Create a new SSH connection."""
        return cls(
            await asyncssh.connect(*args, **kwargs, known_hosts=None),
            _close_conn_on_exit=True,
        )

    @classmethod
    def from_connection(cls, ssh_connection):
        """Create a new KernelTunnelHandler from an existing connection."""
        return cls(ssh_connection)

    @AsyncDispatcher.dispatch(loop="asyncssh", early_return=False)
    async def forward_port(self, remote_host, remote_port):
        """Forward a port through the SSH connection."""
        local = self._get_free_port()
        try:
            self._port_forwarded[(remote_host, remote_port)] = (
                await self.ssh_connection.forward_local_port(
                    '127.0.0.1', local, remote_host, remote_port
                )
            )
        except asyncssh.Error as err:
            raise SpyderKernelError(
                _(
                    "It was not possible to open an SSH tunnel to connect to "
                    "the remote kernel. Please check your credentials and the "
                    "server connection status."
                )
            ) from err
        return local

    @staticmethod
    def _get_free_port():
        """Request a free port from the OS."""
        with socket.socket() as s:
            s.bind(("", 0))
            return s.getsockname()[1]


class SpyderKernelClient(QtKernelClient):
    # Enable receiving messages on control channel.
    # Useful for pdb completion
    control_channel_class = Type(QtZMQSocketChannel)
    sig_spyder_kernel_info = Signal(object)

    def _handle_kernel_info_reply(self, rep):
        """Check spyder-kernels version."""
        super()._handle_kernel_info_reply(rep)
        spyder_kernels_info = rep["content"].get("spyder_kernels_info", None)
        self.sig_spyder_kernel_info.emit(spyder_kernels_info)

    def tunnel_to_kernel(
        self, hostname=None, sshkey=None, password=None, ssh_connection=None
    ):
        """Tunnel to remote kernel."""
        if ssh_connection is not None:
            self.__tunnel_handler = KernelClientTunneler.from_connection(
                ssh_connection
            )
        elif sshkey is not None:
            self.__tunnel_handler = KernelClientTunneler.new_connection(
                password=password,
                client_keys=[sshkey],
                **self._split_shh_address(hostname),
            )
        else:
            self.__tunnel_handler = KernelClientTunneler.new_connection(
                password=password,
                **self._split_shh_address(hostname),
            )

        (
            self.shell_port,
            self.iopub_port,
            self.stdin_port,
            self.hb_port,
            self.control_port,
        ) = (
            self.__tunnel_handler.forward_port(self.ip, port)
            for port in (
                self.shell_port,
                self.iopub_port,
                self.stdin_port,
                self.hb_port,
                self.control_port,
            )
        )
        self.ip = "127.0.0.1"  # Tunneled to localhost

    @staticmethod
    def _split_shh_address(address):
        """Split ssh address into host and port."""
        user_host, _, port = address.partition(':')
        user, _, host = user_host.rpartition('@')
        return {
            'username': user if user else None,
            'host': host if host else None,
            'port': int(port) if port else None
        }
