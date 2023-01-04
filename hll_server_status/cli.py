import os
import re
import tomllib
from datetime import timedelta
from functools import wraps
from pathlib import Path
from pprint import pprint
from typing import Any, Callable

import tomlkit
import discord
import requests

from hll_server_status import constants
from hll_server_status.models import (
    URL,
    APIConfig,
    AppStore,
    Config,
    DiscordConfig,
    DisplayConfig,
    GameState,
    LoginParameters,
    Map,
    ServerName,
    Slots,
)

_APP_STORE = None
_APP_CONFIG = None


def get_app_store():
    global _APP_STORE

    if not _APP_STORE:
        _APP_STORE = AppStore()

    return _APP_STORE


def load_config(path: str | None = None, filename: str | None = None) -> Config:
    if not path:
        path = constants.CONFIG_DIR

    if not filename:
        filename = constants.CONFIG_FILENAME

    raw_config: dict[str, Any]
    with open(Path(path, filename), mode="rb") as fp:
        raw_config = tomllib.load(fp)

    # pprint(raw_config)

    config = Config(
        discord=DiscordConfig(**raw_config["discord"]),
        api=APIConfig(**raw_config["api"]),
        display=DisplayConfig(**raw_config["display"]),
    )

    return config


def load_message_ids(
    path: str | None = None, filename: str | None = None
) -> tomlkit.TOMLDocument:
    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = constants.CONFIG_FILENAME

    print(f"trying to load message ides from {Path(path, filename)}")

    message_ids = None
    with open(Path(path, filename), mode="r") as fp:
        message_ids = tomlkit.load(fp)

    print(f"loaded message ids={message_ids}")
    return message_ids


def save_message_ids(
    message_ids: tomlkit.TOMLDocument,
    path: str | None = None,
    filename: str | None = None,
) -> None:
    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = constants.CONFIG_FILENAME

    with open(Path(path, filename), mode="w") as fp:
        tomlkit.dump(message_ids, fp)


def get_config(path: str | None = None, filename: str | None = None):
    global _APP_CONFIG

    if not _APP_CONFIG:
        _APP_CONFIG = load_config(path, filename)

    return _APP_CONFIG


def get_credentials(
    username_env="CRCON_USERNAME", password_env="CRCON_PASSWORD"
) -> tuple[str, str]:
    username = os.getenv(username_env, None)
    password = os.getenv(password_env, None)

    if not username:
        raise ValueError("Username not set")

    if not password:
        raise ValueError("Password not set")

    return username, password


def login(
    config: Config,
    username: str,
    password: str,
    endpoint: str = "login",
    api_prefix=constants.API_PREFIX,
):
    params = LoginParameters(username=username, password=password)
    response = requests.post(
        config.api.base_server_url + api_prefix + endpoint,
        data=params.as_json(),
    )

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    return response.cookies.get(constants.SESSION_ID_COOKIE)


def with_login(func: Callable):
    @wraps(func)
    def inner(*args, **kwargs):
        app_store = get_app_store()
        config = get_config()
        username, password = get_credentials()

        if not app_store.cookies.get("sessionid", None):
            app_store.cookies["sessionid"] = login(config, username, password)

        return func(*args, **kwargs)

    return inner


@with_login
def get_api_result(
    endpoint: str,
    api_prefix: str | None = None,
    base_url: str | None = None,
):
    config = get_config()
    app_store = get_app_store()

    if base_url is None:
        base_url = config.api.base_server_url

    if api_prefix is None:
        api_prefix = constants.API_PREFIX

    # You can pass app_store.cookies in directly but it complains about types
    # even though it's a dict[str, str]
    response = requests.post(
        base_url + api_prefix + endpoint,
        cookies=app_store.cookies,  # type: ignore
    )

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    try:
        result = response.json()["result"]
    except IndexError:
        raise AttributeError("Received an invalid response from your CRCON Server")

    return result


def parse_gamestate(result: dict[str, Any]) -> GameState:
    time_remaining_pattern = re.compile(r"(\d{1}):(\d{2}):(\d{2})")
    matched = re.match(time_remaining_pattern, result["raw_time_remaining"])
    if not matched:
        raise ValueError("Received an invalid response from your CRCON Server")
    hours, minutes, seconds = matched.groups()

    result["time_remaining"] = timedelta(
        hours=int(hours), minutes=int(minutes), seconds=int(seconds)
    )

    result["current_map"] = Map(raw_name=result["current_map"])
    result["next_map"] = Map(raw_name=result["next_map"])

    return GameState(**result)


def parse_slots(result: str) -> Slots:
    player_count, max_players = result.split("/")
    return Slots(player_count=int(player_count), max_players=int(max_players))


def parse_map_rotation(result: list[str]) -> list[Map]:
    return [Map(raw_name=map_name) for map_name in result]


def get_map_picture_url(
    config: Config, map: Map, map_prefix=constants.MAP_PICTURES
) -> URL:
    base_map_name, _ = map.raw_name.split("_", maxsplit=1)
    url = (
        config.api.base_server_url
        + map_prefix
        + constants.MAP_TO_PICTURE[base_map_name]
    )

    # This is valid even though pylance complains about it
    return URL(url=url)  # type: ignore


def parse_server_name(result: dict[str, Any]) -> ServerName:
    return ServerName(name=result["name"], short_name=result["short_name"])


def parse_vip_slots_num(result: str):
    return int(result)


def parse_vips_count(result: str):
    return int(result)


def guess_map_rotation_position(
    rotation: list[Map], current_map: Map, next_map: Map
) -> list[int]:
    # As of U13 a map can be in a rotation more than once, but the index isn't
    # provided by RCON so we have to try to guess where we are in the rotation

    raw_names = [map.raw_name for map in rotation]

    # the current map is only in once
    if raw_names.count(current_map.raw_name) == 1:
        return [raw_names.index(current_map.raw_name)]

    # the current map is in more than once
    # if the next map is in only once then we know exactly where we are
    if raw_names.count(next_map.raw_name) == 1:
        # have to account for wrapping from the end to the start
        next_map_idx = raw_names.index(next_map.raw_name)
        current_map_idx = None

        # Somewhere besides the end of the rotation
        if next_map_idx == len(raw_names) - 1:
            current_map_idx = next_map_idx - 1
        # current map is the end of the rotation
        elif next_map_idx == 0:
            current_map_idx = len(raw_names) - 1
        else:
            raise ValueError("shouldn't get here")

        return [current_map_idx]

    # the current map is in more than once
    # and the next map is in multiple times so we can't determine where we are
    return [idx for idx, name in enumerate(raw_names) if name == current_map.raw_name]


ENDPOINTS_TO_PARSERS = {
    "get_gamestate": parse_gamestate,
    "get_vip_slots_num": parse_vip_slots_num,
    "get_vips_count": parse_vips_count,
    "get_status": parse_server_name,
    "get_slots": parse_slots,
}

OPTIONS_TO_ENDPOINTS = {
    "reserved_vip_slots": "get_vip_slots_num",
    "current_vips": "get_vips_count",
}


def build_header() -> discord.Embed:
    config = get_config()

    header_embed = discord.Embed()

    result = get_api_result(endpoint="get_status")
    server_name = parse_server_name(result)

    match config.display.header.name:
        case "name":
            header_embed.title = server_name.name
        case "short_name":
            header_embed.title = server_name.short_name

    if url := config.display.header.quick_connect_url:
        header_embed.add_field(name="Quick Connect", value=url, inline=False)

    if url := config.display.header.battlemetrics_url:
        header_embed.add_field(name="BattleMetrics Page", value=url, inline=False)

    for option in config.display.header.embeds:
        endpoint = OPTIONS_TO_ENDPOINTS[option.value]
        result = get_api_result(endpoint=endpoint)
        parser = ENDPOINTS_TO_PARSERS[endpoint]
        value = parser(result)
        header_embed.add_field(name=option.name, value=value, inline=option.inline)

    return header_embed


def build_gamestate(endpoint: str = "get_gamestate") -> discord.Embed:
    config = get_config()
    gamestate_embed = discord.Embed()

    result = get_api_result(endpoint=endpoint)
    gamestate = parse_gamestate(result)

    if config.display.gamestate.image:
        gamestate_embed.set_image(
            url=get_map_picture_url(config, gamestate["current_map"]).url
        )

    for option in config.display.gamestate.embeds:
        if option.value == "slots":
            result = get_api_result(endpoint="get_slots")
            slots = parse_slots(result)
            value = f"{slots.player_count}/{slots.max_players}"
        elif option.value == constants.EMPTY_EMBED:
            value = option.value
        elif option.value == "score":
            if (
                config.display.gamestate.score_format_ger_us
                and gamestate["current_map"].raw_name in constants.US_MAPS
            ):
                print(f"Using ger_us score format")
                format_str = config.display.gamestate.score_format_ger_us
            elif (
                config.display.gamestate.score_format_ger_rus
                and gamestate["current_map"].raw_name in constants.RUSSIAN_MAPS
            ):
                print(f"Using ger_rus score format")
                format_str = config.display.gamestate.score_format_ger_rus
            else:
                print(f"Using generic score format")
                format_str = config.display.gamestate.score_format

            print(f"{format_str=}")
            value = format_str.format(
                gamestate["allied_score"], gamestate["axis_score"]
            )
            print(f"{value=}")
        elif option.value in ("current_map", "next_map"):
            value = gamestate[option.value].name
        else:
            value = gamestate[option.value]

        gamestate_embed.add_field(name=option.name, value=value, inline=option.inline)

    return gamestate_embed


def build_map_rotation(endpoint: str = "get_map_rotation") -> str:
    config = get_config()
    map_rotation_embed = discord.Embed()

    result = get_api_result(endpoint=endpoint)
    map_rotation = parse_map_rotation(result)

    gamestate_result = get_api_result(endpoint="get_gamestate")
    gamestate = parse_gamestate(gamestate_result)
    current_map_positions = guess_map_rotation_position(
        map_rotation, gamestate["current_map"], gamestate["next_map"]
    )

    next_map_positions = []

    print(f"current map positions {current_map_positions=}")
    content: list[str] = []

    if config.display.map_rotation.display_title:
        content.append(config.display.map_rotation.title)

    if config.display.map_rotation.format_style == "color":
        for idx, map in enumerate(map_rotation):
            start_block = "```"
            end_block = "```"
            if idx in current_map_positions:
                start_block = (
                    "```"
                    + constants.COLOR_TO_CODE_BLOCK[
                        config.display.map_rotation.current_map_color
                    ]
                )
            elif idx in next_map_positions:
                start_block = (
                    "```"
                    + constants.COLOR_TO_CODE_BLOCK[
                        config.display.map_rotation.next_map_color
                    ]
                )
            # other map color
            else:
                start_block = (
                    "```"
                    + constants.COLOR_TO_CODE_BLOCK[
                        config.display.map_rotation.other_map_color
                    ]
                )

            print(f"{start_block=}")
            # print(f"{start_block=}")
            print(f"{end_block=}")
            content.append(start_block)
            content.append(f"{idx+1}{config.display.map_rotation.separator} {map.name}")
            content.append(end_block)
    elif config.display.map_rotation.format_style == "emoji":
        pass
    else:
        raise ValueError("should never get here")

    # content.append("```")
    # content.extend(
    #     [
    #         f"{idx+1}{config.display.map_rotation.separator} {map.name}"
    #         for idx, map in enumerate(map_rotation)
    #     ]
    # )
    # content.append("```")

    return "\n".join(content)


def main():

    config = load_config(constants.CONFIG_DIR, constants.CONFIG_FILENAME)
    # pprint(config)
    try:
        message_ids = load_message_ids()
    except FileNotFoundError:
        message_ids = tomlkit.document()
        table = tomlkit.table()
        # table.add("header", None)
        # table.add("gamestate", None)
        # table.add("map_rotation", None)
        message_ids.add("message_ids", table)

    webhook = discord.SyncWebhook.from_url(config.discord.webhook_url)

    if config.display.header.enabled:
        header_embed = build_header()
        if id_ := message_ids["message_ids"].get("header"):
            print("editing header message")
            webhook.edit_message(message_id=id_, embed=header_embed)
        else:
            print("creating new header message")
            message_id = webhook.send(embed=header_embed, wait=True)
            message_ids["message_ids"]["header"] = message_id.id

    if config.display.gamestate.enabled:
        gamestate_embed = build_gamestate()

        if id_ := message_ids["message_ids"].get("gamestate"):
            print("editing gamestate message")
            webhook.edit_message(message_id=id_, embed=gamestate_embed)
        else:
            print("creating new gamestate message")
            message_id = webhook.send(embed=gamestate_embed, wait=True)
            message_ids["message_ids"]["gamestate"] = message_id.id

    if config.display.map_rotation.enabled:
        map_rotation_content = build_map_rotation()

        if id_ := message_ids["message_ids"].get("map_rotation"):
            print("editing map_rotation message")
            webhook.edit_message(message_id=id_, content=map_rotation_content)
        else:
            print("creating new map_rotation message")
            message_id = webhook.send(content=map_rotation_content, wait=True)
            message_ids["message_ids"]["map_rotation"] = message_id.id

    save_message_ids(message_ids)


if __name__ == "__main__":
    main()
