import asyncio

from client.execute import execute_code


async def simulate_users(hub_url, num_users, user_generator, workflow="concurrent"):
    jupyterhub_sessions = []

    if workflow == "concurrent":
        for i, (username, cells) in zip(range(num_users), user_generator):
            jupyterhub_sessions.append(
                execute_code(
                    hub_url=hub_url,
                    username=username,
                    cells=cells,
                    create_user=True,
                    delete_user=True,
                )
            )

        return await asyncio.gather(*jupyterhub_sessions)
    else:
        raise ValueError("uknown type of jupyterhub workflow to simulate")
