# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from pathlib import Path
import socket
import typing
import uuid

import pytest

from spyder.plugins.remoteclient.widgets import AuthenticationMethod


__all__ = [
    "remote_client_id",
    "ssh_server_addr",
    "docker_compose_file",
]

# NOTE: These credentials are hardcoded in the Dockerfile.
USERNAME = "ubuntu"
PASSWORD = USERNAME


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Override the default docker-compose.yml file."""
    return str(Path(__file__).resolve().parent / "docker-compose.yml")


def check_server(ip="127.0.0.1", port=22):
    """Check if a server is listening on the given IP and port.

    Args
    ----
        ip (str, optional): IP address to check. Defaults to "127.0.0.1".
        port (int, optional): Port to check. Defaults to 22.

    Returns
    -------
        bool: server is listening on the given IP and port
    """
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        test_socket.connect((ip, port))
    except OSError:
        return False
    else:
        test_socket.close()
    return True


@pytest.fixture(scope="class")
def remote_client_id(
    ssh_server_addr: typing.Tuple[str, int], remote_client
) -> typing.Iterator[str]:
    """Add the Spyder Remote Client plugin to the registry."""
    ssh_options = {
        "host": ssh_server_addr[0],
        "port": ssh_server_addr[1],
        "username": USERNAME,
        "password": PASSWORD,
        "platform": "linux",
        "known_hosts": None,
    }
    config_id = str(uuid.uuid4())

    # Options Required by container widget
    remote_client.set_conf(
        f"{config_id}/auth_method", AuthenticationMethod.Password
    )
    remote_client.set_conf(
        f"{config_id}/{AuthenticationMethod.Password}/name", "test-server"
    )
    remote_client.set_conf(
        f"{config_id}/{AuthenticationMethod.Password}/address",
        ssh_server_addr[0],
    )
    remote_client.set_conf(
        f"{config_id}/{AuthenticationMethod.Password}/username", USERNAME
    )

    remote_client.load_client(options=ssh_options, config_id=config_id)

    try:
        yield config_id
    finally:
        remote_client.on_close()


@pytest.fixture(scope="class")
def ssh_server_addr(
    docker_ip: str, docker_services
) -> typing.Tuple[str, int]:
    """Start an SSH server from docker-compose and return its address.

    Args
    ----
        docker_ip (str): IP address of the Docker daemon.
        docker_services (Services): Docker services.

    Returns
    -------
        tuple: IP address and port of the SSH server.
    """
    # Build URL to service listening on random port.
    # NOTE: This is the service name and port in the docker-compose.yml file.
    port = docker_services.port_for("test-spyder-remote-server", 22)

    docker_services.wait_until_responsive(
        check=lambda: check_server(ip=docker_ip, port=port),
        timeout=30.0,
        pause=0.1,
    )

    return docker_ip, port
