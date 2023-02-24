import time
import tomllib
from copy import copy
from functools import partial, wraps
from pathlib import Path
from typing import Any, Callable

import trio
from pprint import pprint
import discord
import tomlkit
import httpx

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
)

GLOBAL_NURSERY_STORAGE: dict[str, trio.CancelScope] = {}


def load_config(path: Path) -> Config:
    """Load and validate a TOML config file"""
    raw_config: dict[str, Any]
    with open(path, mode="rb") as fp:
        raw_config = tomllib.load(fp)

    config = Config(
        output=OutputConfig(**raw_config["output"]),
        discord=DiscordConfig(**raw_config["discord"]),
        api=APIConfig(**raw_config["api"]),
        display=DisplayConfig(**raw_config["display"]),
    )

    return config


async def save_message_id(
    app_store: AppStore, table_name: str, key: str, message_id: int
) -> None:
    """Update a webhook message ID in the app_store"""
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

    async with await trio.open_file(file, mode="w") as fp:
        # async with trio.open(file, mode="w") as fp:
        toml = tomlkit.dumps(app_store.message_ids)
        await fp.write(toml)


def validate_message_ids_format(
    app_store: AppStore,
    message_ids: tomlkit.TOMLDocument | None,
    format: MessageIDFormat = constants.MESSAGE_ID_FORMAT,
    default_value: int = constants.NONE_MESSAGE_ID,
) -> tomlkit.TOMLDocument:
    """Validate the structure of saved message IDs and create defaults for missing keys"""
    # TODO include file name for better error messages

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


async def get_message_ids(app_store: AppStore, config: Config) -> tomlkit.TOMLDocument:
    if not (message_ids := app_store.message_ids):
        try:
            message_ids = await load_message_ids_from_disk(app_store)
        except FileNotFoundError:
            app_store.logger.warning(
                f"{app_store.server_identifier}.toml config file not found."
            )

        message_ids = validate_message_ids_format(app_store, message_ids)
        app_store.message_ids = message_ids
    return message_ids


async def load_message_ids_from_disk(
    app_store: AppStore,
    path: str | None = None,
    filename: str | None = None,
) -> tomlkit.TOMLDocument:
    if not path:
        path = constants.MESSAGES_DIR

    if not filename:
        filename = app_store.server_identifier + ".toml"

    file = trio.Path(path, filename)
    app_store.logger.info(f"Loading message IDs from {file}")
    async with await file.open() as fp:
        contents = await fp.read()

    message_ids = tomlkit.loads(contents)
    app_store.logger.info(f"Loaded message IDs={message_ids}")
    return message_ids


def with_login(func: Callable):
    """Wrap functions that call the CRCON API and save the sessionid cookie"""

    @wraps(func)
    async def inner(
        app_store: AppStore,
        config: Config,
        *args,
        **kwargs,
    ):
        username = config.api.username
        password = config.api.password

        if not app_store.cookies.get("sessionid", None) and not app_store.logging_in:
            app_store.logging_in = True
            app_store.cookies["sessionid"] = login(config, username, password)
            app_store.logger.info(
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
                # if result.status_code == 401:
                #     app_store.logger.error(
                #         "HTTP 401 (Unathorized) error, attempting to log in again"
                #     )
                #     app_store.cookies.pop("sessionid", None)
                #     app_store.logging_in = False
                # else:
                #     app_store.logger.error(
                #         f"HTTP {result.status_code} error when making API call to CRCON attempt"
                #     )

            except IndexError:
                app_store.logger.error(
                    "Received an invalid response from your CRCON Server"
                )
            except ValueError:
                # logged in #get_api_result
                pass
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

    # Use a blocking response since nothing else can proceed anyway until we log in
    response = httpx.post(
        config.api.base_server_url + api_prefix + endpoint, json=params.as_dict()
    )
    if response.status_code != 200:
        response.raise_for_status()

    cookie = response.cookies.get(constants.SESSION_ID_COOKIE)

    # Shouldn't get here if we got an HTTP 200
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

    if response.status_code != 200:
        app_store.logger.error(
            f"HTTP {response.status_code} for {endpoint=} for {app_store.server_identifier} {response.content=} {response.text=}"
        )
        response.raise_for_status()

    result = response.json()["result"]

    if result is None:
        app_store.logger.error(
            f"Received a None response from {endpoint} {response.text=}"
        )
        raise ValueError(f"Received a None response from {endpoint} {response.text=}")

    # for typing purposes, wrap any plain results into a dict
    if isinstance(result, str) or isinstance(result, int) or isinstance(result, list):
        result = {"result": result}

    return result


async def send_for_webhook(
    app_store: AppStore,
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
        log_message = f"Creating new {key} webhook message"
        if embed:
            func = partial(webhook.send, content=content, embed=embed, wait=True)
        else:
            func = partial(webhook.send, content=content, wait=True)

    try:
        app_store.logger.info(log_message)
        message = func()
        message_id = message.id
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

    return message_id


async def update_hook_for_section(
    app_store: AppStore,
    config: Config,
    webhook: discord.SyncWebhook,
    table_name: str,
    key: str,
    message_id: int | None,
    refresh_delay: int,
    content_embed_creator_func: Callable,
    nursery: trio.Nursery,
    task_status=trio.TASK_STATUS_IGNORED,
) -> None:
    """Infinitely update/sleep between refreshes for a specific section"""
    kill_task = False
    retries = 10
    back_offs = list(reversed([1, 2, 3, 3, 3, 3, 3, 3, 3, 3]))

    with trio.CancelScope() as scope:
        task_status.started(scope)
        while True:
            try:
                start_time = time.perf_counter_ns()
                print(f"Creating content")
                content, embed = await content_embed_creator_func(app_store, config)
                print(f"Sending for webhook")
                message_id = await send_for_webhook(
                    app_store, key, webhook, message_id, content=content, embed=embed
                )

                if message_id:
                    print(f"Saving message ID")
                    await save_message_id(
                        app_store, table_name=table_name, key=key, message_id=message_id
                    )

                # Reduce disk usage by only persisting message IDs if they've changed or haven't been
                # saved yet
                if (
                    not app_store.last_saved_message_ids
                    or app_store.message_ids != app_store.last_saved_message_ids
                ):
                    print("Persisting message IDs")
                    await save_message_ids_to_disk(app_store, config)
                    app_store.last_saved_message_ids = copy(app_store.message_ids)

                end_time = time.perf_counter_ns()
                elapsed_time_ns = end_time - start_time
                factor = 1_000_000_000
                refresh_delay_ns = refresh_delay * factor
                time_to_sleep = round(
                    (refresh_delay_ns - elapsed_time_ns) / factor, ndigits=0
                )
                print(
                    f"Sleeping in update_hook_for_section {app_store.server_identifier} {key}"
                )
                app_store.logger.info(
                    f"Sleeping {app_store.server_identifier}.{key} for {time_to_sleep} seconds"
                )
                await trio.sleep(time_to_sleep)
            except httpx.ConnectError as e:
                if retries == 0:
                    print(f"Cancellening {app_store.server_identifier}:{key}")
                    scope.cancel()
                print(
                    f"Error {e} in {app_store.server_identifier}:{key} attempt #{10-retries} sleeping for {back_offs[retries-1]} seconds"
                )
                retries -= 1
                await trio.sleep(back_offs[retries - 1])
