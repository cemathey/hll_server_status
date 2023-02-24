import httpx
import trio
from pprint import pprint
import json


async def login(username, password):
    data = {"username": username, "password": password}
    json_data = json.dumps(data)
    pprint(json_data)
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://rcon.squidds.tv/api/login",
            json=data,
        )

    pprint(r)
    pprint(r.cookies)
    pprint(type(r.cookies))
    pprint(type(r.cookies["sessionid"]))
    pprint(r.cookies["sessionid"])


trio.run(login, "ServerStatus", "FRoKHtcL4ZT4ZXyspq7G")
