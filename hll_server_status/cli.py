import logging.config
from copy import deepcopy
from pathlib import Path

import httpx
import trio
from loguru import logger

from hll_server_status import constants
from hll_server_status.io import (
    load_config,
    queue_webhook_update,
    send_queued_webhook_update,
)
from hll_server_status.types import AppStore

# Disable logging so discord_webhook doesn't log for us
logging.config.dictConfig(
    {
        "version": 1,
        # Other configs ...
        "disable_existing_loggers": True,
    }
)


async def main():
    """Load all the config files and create async tasks for each section in each config file"""

    # Remove existing loguru sinks so it's copyable
    # https://loguru.readthedocs.io/en/stable/resources/recipes.html#creating-independent-loggers-with-separate-set-of-handlers
    logger.remove()
    default_logger = deepcopy(logger)
    default_logger.add(
        f"{constants.LOG_DIR}/{'hll_server_status'}.{constants.LOG_EXTENSION}",
        format=constants.LOG_FORMAT,
        rotation=constants.LOG_SIZE,
    )

    config_files: list[tuple[AppStore, Path]] = []
    for config_file_path in Path(constants.CONFIG_DIR).iterdir():
        # Give each config file its own log file
        _logger = deepcopy(logger)
        _logger.add(
            f"{constants.LOG_DIR}/{config_file_path.stem}.{constants.LOG_EXTENSION}",
            format=constants.LOG_FORMAT,
            rotation=constants.LOG_SIZE,
            retention=constants.LOG_RETENTION_DAYS,
        )
        app_store = AppStore(
            server_identifier=config_file_path.stem, logger=_logger, client=None
        )

        config_files.append((app_store, config_file_path))

    if not config_files:
        default_logger.error(
            f"No config files found, add one or more to {constants.LOG_DIR} "
        )

    section_keys = (
        "player_stats",
        "map_rotation",
        "gamestate",
        "header",
    )
    # Use a 0 size buffer so we never queue another attempt until the previous one has been
    # received since these are all snap shots and producing faster than we can consume is
    # negative value
    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.open_nursery() as nursery:
        async with send_channel, receive_channel:
            for idx, (app_store, config_file_path) in enumerate(config_files):
                default_logger.info(
                    f"Starting {config_file_path} check log files for further output"
                )
                print(f"Starting {config_file_path} check log files for further output")

                app_store.logger.info(
                    f"Reading config file for {idx=} {config_file_path}"
                )
                try:
                    config = load_config(app_store, config_file_path)
                except (KeyError, ValueError) as e:
                    app_store.logger.error(
                        f"{e} while loading config from {config_file_path}"
                    )
                    continue

                app_store.client = httpx.AsyncClient(
                    headers={
                        constants.AUTH_HEADER: constants.API_KEY_FORMAT.format(
                            api_key=config.api.api_key
                        )
                    }
                )

                logger.info(f"Testing a connection to {config.api.base_server_url}")
                try:
                    await app_store.client.get(str(config.api.base_server_url))
                except httpx.ConnectError as e:
                    app_store.logger.error(
                        f"Unable to connect to {config.api.base_server_url} for {config_file_path}"
                    )

                for section_key in section_keys:
                    job_key = f"{app_store.server_identifier}:{section_key}"

                    # Create a unique queue for each section in each config file so they can all update
                    # independently of each other
                    send_channel_clone = send_channel.clone()
                    receive_channel_clone = receive_channel.clone()

                    nursery.start_soon(
                        queue_webhook_update,
                        send_channel_clone,
                        job_key,
                        config,
                        config_file_path,
                        app_store,
                        section_key,
                    )
                    nursery.start_soon(
                        send_queued_webhook_update, receive_channel_clone
                    )


if __name__ == "__main__":
    trio.run(main)

# TODO: Update README
# TODO: test/finish map voting sections

# Future
# TODO: add score sections
# TODO: add map vote info
