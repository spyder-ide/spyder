# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import re

import aiohttp
import yarl


async def token_authentication(api_token, verify_ssl=True):
    return aiohttp.ClientSession(
        headers={"Authorization": f"token {api_token}"},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )


async def basic_authentication(hub_url, username, password, verify_ssl=True):
    session = aiohttp.ClientSession(
        headers={"Referer": str(yarl.URL(hub_url) / "hub" / "api")},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )

    await session.post(
        yarl.URL(hub_url) / "hub" / "login",
        data={
            "username": username,
            "password": password,
        },
    )

    return session


async def keycloak_authentication(
    hub_url, username, password, verify_ssl=True
):
    session = aiohttp.ClientSession(
        headers={"Referer": str(yarl.URL(hub_url) / "hub" / "api")},
        connector=aiohttp.TCPConnector(ssl=None if verify_ssl else False),
    )

    response = await session.get(yarl.URL(hub_url) / "hub" / "oauth_login")
    content = await response.content.read()
    auth_url = re.search('action="([^"]+)"', content.decode("utf8")).group(1)

    response = await session.post(
        auth_url.replace("&amp;", "&"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": username,
            "password": password,
            "credentialId": "",
        },
    )
    return session
