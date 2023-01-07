import logging
import os
import re
import sys
import tomllib
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import discord
import requests
import tomlkit

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
    OutputConfig,
    ServerName,
    Slots,
)

logging.basicConfig(level=os.getenv("LOGGING_LEVEL", logging.INFO), stream=sys.stdout)
logger = logging.getLogger()


def load_config(path: Path | None = None) -> Config:
    if not path:
        path = Path(constants.CONFIG_DIR, constants.CONFIG_FILENAME)

    raw_config: dict[str, Any]
    with open(Path(path), mode="rb") as fp:
        raw_config = tomllib.load(fp)

    config = Config(
        output=OutputConfig(**raw_config["output"]),
        discord=DiscordConfig(**raw_config["discord"]),
        api=APIConfig(**raw_config["api"]),
        display=DisplayConfig(**raw_config["display"]),
    )

    return config


def load_message_ids(
    app_store: AppStore,
    config: Config,
    path: str | None = None,
    filename: str | None = None,
) -> tomlkit.TOMLDocument:
    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = app_store.server_identifier

    logger.info(f"Loading message IDs from {Path(path, filename)}")

    message_ids = None
    with open(Path(path, filename), mode="r") as fp:
        message_ids = tomlkit.load(fp)

    logger.info(f"Loaded message IDs={message_ids}")
    return message_ids


def save_message_id(app_store: AppStore, table, key, value):

    message_ids = app_store.message_ids
    message_ids[table][key] = value

    app_store.message_ids = message_ids


def persist_message_ids(
    app_store: AppStore,
    config: Config,
    path: str | None = None,
    filename: str | None = None,
) -> None:
    if config.output.message_id_directory:
        path = config.output.message_id_directory

    if config.output.message_id_filename:
        filename = config.output.message_id_filename

    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = app_store.server_identifier

    with open(Path(path, filename), mode="w") as fp:
        tomlkit.dump(app_store.message_ids, fp)


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

    if not username or not password:
        raise ValueError("Username or password not provided.")

    if response.status_code != requests.codes.ok:
        response.raise_for_status()

    return response.cookies.get(constants.SESSION_ID_COOKIE)


def with_login(func: Callable):
    @wraps(func)
    def inner(app_store: AppStore, config: Config, *args, **kwargs):
        username = config.api.username
        password = config.api.password

        if not app_store.cookies.get("sessionid", None):
            app_store.cookies["sessionid"] = login(config, username, password)

        return func(app_store, config, *args, **kwargs)

    return inner


@with_login
def get_api_result(
    app_store: AppStore,
    config: Config,
    endpoint: str,
    api_prefix: str | None = None,
    base_url: str | None = None,
):

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

    try:
        result["current_map"] = Map(raw_name=result["current_map"])
    except ValueError:
        logger.error(f"Invalid map name received current_map={result['current_map']}")
        raise
    try:
        result["next_map"] = Map(raw_name=result["next_map"])
    except ValueError:
        logger.error(f"Invalid map name received next_map={result['next_map']}")
        raise

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


def guess_current_map_rotation_positions(
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


def guess_next_map_rotation_positions(
    current_map_positions: list[int], rotation: list[Map]
) -> list[int]:
    rotation_length = len(rotation)

    positions: list[int] = []
    for position in current_map_positions:
        # handle wrapping back to the start of the rotation
        if position == rotation_length - 1:
            positions.append(0)
        # otherwise the next map is immediately after the current map
        else:
            positions.append(position + 1)

    return positions


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


def build_header(
    app_store: AppStore, config: Config
) -> tuple[str | None, discord.Embed | None]:
    header_embed = discord.Embed()

    result = get_api_result(app_store, config, endpoint="get_status")
    server_name = parse_server_name(result)

    match config.display.header.server_name:
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
        result = get_api_result(app_store, config, endpoint=endpoint)
        parser = ENDPOINTS_TO_PARSERS[endpoint]
        value = parser(result)
        header_embed.add_field(name=option.name, value=value, inline=option.inline)

    return None, header_embed


def build_gamestate(
    app_store: AppStore, config: Config, endpoint: str = "get_gamestate"
) -> tuple[str | None, discord.Embed | None]:
    gamestate_embed = discord.Embed()

    result = get_api_result(app_store, config, endpoint=endpoint)
    gamestate = parse_gamestate(result)

    if config.display.gamestate.image:
        gamestate_embed.set_image(
            url=get_map_picture_url(config, gamestate["current_map"]).url
        )

    for option in config.display.gamestate.embeds:
        if option.value == "slots":
            result = get_api_result(app_store, config, endpoint="get_slots")
            slots = parse_slots(result)
            value = f"{slots.player_count}/{slots.max_players}"
        elif option.value == constants.EMPTY_EMBED:
            value = option.value
        elif option.value == "score":
            if (
                config.display.gamestate.score_format_ger_us
                and gamestate["current_map"].raw_name in constants.US_MAPS
            ):
                format_str = config.display.gamestate.score_format_ger_us
            elif (
                config.display.gamestate.score_format_ger_rus
                and gamestate["current_map"].raw_name in constants.RUSSIAN_MAPS
            ):
                format_str = config.display.gamestate.score_format_ger_rus
            else:
                format_str = config.display.gamestate.score_format

            value = format_str.format(
                gamestate["allied_score"], gamestate["axis_score"]
            )
        elif option.value in ("current_map", "next_map"):
            value = gamestate[option.value].name
        else:
            value = gamestate[option.value]

        gamestate_embed.add_field(name=option.name, value=value, inline=option.inline)

    return None, gamestate_embed


def build_map_rotation_color(
    app_store: AppStore,
    config: Config,
    endpoint: str = "get_map_rotation",
) -> tuple[str | None, discord.Embed | None]:

    result = get_api_result(app_store, config, endpoint=endpoint)
    map_rotation = parse_map_rotation(result)

    gamestate_result = get_api_result(app_store, config, endpoint="get_gamestate")
    gamestate = parse_gamestate(gamestate_result)
    current_map_positions = guess_current_map_rotation_positions(
        map_rotation, gamestate["current_map"], gamestate["next_map"]
    )

    next_map_positions = guess_next_map_rotation_positions(
        current_map_positions, map_rotation
    )

    logger.debug(f"current map positions color {current_map_positions=}")
    logger.debug(f"next map positions color {next_map_positions}")

    content: list[str] = []

    if config.display.map_rotation.color.display_title:
        content.append(config.display.map_rotation.color.title)

    start_block = "```"
    end_block = "```"
    current_map_color = constants.COLOR_TO_CODE_BLOCK[
        config.display.map_rotation.color.current_map_color
    ]
    next_map_color = constants.COLOR_TO_CODE_BLOCK[
        config.display.map_rotation.color.next_map_color
    ]
    other_map_color = constants.COLOR_TO_CODE_BLOCK[
        config.display.map_rotation.color.other_map_color
    ]

    for idx, map in enumerate(map_rotation):
        if idx in current_map_positions:
            style = current_map_color
        elif idx in next_map_positions:
            style = next_map_color
        # other map color
        else:
            style = other_map_color
        line = start_block + style + "\n" + map.name + "\n" + end_block
        content.append(line)

    if config.display.map_rotation.color.display_legend:
        content.append(config.display.map_rotation.color.legend_title)
        current, next, other = config.display.map_rotation.color.legend

        content.append(start_block + current_map_color + "\n" + current + end_block)
        content.append(start_block + next_map_color + "\n" + next + end_block)
        content.append(start_block + other_map_color + "\n" + other + end_block)

    return "".join(content), None


def build_map_rotation_emoji(
    app_store: AppStore,
    config: Config,
    endpoint: str = "get_map_rotation",
) -> tuple[str | None, discord.Embed | None]:

    result = get_api_result(app_store, config, endpoint=endpoint)
    map_rotation = parse_map_rotation(result)

    gamestate_result = get_api_result(app_store, config, endpoint="get_gamestate")
    gamestate = parse_gamestate(gamestate_result)

    current_map_positions = guess_current_map_rotation_positions(
        map_rotation, gamestate["current_map"], gamestate["next_map"]
    )
    next_map_positions = guess_next_map_rotation_positions(
        current_map_positions, map_rotation
    )

    logger.debug(f"current map positions emoji {current_map_positions=}")
    logger.debug(f"next map positions emoji {next_map_positions}")

    map_rotation_embed = discord.Embed()

    description = []
    for idx, map in enumerate(map_rotation):
        if idx in current_map_positions:
            description.append(
                config.display.map_rotation.emoji.current_map_emoji.format(
                    map.name, idx + 1
                )
            )
        elif idx in next_map_positions:
            description.append(
                config.display.map_rotation.emoji.next_map_emoji.format(
                    map.name, idx + 1
                )
            )
        # other map emoji
        else:
            description.append(
                config.display.map_rotation.emoji.other_map_emoji.format(
                    map.name, idx + 1
                )
            )

    if config.display.map_rotation.emoji.display_legend:
        description.append(config.display.map_rotation.emoji.legend)

    map_rotation_embed.add_field(
        name=config.display.map_rotation.emoji.title, value="\n".join(description)
    )

    return None, map_rotation_embed


def build_default_message_ids(default_value: int = 0) -> tomlkit.TOMLDocument:
    message_ids = tomlkit.document()
    table = tomlkit.table()
    table.add("header", default_value)
    table.add("gamestate", default_value)
    table.add("map_rotation_color", default_value)
    table.add("map_rotation_emoji", default_value)
    message_ids.add("message_ids", table)

    return message_ids


def validate_message_ids_format(
    doc: tomlkit.TOMLDocument, format=constants.MESSAGE_ID_FORMAT
) -> None:
    # TODO include file name for better error messages
    table = doc.get(format["table_name"])

    if format["table_name"] not in doc:
        raise ValueError("Invalid Message IDs")

    for field in format["fields"]:
        if field not in table:
            raise ValueError("Invalid Message IDs")


def handle_webhook(
    type: str,
    webhook: discord.SyncWebhook,
    message_id: int | None = None,
    embed: discord.Embed | None = None,
    content: str | None = None,
) -> int | None:

    if content is None:
        content = ""

    if message_id:
        try:
            logger.info(f"Editing {type} webhook message message ID={message_id}")
            webhook.edit_message(message_id=message_id, content=content, embed=embed)
        except discord.errors.NotFound:
            message_id = None

    if not message_id:
        logger.info(f"Creating new {type} webhook message")
        message = webhook.send(content=content, embed=embed, wait=True)
        message_id = message.id

    return message_id


def get_message_ids(app_store: AppStore, config: Config) -> tomlkit.TOMLDocument:
    try:
        message_ids = load_message_ids(app_store, config)
    except FileNotFoundError:
        message_ids = build_default_message_ids()

    try:
        validate_message_ids_format(message_ids)
    except ValueError:
        message_ids = build_default_message_ids()

    app_store.message_ids = message_ids
    return message_ids


def main():

    configs: list[tuple[AppStore, Config]] = []
    for file_path in Path(constants.CONFIG_DIR).iterdir():
        config = load_config(file_path)
        app_store = AppStore(server_identifier=file_path.name)
        configs.append((app_store, config))

    for app_store, config in configs:
        webhook = discord.SyncWebhook.from_url(config.discord.webhook_url)

        table_name = "message_ids"
        to_process = (
            (config.display.header.enabled, table_name, "header", build_header),
            (
                config.display.gamestate.enabled,
                table_name,
                "gamestate",
                build_gamestate,
            ),
            (
                config.display.map_rotation.color.enabled,
                table_name,
                "map_rotation_color",
                build_map_rotation_color,
            ),
            (
                config.display.map_rotation.color.enabled,
                table_name,
                "map_rotation_emoji",
                build_map_rotation_emoji,
            ),
        )

        for enabled, table, key, func in to_process:
            if enabled:
                message_ids = get_message_ids(app_store, config)
                content, embed = func(app_store, config)
                message_id: int | None = message_ids[table].get(key)
                message_id = handle_webhook(
                    key, webhook, message_id, content=content, embed=embed
                )
                if message_id:
                    save_message_id(app_store, table=table, key=key, value=message_id)

                persist_message_ids(app_store, config)


if __name__ == "__main__":
    main()
