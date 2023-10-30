import logging.config
from copy import deepcopy
from pathlib import Path

import trio
from loguru import logger

from hll_server_status import constants
from hll_server_status.io import (
    load_config,
    load_message_ids,
    queue_webhook_update,
    send_queued_webhook_update,
)
from hll_server_status.models import AppStore

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
        )
        app_store = AppStore(
            server_identifier=config_file_path.stem,
            logger=_logger,
            last_saved_message_ids=None,
        )
        await load_message_ids(app_store)
        config_files.append((app_store, config_file_path))

    if not config_files:
        default_logger.error(
            f"No config files found, add one or more to {constants.LOG_DIR} "
        )

    toml_section_keys = (
        "header",
        "gamestate",
        "map_rotation_color",
        "map_rotation_embed",
    )
    table_name = constants.MESSAGE_ID_FORMAT["table_name"]

    # Use a 0 size buffer so we never queue another attempt until the previous one has been
    # received since these are all snap shots and producing faster than we can consume is
    # negative value
    send_channel, receive_channel = trio.open_memory_channel(0)
    async with trio.open_nursery() as nursery:
        async with send_channel, receive_channel:
            for app_store, config_file_path in config_files:
                default_logger.info(
                    f"Starting {config_file_path} check log files for further output"
                )
                print(f"Starting {config_file_path} check log files for further output")

                app_store.logger.info(f"Reading config file for {config_file_path}")
                try:
                    config = load_config(config_file_path)
                except (KeyError, ValueError) as e:
                    app_store.logger.error(
                        f"{e} while loading config from {config_file_path}"
                    )
                    continue

                for section_key in toml_section_keys:
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
                        table_name,
                        section_key,
                    )
                    nursery.start_soon(
                        send_queued_webhook_update, receive_channel_clone, job_key
                    )


if __name__ == "__main__":
    trio.run(main)

# TODO: Update README
# TODO: test/finish map voting sections

# Future
# TODO: add score sections
# TODO: add map vote info
