# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import uuid
import difflib
import logging
import textwrap

from spyder.plugins.remoteclient.api.jupyterhub import JupyterHubAPI
from spyder.plugins.remoteclient.api.jupyterhub.utils import (
    parse_notebook_cells,
)

logger = logging.getLogger(__name__)


DAEMONIZED_STOP_SERVER_HEADER = """
def _client_stop_server():
    import urllib.request
    request = urllib.request.Request(url="{delete_server_endpoint}", method= "DELETE")
    request.add_header("Authorization", "token {api_token}")
    urllib.request.urlopen(request)

def custom_exc(shell, etype, evalue, tb, tb_offset=None):
     _jupyerhub_client_stop_server()

get_ipython().set_custom_exc((Exception,), custom_exc)
"""


async def determine_username(
    hub,
    username=None,
    user_format="user-{user}-{id}",
    service_format="service-{name}-{id}",
    temporary_user=False,
):
    token = await hub.identify_token(hub.api_token)

    if username is None and not temporary_user:
        if token["kind"] == "service":
            logger.error(
                "cannot execute without specified username or "
                "temporary_user=True for service api token"
            )
            raise ValueError(
                "Service api token cannot execute without specified username "
                "or temporary_user=True for"
            )
        return token["name"]
    elif username is None and temporary_user:
        if token["kind"] == "service":
            return service_format.format(
                id=str(uuid.uuid4()), name=token["name"]
            )
        else:
            return user_format.format(id=str(uuid.uuid4()), name=token["name"])
    else:
        return username


async def execute_code(
    hub_url,
    cells,
    username=None,
    temporary_user=False,
    create_user=False,
    delete_user=False,
    server_creation_timeout=60,
    server_deletion_timeout=60,
    kernel_execution_timeout=60,
    daemonized=False,
    validate=False,
    stop_server=True,
    user_options=None,
    kernel_spec=None,
    auth_type="token",
    verify_ssl=True,
):
    hub = JupyterHubAPI(hub_url, auth_type=auth_type, verify_ssl=verify_ssl)
    result_cells = []

    async with hub:
        username = await determine_username(
            hub, username, temporary_user=temporary_user
        )
        try:
            jupyter = await hub.ensure_server(
                username,
                create_user=create_user,
                user_options=user_options,
                timeout=server_creation_timeout,
            )

            async with jupyter:
                kernel_id, kernel = await jupyter.ensure_kernel(
                    kernel_spec=kernel_spec
                )
                async with kernel:
                    if daemonized and stop_server:
                        await kernel.send_code(
                            username,
                            DAEMONIZED_STOP_SERVER_HEADER.format(
                                delete_server_endpoint=hub.api_url
                                / "users"
                                / username
                                / "server",
                                api_token=hub.api_token,
                            ),
                            wait=False,
                        )

                    for i, (code, expected_result) in enumerate(cells):
                        kernel_result = await kernel.send_code(
                            username,
                            code,
                            timeout=kernel_execution_timeout,
                            wait=(not daemonized),
                        )
                        result_cells.append((code, kernel_result))
                        if daemonized:
                            logger.debug(
                                f"kernel submitted cell={i} "
                                f'code=\n{textwrap.indent(code, "   >>> ")}'
                            )
                        else:
                            logger.debug(
                                f"kernel executing cell={i} "
                                f'code=\n{textwrap.indent(code, "   >>> ")}'
                            )
                            logger.debug(
                                f"kernel result cell={i} result=\n"
                                f'{textwrap.indent(kernel_result, "   | ")}'
                            )
                            if validate and (
                                kernel_result.strip()
                                != expected_result.strip()
                            ):
                                diff = "".join(
                                    difflib.unified_diff(
                                        kernel_result, expected_result
                                    )
                                )
                                logger.error(
                                    f"kernel result did not match expected "
                                    f"result diff={diff}"
                                )
                                raise ValueError(
                                    f"execution of cell={i} did not match "
                                    f"expected result diff={diff}"
                                )

                    if daemonized and stop_server:
                        await kernel.send_code(
                            username, "__client_stop_server()", wait=False
                        )
                if not daemonized:
                    await jupyter.delete_kernel(kernel_id)
            if not daemonized and stop_server:
                await hub.ensure_server_deleted(
                    username, timeout=server_deletion_timeout
                )
        finally:
            if delete_user and not daemonized:
                await hub.delete_user(username)

        return result_cells


async def execute_notebook(hub_url, notebook_path, **kwargs):
    cells = parse_notebook_cells(notebook_path)
    return await execute_code(hub_url, cells, **kwargs)
