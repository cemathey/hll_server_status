import time
import tomllib
from copy import copy
from functools import partial, wraps
from itertools import cycle
from pathlib import Path
from typing import Any, Callable

import discord
import httpx
import requests
import tomlkit
import trio
from loguru import logger

from hll_server_status import constants
from hll_server_status.models import (
    APIConfig,
    AppStore,
    Config,
    DiscordConfig,
    DisplayConfig,
    LoginParameters,
    MessageIDFormat,
    OutputConfig,
    SettingsConfig,
)
from hll_server_status.utils import (
    build_gamestate,
    build_header,
    build_map_rotation_color,
    build_map_rotation_embed,
)


def calculate_sleep_time(
    start_time_ns: int, end_time_ns: int, refresh_delay_seconds: int
) -> float:
    """Return the difference from the refresh delay and elapsed time"""
    elapsed_time_ns = end_time_ns - start_time_ns
    refresh_delay_ns = refresh_delay_seconds * constants.NS_TO_SECONDS_FACTOR
    time_to_sleep = round(
        (refresh_delay_ns - elapsed_time_ns) / constants.NS_TO_SECONDS_FACTOR, ndigits=0
    )

    if time_to_sleep > 0:
        return time_to_sleep
    else:
        return 1


def get_producer_config_values(config: Config, key: str) -> tuple[bool, int, Callable]:
    """Return the state, refresh delay and appropriate function for a given key (section)"""
    KEYS_TO_CONFIG_LOOKUP = {
        "header": (
            config.display.header.enabled,
            config.display.header.time_between_refreshes,
            build_header,
        ),
        "gamestate": (
            config.display.gamestate.enabled,
            config.display.gamestate.time_between_refreshes,
            build_gamestate,
        ),
        "map_rotation_color": (
            config.display.map_rotation.color.enabled,
            config.display.map_rotation.color.time_between_refreshes,
            build_map_rotation_color,
        ),
        "map_rotation_embed": (
            config.display.map_rotation.embed.enabled,
            config.display.map_rotation.embed.time_between_refreshes,
            build_map_rotation_embed,
        ),
    }
    return KEYS_TO_CONFIG_LOOKUP[key]


async def queue_webhook_update(
    send_channel,
    job_key: str,
    config: Config,
    config_file_path: Path,
    app_store: AppStore,
    table_name: str,
    toml_section_key: str,
) -> None:
    """Queue an update for this sections webhook and then sleep until next update time"""
    refresh_config = False
    kill_task = False

    back_offs = cycle([1, 2, 3, 4, 5])

    # enabled = True
    config_update_timestamp_ns = 0

    # Not using an async webhook since trio and aiohttp are incompatible
    # not a big deal since we're only blocking within each individual
    # Discord message and not preventing any others from updating
    webhook = discord.SyncWebhook.from_url(config.discord.webhook_url)

    # pylance complains about this even though it's valid with tomlkit
    message_id = app_store.message_ids[table_name][toml_section_key]  # type: ignore

    # Get the information for this specific section
    (
        enabled,
        refresh_delay,
        content_embed_creator_func,
    ) = get_producer_config_values(config, toml_section_key)

    app_store.logger.debug(
        f"{enabled=} key={toml_section_key} {job_key=} {content_embed_creator_func=}"
    )

    async with send_channel:
        while True:
            start_time_ns = time.perf_counter_ns()
            if (start_time_ns - config_update_timestamp_ns) > (
                config.settings.time_between_config_file_reads
                * constants.NS_TO_SECONDS_FACTOR
            ):
                refresh_config = True

            # Periodically re-read the config file for changes without need to restart
            # the entire service
            # TODO: watch the file for changes rather than polling?
            if refresh_config:
                refresh_config = False
                try:
                    config_update_timestamp_ns = time.perf_counter_ns()
                    app_store.logger.info(f"Reading config file for {config_file_path}")
                    app_store.logger.debug(
                        f"{enabled=} key={toml_section_key} {job_key=} {content_embed_creator_func=}"
                    )
                    try:
                        config = load_config(config_file_path)
                    except (KeyError, ValueError) as e:
                        app_store.logger.error(
                            f"{e} while loading config from {config_file_path}"
                        )
                        break

                    webhook = discord.SyncWebhook.from_url(config.discord.webhook_url)
                    # pylance complains about this even though it's valid with tomlkit
                    message_id = app_store.message_ids[table_name][toml_section_key]  # type: ignore

                    (
                        enabled,
                        refresh_delay,
                        content_embed_creator_func,
                    ) = get_producer_config_values(config, toml_section_key)

                except Exception as e:
                    app_store.logger.exception(
                        f"Fatal error while trying to read {config_file_path}"
                    )
                    app_store.logger.exception(e)
                    kill_task = True

            if kill_task:
                logger.error(f"Shutting down {job_key} due to a fatal error")
                break

            if not enabled:
                time_to_sleep = config.settings.disabled_section_sleep_timer
                logger.info(
                    f"Section not enabled, sleeping for {time_to_sleep} seconds"
                )
                await trio.sleep(time_to_sleep)
            else:
                try:
                    # pylance complains about this even though it's valid with tomlkit
                    message_id = app_store.message_ids[table_name][toml_section_key]  # type: ignore
                    content, embed = await content_embed_creator_func(
                        app_store, config, get_api_result
                    )
                    await send_channel.send(
                        (
                            app_store,
                            config,
                            webhook,
                            table_name,
                            toml_section_key,
                            message_id,
                            content,
                            embed,
                        )
                    )
                    # This isn't really the amount of time it took for the webhook to update
                    # just to send it over the channel, but sleep the remaining time so we try to
                    # queue another update every `refresh_delay` seconds
                    end_time = time.perf_counter_ns()
                    time_to_sleep = calculate_sleep_time(
                        start_time_ns, end_time, refresh_delay
                    )
                    app_store.logger.debug(
                        f"Sleeping {job_key} for {time_to_sleep} seconds"
                    )
                    await trio.sleep(time_to_sleep)
                except* (
                    httpx.RequestError,
                    httpx.HTTPStatusError,
                    requests.ConnectionError,
                ) as e:
                    # TODO: better backoff system
                    backoff = next(back_offs)
                    logger.error(f"{e} in {job_key} sleeping for {backoff} seconds")
                    await trio.sleep(backoff)


async def send_queued_webhook_update(receive_channel, job_key: str):
    """Retrieve a queued update for this sections webhook, send it to Discord and save the message ID"""
    app_store: AppStore
    config: Config
    webhook: discord.SyncWebhook
    table_name: str
    key: str
    message_id: int | None
    content: str | None = None
    embed: discord.Embed | None = None

    async for app_store, config, webhook, table_name, key, message_id, content, embed in receive_channel:
        try:
            message_id = await send_for_webhook(
                app_store,
                config,
                key,
                webhook,
                message_id,
                content=content,
                embed=embed,
            )
            await save_message_id(
                app_store, table_name=table_name, key=key, message_id=message_id
            )
            # Reduce disk usage by only persisting message IDs if they've changed or haven't been
            # saved yet
            if (
                not app_store.last_saved_message_ids
                or app_store.message_ids != app_store.last_saved_message_ids
            ):
                await save_message_ids_to_disk(app_store, config)
                app_store.last_saved_message_ids = copy(app_store.message_ids)
        except Exception as e:
            # try to save the current message IDs if there's an exception to avoid orphaned
            # messages
            await save_message_id(
                app_store, table_name=table_name, key=key, message_id=message_id
            )
            await save_message_ids_to_disk(app_store, config)
            raise e


def load_config(file_path: Path) -> Config:
    """Load and validate a TOML config file"""
    raw_config: dict[str, Any]

    with open(file_path, mode="rb") as fp:
        raw_config = tomllib.load(fp)

    config = Config(
        settings=SettingsConfig(**raw_config["settings"]),
        output=OutputConfig(**raw_config["output"]),
        discord=DiscordConfig(**raw_config["discord"]),
        api=APIConfig(**raw_config["api"]),
        display=DisplayConfig(**raw_config["display"]),
    )

    return config


async def save_message_id(
    app_store: AppStore, table_name: str, key: str, message_id: int | None
) -> None:
    """Update a webhook message ID in the app_store"""
    if message_id is None:
        message_id = constants.NONE_MESSAGE_ID

    app_store.logger.debug(f"save_message_id({table_name=} {key=} {message_id=})")
    # pylance complains about this even though it's valid with tomlkit
    app_store.message_ids[table_name][key] = message_id  # type: ignore


async def save_message_ids_to_disk(
    app_store: AppStore,
    config: Config,
    path: str | None = None,
    filename: str | None = None,
) -> None:
    """Save the current message IDs for a specific config to disk"""
    if config.output.message_id_directory:
        path = config.output.message_id_directory

    if config.output.message_id_filename:
        filename = config.output.message_id_filename

    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = app_store.server_identifier + ".toml"

    file = Path(path, filename)

    app_store.logger.info(f"Saving message IDs to {file}")
    app_store.logger.debug(f"{app_store.message_ids=}")
    app_store.logger.debug(f"tomlkit.dumps={tomlkit.dumps(app_store.message_ids)}")
    async with await trio.open_file(file, mode="w") as fp:
        toml_string = tomlkit.dumps(app_store.message_ids)
        await fp.write(toml_string)


def validate_message_ids_format(
    app_store: AppStore,
    message_ids: tomlkit.TOMLDocument | None,
    format: MessageIDFormat = constants.MESSAGE_ID_FORMAT,
    default_value: int = constants.NONE_MESSAGE_ID,
) -> tomlkit.TOMLDocument:
    """Validate the structure of saved message IDs and create defaults for missing keys"""
    if message_ids is None:
        app_store.logger.warning(
            f"{app_store.server_identifier} No message IDs passed, creating a new TOML document"
        )
        message_ids = tomlkit.document()

    table_name = format["table_name"]
    table = message_ids.get(table_name)
    if table is None:
        app_store.logger.warning(
            f"{app_store.server_identifier} {table_name=} missing, creating a new table"
        )
        table = tomlkit.table()
        message_ids.add(table_name, table)

    for field in format["fields"]:
        if field not in table:
            app_store.logger.warning(
                f"{app_store.server_identifier} Creating missing {field=} with {default_value=}"
            )

            # pylance complains about this even though it's valid with tomlkit
            message_ids[table_name].add(field, default_value)  # type: ignore
        if field not in constants.MESSAGE_ID_FORMAT["fields"]:
            app_store.logger.error(
                f"{app_store.server_identifier} Unknown field {field} in saved message IDs"
            )

    return message_ids


async def load_message_ids(app_store: AppStore) -> None:
    """Load and validate Discord message IDs from disk if not already saved"""
    if not (message_ids := app_store.message_ids):
        try:
            message_ids = await load_message_ids_from_disk(app_store)
        except FileNotFoundError:
            app_store.logger.warning(
                f"{app_store.server_identifier}.toml message ID file not found."
            )

        message_ids = validate_message_ids_format(app_store, message_ids)
        app_store.message_ids = message_ids


async def load_message_ids_from_disk(
    app_store: AppStore,
    path: str | None = None,
    filename: str | None = None,
) -> tomlkit.TOMLDocument:
    """Read Discord message IDs from disk"""
    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = app_store.server_identifier + ".toml"

    file = trio.Path(path, filename)
    app_store.logger.info(f"Loading Discord message IDs from {file}")
    async with await file.open() as fp:
        # pylance doesn't understand the return type even though it's a string
        contents: str = await fp.read()  # type: ignore

    message_ids = tomlkit.loads(contents)
    app_store.logger.debug(f"Loaded Discord message IDs={message_ids}")
    return message_ids


def with_login(func: Callable):
    """Log in to the CRCON API and save the sessionid cookie if not logged in"""

    @wraps(func)
    async def inner(
        app_store: AppStore,
        config: Config,
        *args,
        **kwargs,
    ):
        username = config.api.username
        password = config.api.password

        # Don't log in if we're already trying to log in from another task for this config file
        # This does not prevent multiple simultaneous log ins to the same CRCON server
        # if multiple config files are using it, but this is okay because they might be using different
        # credentials, it's probably not worth trying to prevent
        if not app_store.cookies.get("sessionid", None) and not app_store.logging_in:
            app_store.logging_in = True
            app_store.cookies["sessionid"] = login(config, username, password)
            app_store.logger.debug(
                f"Logged in with session ID: {app_store.cookies['sessionid']}"
            )

        return await func(app_store, config, *args, **kwargs)

    return inner


def with_retry(func: Callable, retries=10, delay_between_retries=1):
    """Wrapper for functions that call the CRCON API to retry failed API calls"""

    @wraps(func)
    async def inner(app_store: AppStore, *args, **kwargs) -> dict[str, Any]:
        result: dict[str, Any]

        for num in range(1, retries + 1):
            try:
                result = await func(app_store, *args, **kwargs)
                return result
            except (IndexError, ValueError):
                app_store.logger.exception(
                    "Received improperly formatted data from your CRCON Server"
                )
            app_store.logger.error(
                f"Retrying attempt {num}/{retries}, waiting {delay_between_retries} seconds."
            )
            await trio.sleep(delay_between_retries)

        raise RuntimeError(f"{func} failed after {retries} attempts.")

    return inner


def login(
    config: Config,
    username: str,
    password: str,
    endpoint: str = "login",
    api_prefix=constants.API_PREFIX,
) -> str:
    """Log into CRCON and return the sessionid cookie for future requests"""
    if not username or not password:
        raise ValueError("Username or password not provided.")

    params = LoginParameters(username=username, password=password)
    cookie: str | None = None
    url: str = config.api.base_server_url + api_prefix + endpoint

    try:
        # Use a blocking request since nothing else can proceed anyway until we log in
        response = httpx.post(url, json=params.as_dict())
        if response.status_code != 200:
            response.raise_for_status()

        cookie = response.cookies.get(constants.SESSION_ID_COOKIE)
    except httpx.ConnectError as e:
        raise httpx.ConnectError(f"Unable to connect to URL {url}") from e

    # Shouldn't get here, should either get an HTTP 200
    # or handle a httpx.ConnectError
    if cookie is None:
        raise ValueError(
            "Did not receive a valid session ID cookie after logging in to CRCON"
        )

    return cookie


@with_retry
@with_login
async def get_api_result(
    app_store: AppStore,
    config: Config,
    endpoint: str,
    api_prefix: str | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Call the CRCON API endpoint and return the unparsed result"""
    if base_url is None:
        base_url = config.api.base_server_url

    if api_prefix is None:
        api_prefix = constants.API_PREFIX

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=base_url + api_prefix + endpoint, cookies=app_store.cookies
        )

    if response.status_code == 401:
        app_store.logger.error(
            "HTTP 401 (Unathorized) error, attempting to log in again"
        )
        app_store.cookies.pop("sessionid", None)
        app_store.logging_in = False
    elif response.status_code != 200:
        app_store.logger.error(
            f"HTTP {response.status_code} for {endpoint=} for {app_store.server_identifier} {response.content=} {response.text=}"
        )
        response.raise_for_status()

    result = response.json()["result"]

    if result is None:
        app_store.logger.error(
            f"Received an empty response from {endpoint} {response.text=}"
        )
        raise httpx.ConnectError(
            f"Received an empty response from {endpoint} {response.text=}"
        )

    # for typing purposes, wrap any plain results into a dict
    if isinstance(result, str) or isinstance(result, int) or isinstance(result, list):
        result = {"result": result}

    return result


async def send_for_webhook(
    app_store: AppStore,
    config: Config,
    key: str,
    webhook: discord.SyncWebhook,
    message_id: int | None = None,
    embed: discord.Embed | None = None,
    content: str | None = None,
) -> int | None:
    """Send the content/embed for a given webhook and return the message ID"""
    if content is None:
        content = ""

    if message_id:
        log_message = f"Editing {key} message ID={message_id}"
        func = partial(
            webhook.edit_message, message_id=message_id, content=content, embed=embed
        )
    else:
        log_message = f"Creating new {key} Discord message"
        if embed:
            func = partial(webhook.send, content=content, embed=embed, wait=True)
        else:
            func = partial(webhook.send, content=content, wait=True)

    try:
        app_store.logger.info(log_message)
        message_id = func().id
    except discord.errors.NotFound:
        app_store.logger.warning(
            f"Tried to edit non-existent {key} message ID={message_id}"
        )
        message_id = None
    except discord.errors.RateLimited as e:
        app_store.logger.warning(
            f"This message was rate limited by Discord retrying after {e.retry_after:.2f} seconds"
        )
        await trio.sleep(e.retry_after)
    except requests.exceptions.ConnectionError:
        app_store.logger.error(f"Connection error with url={webhook.url}")
        await trio.sleep(config.settings.disabled_section_sleep_timer)

    return message_id
