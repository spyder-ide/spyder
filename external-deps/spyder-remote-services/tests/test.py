import asyncio
import logging

import textwrap

from client.api import JupyterHubAPI

logger = logging.getLogger(__name__)

SERVER_TIMEOUT = 3600
KERNEL_EXECUTION_TIMEOUT = 3600


SERVER_URL = "http://localhost:8000"

USERNAME = "user-test-1"

async def test():
    result_cells = []
    cells = [
        "a, b = 1, 2",
        "a + b"
    ]

    async with  JupyterHubAPI(
        SERVER_URL,
        auth_type="token",
        api_token="GiJ96ujfLpPsq7oatW1IJuER01FbZsgyCM0xH6oMZXDAV6zUZsFy3xQBZakSBo6P",
        verify_ssl=False
    ) as hub:
        try:
            # jupyter = await hub.ensure_server(
            #     USERNAME,
            #     timeout=SERVER_TIMEOUT,
            #     create_user=True,
            # )

            # # test kernel
            # async with jupyter:
            #     kernel_id, kernel = await jupyter.ensure_kernel()
            #     async with kernel:
            #         for i, code in enumerate(cells):
            #             kernel_result = await kernel.send_code(
            #                 USERNAME,
            #                 code,
            #                 timeout=KERNEL_EXECUTION_TIMEOUT,
            #                 wait=True,
            #             )
            #             result_cells.append((code, kernel_result))
            #             logger.warning(
            #                 f'kernel executing cell={i} code=\n{textwrap.indent(code, "   >>> ")}'
            #             )
            #             logger.warning(
            #                 f'kernel result cell={i} result=\n{textwrap.indent(kernel_result, "   | ")}'
            #             )
            
            # test custom spyder-service
            # spyder_service_response = await hub.get_service("spyder-service")
            # logger.warning(f'spyder-service: {spyder_service_response}')

            spyder_service_response = await hub.execute_get_service("spyder-service", "kernel")
            logger.warning(f'spyder-service-kernel-get: {spyder_service_response}')

            spyder_service_response = await hub.execute_post_service("spyder-service", "kernel")
            logger.warning(f'spyder-service-kernel-post: {spyder_service_response}')

            key = spyder_service_response['key']

            spyder_service_response = await hub.execute_get_service("spyder-service", f"kernel/{key}")
            logger.warning(f'spyder-service-kernel-get: {spyder_service_response}')

            spyder_service_response = await hub.execute_delete_service("spyder-service", f"kernel/{key}")
            logger.warning(f'spyder-service-kernel-delete: {spyder_service_response}')

            spyder_service_response = await hub.execute_get_service("spyder-service", "kernel")
            logger.warning(f'spyder-service-kernel-get: {spyder_service_response}')

        finally:
            if await hub.get_user(USERNAME) is not None:
                await hub.delete_user(USERNAME)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()
