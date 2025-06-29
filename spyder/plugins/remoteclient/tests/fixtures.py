# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from pathlib import Path
import socket
import subprocess
import time
import typing
import uuid

import pytest
import requests

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.widgets import AuthenticationMethod


__all__ = [
    "remote_client_id",
    "ssh_server_addr",
    "ssh_client_id",
    "jupyterhub_server_addr",
    "jupyterhub_client_id",
]

# NOTE: These credentials are hardcoded in the Dockerfile.
USERNAME = "ubuntu"
PASSWORD = USERNAME

_COMPOSE_FILE = str(Path(__file__).resolve().parent / "docker-compose.yml")
_COMPOSE_PROJECT_NAME = "spyder-remote-client-tests"


def start_docker_service(service: str) -> None:
    """docker-compose up for one service only (no deps, build if needed)."""
    subprocess.check_call(
        [
            "docker",
            "compose",
            "-f",
            _COMPOSE_FILE,
            "-p",
            _COMPOSE_PROJECT_NAME,
            "up",
            "-d",
            # "--build",
            service,
        ],
    )


def stop_docker_service(service: str) -> None:
    """docker-compose down for one service only (no deps)."""
    subprocess.check_call(
        [
            "docker",
            "compose",
            "-f",
            _COMPOSE_FILE,
            "-p",
            _COMPOSE_PROJECT_NAME,
            "down",
            "--remove-orphans",
            service
        ],
    )


def get_addr_for_port(service_name: str, container_port: int):
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            _COMPOSE_PROJECT_NAME,
            "port",
            service_name,
            str(container_port),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    host, port = result.stdout.strip().split(":")
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return host, int(port)


def check_server(ip="127.0.0.1", port=22, timeout=30):
    """Check if a server is listening on the given IP and port.

    Args
    ----
        ip (str, optional): IP address to check. Defaults to "127.0.0.1".
        port (int, optional): Port to check. Defaults to 22.

    Raises
    ------
        TimeoutError: If the server is not reachable within the timeout period.
    """
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_port():
        try:
            test_socket.connect((ip, port))
        except OSError:
            return False
        else:
            return True

    start = time.monotonic()
    while not test_port():
        if time.monotonic() - start > timeout:
            msg = f"Timeout waiting for socket on {ip}:{port}"
            test_socket.close()
            raise TimeoutError(
                msg,
            )
        time.sleep(1)
    test_socket.close()


@pytest.fixture(
    scope="class",
    params=["ssh_client_id", "jupyterhub_client_id"],
)
def remote_client_id(request):
    """
    Fixture to provide the remote client ID based on the request parameter.
    """
    return request.getfixturevalue(request.param)


@pytest.fixture(scope="class")
def ssh_client_id(
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

    remote_client.load_ssh_client(options=ssh_options, config_id=config_id)

    try:
        yield config_id
    finally:
        AsyncDispatcher(
            loop="asyncssh",
            early_return=False,
        )(remote_client._remote_clients[config_id].close)()


@pytest.fixture(scope="class")
def jupyterhub_client_id(
    jupyterhub_server_addr: typing.Tuple[str, int], remote_client
) -> typing.Iterator[str]:
    """Add the Spyder Remote Client plugin to the registry."""
    jupyterhub_options = {
        "url": f"http://{jupyterhub_server_addr[0]}:{jupyterhub_server_addr[1]}",
        "token": "test_api_key",
    }
    config_id = str(uuid.uuid4())

    remote_client.set_conf(
        f"{config_id}/client_type", "jupyterhub"
    )
    remote_client.set_conf(
        f"{config_id}/{AuthenticationMethod.JupyterHub}/name", "test-server"
    )

    remote_client.load_jupyterhub_client(
        options=jupyterhub_options, config_id=config_id
    )

    try:
        yield config_id
    finally:
        AsyncDispatcher(
            loop="asyncssh",
            early_return=False,
        )(remote_client._remote_clients[config_id].close)()


@pytest.fixture(scope="class")
def ssh_server_addr():
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
    service_name = "test-spyder-remote-server"
    start_docker_service(service_name)
    docker_ip, port = get_addr_for_port(service_name, 22)

    check_server(ip=docker_ip, port=port)
    try:
        yield (docker_ip, port)
    finally:
        stop_docker_service(service_name)


@pytest.fixture(scope="class")
def jupyterhub_server_addr():
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
    service_name = "test-spyder-jupyterhub"
    start_docker_service(service_name)

    docker_ip, port = get_addr_for_port(service_name, 8000)

    check_server(ip=docker_ip, port=port)
    timeout = 30
    start = time.monotonic()
    while True:
        try:
            if requests.get(
                f"http://{docker_ip}:{port}/hub/api",
                timeout=5,
            ).status_code == 200:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        if time.monotonic() - start > timeout:
            msg = f"Timeout waiting for JupyterHub server on {docker_ip}:{port}"
            raise TimeoutError(
                msg,
            )
    try:
        yield (docker_ip, port)
    finally:
        stop_docker_service(service_name)
