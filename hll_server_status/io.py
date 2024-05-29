import json
import time
from functools import wraps
from itertools import cycle
from pathlib import Path
from typing import Any, Callable

import discord_webhook
import httpx
import pydantic
import trio
import yaml

from hll_server_status import constants, models
from hll_server_status.exceptions import RateLimited
from hll_server_status.models import enter_session, get_set_wh_row
from hll_server_status.types import (
    APIConfig,
    AppStore,
    Config,
    DiscordConfig,
    DisplayConfig,
    SettingsConfig,
)
from hll_server_status.utils import (
    build_gamestate,
    build_header,
    build_map_rotation,
    build_player_stats_embed,
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
    KEYS_TO_CONFIG_LOOKUP: dict[str, tuple[bool, int, Callable]] = {
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
        "map_rotation": (
            config.display.map_rotation.enabled,
            config.display.map_rotation.time_between_refreshes,
            build_map_rotation,
        ),
        "player_stats": (
            config.display.player_stats.enabled,
            config.display.player_stats.time_between_refreshes,
            build_player_stats_embed,
        ),
    }
    return KEYS_TO_CONFIG_LOOKUP[key]


async def queue_webhook_update(
    send_channel,
    job_key: str,
    config: Config,
    config_file_path: Path,
    app_store: AppStore,
    key: str,
) -> None:
    """Queue an update for this sections webhook and then sleep until next update time"""
    refresh_config = False
    kill_task = False

    back_offs = cycle([1, 2, 3, 4, 5])

    # enabled = True
    config_update_timestamp_ns = 0
    webhook_url = config.discord.webhook_url

    # Get the information for this specific section
    (
        enabled,
        refresh_delay,
        content_embed_creator_func,
    ) = get_producer_config_values(config, key)

    app_store.logger.debug(
        f"{enabled=} {key=} {job_key=} {content_embed_creator_func=}"
    )

    first_run = True
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
            if refresh_config and not first_run:
                refresh_config = False
                first_run = False
                try:
                    config_update_timestamp_ns = time.perf_counter_ns()
                    app_store.logger.info(f"Reading config file for {config_file_path}")
                    app_store.logger.debug(
                        f"{enabled=} key={key} {job_key=} {content_embed_creator_func=}"
                    )
                    try:
                        config = load_config(app_store, config_file_path)
                    except (KeyError, ValueError) as e:
                        app_store.logger.error(
                            f"{e} while loading config from {config_file_path}"
                        )
                        break

                    (
                        enabled,
                        refresh_delay,
                        content_embed_creator_func,
                    ) = get_producer_config_values(config, key)

                except Exception as e:
                    app_store.logger.exception(
                        f"Fatal error while trying to read {config_file_path}"
                    )
                    app_store.logger.exception(e)
                    kill_task = True

            if kill_task:
                app_store.logger.error(f"Shutting down {job_key} due to a fatal error")
                break

            if not enabled:
                time_to_sleep = config.settings.disabled_section_sleep_timer
                app_store.logger.info(
                    f"Section not enabled, sleeping for {time_to_sleep} seconds"
                )
                await trio.sleep(time_to_sleep)
            else:
                with enter_session(config.name) as session:
                    message_ids = get_set_wh_row(
                        session=session, webhook_url=str(webhook_url)
                    )
                    message_id = message_ids[key]
                try:
                    content, embed = await content_embed_creator_func(
                        app_store, config, get_api_result
                    )
                    await send_channel.send(
                        (
                            app_store,
                            config,
                            webhook_url,
                            key,
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
                ) as e:
                    # TODO: better backoff system

                    backoff = next(back_offs)
                    app_store.logger.error(
                        f"{e.exceptions} in {job_key} sleeping for {backoff} seconds"
                    )
                    await trio.sleep(backoff)


async def send_queued_webhook_update(receive_channel):
    """Retrieve a queued update for this sections webhook, send it to Discord and save the message ID"""
    app_store: AppStore
    config: Config
    webhook_url: pydantic.HttpUrl
    key: str
    message_id: int | None
    content: str | None = None
    embed: discord_webhook.DiscordEmbed | None = None

    async for (
        app_store,
        config,
        webhook_url,
        key,
        message_id,
        content,
        embed,
    ) in receive_channel:
        message_id = await send_for_webhook(
            app_store,
            config,
            key,
            webhook_url,
            message_id,
            content=content,
            embed=embed,
        )
        app_store.logger.debug(f"Received {message_id=} from send_for_webhook {key=}")

        if message_id is None:
            message_id = constants.NONE_MESSAGE_ID

        models.save_message_ids_by_key(
            config.name, webhook_url=str(webhook_url), key=key, value=message_id
        )


def load_config(app_store: AppStore, file_path: Path) -> Config:
    """Load and validate a yaml config file"""
    raw_config: dict[str, Any]

    with open(file_path, mode="rb") as fp:
        raw_config = yaml.safe_load(fp)

    name = file_path.stem
    models.init_engine(name)

    key = "settings"
    try:
        settings_config = SettingsConfig(**raw_config[key])
    except pydantic.ValidationError:
        app_store.logger.error(f"validating {file_path}, check your [{key}] section")
        raise

    key = "discord"
    try:
        discord_config = DiscordConfig(**raw_config[key])
    except pydantic.ValidationError:
        app_store.logger.error(f"validating {file_path}, check your [{key}] section")
        raise

    key = "api"
    try:
        api_config = APIConfig(**raw_config[key])
    except pydantic.ValidationError:
        app_store.logger.error(f"validating {file_path}, check your [{key}] section")
        raise

    key = "display"
    try:
        display_config = DisplayConfig(**raw_config[key])
    except pydantic.ValidationError:
        app_store.logger.error(f"validating {file_path}, check your [{key}] section")
        raise

    config = Config(
        name=name,
        settings=settings_config,
        discord=discord_config,
        api=api_config,
        display=display_config,
    )

    return config


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


@with_retry
async def get_api_result(
    app_store: AppStore,
    config: Config,
    endpoint: str,
    api_prefix: str | None = None,
    base_url: pydantic.HttpUrl | None = None,
) -> dict[str, Any]:
    """Call the CRCON API endpoint and return the unparsed result"""
    if base_url is None:
        base_url = config.api.base_server_url

    if api_prefix is None:
        api_prefix = constants.API_PREFIX

    if app_store.client is None:
        raise ValueError(f"{app_store.client=}")

    response = await app_store.client.get(url=str(base_url) + api_prefix + endpoint)

    if response.status_code == 401:
        app_store.logger.error("HTTP 401 (Unathorized) error, check your API key")
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
    webhook_url: pydantic.HttpUrl,
    message_id: int | None = None,
    embed: discord_webhook.DiscordEmbed | None = None,
    content: str | None = None,
) -> int | None:
    """Send the content/embed for a given webhook and return the message ID"""
    if content is None:
        content = ""

    webhook = discord_webhook.AsyncDiscordWebhook(
        url=str(webhook_url), with_retry=False, id=str(message_id)
    )

    app_store.logger.debug(f"Created webhook id={webhook.id} for {key=}")

    if message_id:
        log_message = f"Editing {key} {message_id=}"
        webhook.content = content
        if embed and embed not in webhook.embeds:
            webhook.add_embed(embed)
    else:
        log_message = f"Creating new {key} Discord message {message_id=}"
        webhook.content = content
        if embed and embed not in webhook.embeds:
            webhook.add_embed(embed)

    try:
        app_store.logger.debug(f"send_for_webhook {message_id=}")
        if message_id:
            response = await webhook.edit()
        else:
            response = await webhook.execute()
        app_store.logger.debug(f"executed webhook={webhook.id}")
        if webhook.id:
            message_id = int(webhook.id)
        if response.status_code == 404:
            app_store.logger.error(f"404")
            response.raise_for_status()
        elif response.status_code == 429:
            errors = json.loads(response.content.decode("utf-8"))
            retry_after = float(errors["retry_after"]) + 0.15
            raise RateLimited(retry_after=retry_after)
        app_store.logger.info(log_message)
    except RateLimited as e:
        app_store.logger.warning(
            f"{message_id=} was rate limited by Discord retrying after {e.retry_after:.2f} seconds"
        )
        await trio.sleep(e.retry_after)
    except httpx.ConnectError:
        app_store.logger.error(f"Connection error with url={webhook.url}")
        await trio.sleep(config.settings.disabled_section_sleep_timer)
    except httpx.HTTPError:
        app_store.logger.warning(
            f"Tried to edit non-existent {key} message ID={message_id}"
        )
        message_id = None

    return message_id
