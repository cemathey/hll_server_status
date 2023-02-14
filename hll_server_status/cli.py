import asyncio
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable

import aiohttp
import discord

from hll_server_status import constants
from hll_server_status.io import get_message_ids, load_config, update_hook_for_section
from hll_server_status.models import AppStore, Config
from hll_server_status.utils import (
    bootstrap,
    build_gamestate,
    build_header,
    build_map_rotation_color,
    build_map_rotation_embed,
)


async def main():
    """Load all the config files and create asyncio tasks"""
    formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

    root_logger = logging.getLogger(constants.ROOT_LOGGER_NAME)
    root_logger.setLevel(os.getenv("LOGGING_LEVEL", logging.INFO))
    file_handler = RotatingFileHandler(
        filename=Path(
            constants.LOG_DIR, constants.ROOT_LOGGER_NAME + constants.LOG_EXTENSION
        ),
        maxBytes=constants.LOG_SIZE_BYTES,
        backupCount=constants.LOG_COUNT,
    )
    console_handler = logging.StreamHandler(stream=sys.stderr)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    bootstrap(root_logger)
    servers: list[tuple[AppStore, Config]] = []
    for file_path in Path(constants.CONFIG_DIR).iterdir():
        root_logger.info(f"Reading config file for {file_path}")
        logger = logging.getLogger(file_path.stem)
        logger.setLevel(os.getenv("LOGGING_LEVEL", logging.INFO))
        handler = RotatingFileHandler(
            filename=Path(constants.LOG_DIR, file_path.stem + constants.LOG_EXTENSION),
            maxBytes=constants.LOG_SIZE_BYTES,
            backupCount=constants.LOG_COUNT,
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        config = load_config(file_path)
        app_store = AppStore(
            server_identifier=file_path.stem, logger=logger, last_saved_message_ids=None
        )
        servers.append((app_store, config))

    if not servers:
        root_logger.error(
            f"No config files found, add one or more to {constants.LOG_DIR} "
        )

    async with aiohttp.ClientSession() as session:
        server_sections = []
        for app_store, config in servers:
            webhook = discord.Webhook.from_url(
                config.discord.webhook_url, session=session
            )
            message_ids = await get_message_ids(app_store, config)
            table_name = constants.MESSAGE_ID_FORMAT["table_name"]

            sections: list[
                tuple[
                    AppStore,
                    Config,
                    discord.Webhook,
                    aiohttp.ClientSession,
                    str,  # TOML message IDs table_name
                    str,  # TOML message ID key (i.e. gamestate)
                    int,  # saved Discord message ID
                    int,  # refresh delay (seconds)
                    Callable,
                ]
            ] = []

            callables = (
                build_header,
                build_gamestate,
                build_map_rotation_color,
                build_map_rotation_embed,
            )
            keys = ("header", "gamestate", "map_rotation_color", "map_rotation_embed")
            enableds = (
                config.display.header.enabled,
                config.display.gamestate.enabled,
                config.display.map_rotation.color.enabled,
                config.display.map_rotation.embed.enabled,
            )
            refresh_delays = (
                config.display.header.time_between_refreshes,
                config.display.gamestate.time_between_refreshes,
                config.display.map_rotation.color.time_between_refreshes,
                config.display.map_rotation.embed.time_between_refreshes,
            )

            for enabled, key, refresh_delay, callable in zip(
                enableds, keys, refresh_delays, callables
            ):
                if enabled:
                    sections.append(
                        (
                            app_store,
                            config,
                            webhook,
                            session,
                            table_name,
                            key,
                            # pylance complains about this even though it's valid with tomlkit
                            message_ids[table_name][key],  # type: ignore
                            refresh_delay,
                            callable,
                        )
                    )

            server_sections.append(sections)

        async with asyncio.taskgroups.TaskGroup() as tg:
            for server_section in server_sections:
                for section in server_section:
                    (
                        app_store,
                        config,
                        webhook,
                        session,
                        table_name,
                        key,
                        message_id,
                        refresh_delay,
                        func,
                    ) = section
                    root_logger.info(
                        f"Starting {app_store.server_identifier}:{key} check log files for further output"
                    )
                    tg.create_task(
                        update_hook_for_section(
                            app_store=app_store,
                            config=config,
                            webhook=webhook,
                            session=session,
                            table_name=table_name,
                            key=key,
                            message_id=message_id,
                            refresh_delay=refresh_delay,
                            content_embed_creator_func=func,
                        )
                    )


if __name__ == "__main__":
    asyncio.run(main())

# TODO: Update README
# TODO: test/finish map voting sections
# TODO: break functions out into modules

# Future
# TODO: add score sections
