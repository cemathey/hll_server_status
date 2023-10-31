import json
import re
from dataclasses import dataclass, field
from datetime import timedelta
from itertools import zip_longest
from typing import NotRequired, TypedDict

import httpx
import loguru
import pydantic
import tomlkit

from hll_server_status import constants


class MessageIDFormat(TypedDict):
    table_name: str
    fields: list[str]


class ServerName(pydantic.BaseModel):
    """Represents the server name from /api/get_status"""

    name: str
    short_name: str


class Map(pydantic.BaseModel):
    """Represents a RCON map name such as foy_offensive_ger"""

    raw_name: str

    @pydantic.validator("raw_name")
    def must_be_valid_map_name(cls, v):
        map_change_pattern = r"Untitled_\d+"

        if re.match(map_change_pattern, v):
            return constants.BETWEEN_MATCHES_MAP_NAME

        restart_maps = [
            map_name + suffix
            for map_name, suffix in zip_longest(
                constants.ALL_MAPS, [], fillvalue=constants.MAP_RESTART_SUFFIX
            )
        ]

        if v in restart_maps:
            v = v.replace("_RESTART", "")

        if v not in constants.ALL_MAPS:
            # Most likely an update has dropped and a new map exists
            v = v.split("_", 1)[0]
            if v == "":
                v = "Unknown Map"

        return v

    @property
    def name(self):
        try:
            _name = constants.LONG_HUMAN_MAP_NAMES[self.raw_name]
        except KeyError:
            # Most likely an update has dropped and a new map exists
            _name = self.raw_name

        return _name

    def __repr__(self) -> str:
        return f"{self.__class__}({self.name=} {self.raw_name=})"


class GameState(TypedDict):
    """Response from api/get_gamestate"""

    num_allied_players: int
    num_axis_players: int
    allied_score: int
    axis_score: int
    raw_time_remaining: str
    time_remaining: timedelta
    current_map: Map
    next_map: Map


class Slots(pydantic.BaseModel):
    """Response from api/get_slots"""

    player_count: int
    max_players: int


class PlayerStatsCrconType(TypedDict):
    player: str
    steam_id_64: str

    kills: int
    kills_streak: int
    deaths: int
    deaths_without_kill_streak: int
    teamkills: int
    teamkills_streak: int
    deaths_by_tk: int
    deaths_by_tk_streak: int
    longest_life_secs: int
    shortest_life_secs: int

    weapons: dict[str, int]
    death_by_weapons: dict[str, int]
    most_killed: dict[str, int]
    death_by: dict[str, int]

    combat: int
    offense: int
    defense: int
    support: int

    kills_per_minute: float
    deaths_per_minute: float
    kill_death_ratio: float


class PlayerStats(pydantic.BaseModel):
    player: str
    steam_id_64: str

    kills: int
    kill_streak: int
    deaths: int
    death_streak: int
    teamkills: int
    teamkills_streak: int
    deaths_by_tk: int
    deaths_by_tk_streak: int
    longest_life_secs: int
    shortest_life_secs: int

    kills_by_weapons: dict[str, int]
    deaths_by_weapons: dict[str, int]
    most_killed_players: dict[str, int]
    death_by_players: dict[str, int]

    combat: int
    offense: int
    defense: int
    support: int

    kills_per_minute_: float
    deaths_per_minute_: float
    kill_death_ratio_: float

    @property
    def kills_per_minute(self) -> float:
        return round(self.kills_per_minute_, 1)

    @property
    def deaths_per_minute(self) -> float:
        return round(self.deaths_per_minute_, 1)

    @property
    def kill_death_ratio(self) -> float:
        return round(self.kill_death_ratio_, 1)


class LoginParameters(pydantic.BaseModel):
    """Body for api/login"""

    username: str
    password: str

    def as_dict(self) -> dict[str, str]:
        return {"username": self.username, "password": self.password}

    def as_json(self):
        return json.dumps(self.as_dict())


class Cookies(TypedDict):
    sessionid: NotRequired[httpx.Cookies]


def default_cookies() -> Cookies:
    return {}


@dataclass
class AppStore:
    server_identifier: str
    logger: "loguru.Logger"
    last_saved_message_ids: tomlkit.TOMLDocument | None
    logging_in: bool = field(default_factory=lambda: False)
    message_ids: tomlkit.TOMLDocument = field(default_factory=tomlkit.TOMLDocument)
    cookies: dict[str, str] = field(default_factory=dict)


class URL(pydantic.BaseModel):
    url: pydantic.HttpUrl


class SettingsConfig(pydantic.BaseModel):
    # pylance complains about this even though it's valid with pydantic
    time_between_config_file_reads: pydantic.conint(ge=1)  # type: ignore
    disabled_section_sleep_timer: pydantic.conint(ge=1)  # type: ignore


class OutputConfig(pydantic.BaseModel):
    message_id_directory: str | None
    message_id_filename: str | None


class DiscordConfig(pydantic.BaseModel):
    webhook_url: pydantic.HttpUrl


class APIConfig(pydantic.BaseModel):
    base_server_url: str
    username: str
    password: str

    @pydantic.validator("base_server_url")
    def must_include_trailing_slash(cls, value: str):
        if not value.endswith("/"):
            return value + "/"

        return value


class DisplayEmbedConfig(pydantic.BaseModel):
    name: str
    value: str
    inline: bool

    @pydantic.validator("value")
    def must_be_valid_embed(cls, v):
        if v not in constants.DISPLAY_EMBEDS:
            raise ValueError(f"Invalid [[display.header]] embed {v}")

        return v


class GamestateEmbedConfig(pydantic.BaseModel):
    name: str
    value: str
    inline: bool

    @pydantic.validator("value")
    def must_be_valid_embed(cls, v):
        if v not in constants.GAMESTATE_EMBEDS:
            raise ValueError(f"Invalid [[display.gamestate]] embed {v}")

        return v


class DisplayFooterConfig(pydantic.BaseModel):
    enabled: bool
    footer_text: str | None
    include_timestamp: bool
    last_refresh_text: str | None


class DisplayHeaderConfig(pydantic.BaseModel):
    enabled: bool
    # pylance complains about this even though it's valid with pydantic
    time_between_refreshes: pydantic.conint(ge=1)  # type: ignore
    server_name: str
    quick_connect_name: str
    quick_connect_url: pydantic.AnyUrl | None
    battlemetrics_name: str
    battlemetrics_url: pydantic.HttpUrl | None
    embeds: list[DisplayEmbedConfig] | None
    footer: DisplayFooterConfig

    @pydantic.validator("server_name")
    def must_be_valid_name(cls, v):
        if v not in constants.DISPLAY_NAMES:
            raise ValueError(f"Invalid [[display.header]] name={v}")

        return v

    @pydantic.validator("quick_connect_url", "battlemetrics_url", pre=True)
    def allow_empty_urls(cls, v):
        # Can't set None/null values in TOML but we want to support empty URL strings
        if v == "":
            return None
        else:
            return v


class DisplayGamestateConfig(pydantic.BaseModel):
    enabled: bool
    # pylance complains about this even though it's valid with pydantic
    time_between_refreshes: pydantic.conint(ge=1)  # type: ignore
    image: bool
    score_format: str
    score_format_ger_us: str | None
    score_format_ger_rus: str | None
    score_format_ger_uk: str | None
    footer: DisplayFooterConfig
    embeds: list[GamestateEmbedConfig]


class DisplayMapRotationColorConfig(pydantic.BaseModel):
    enabled: bool
    # pylance complains about this even though it's valid with pydantic
    time_between_refreshes: pydantic.conint(ge=1)  # type: ignore
    display_title: bool
    title: str
    current_map_color: str
    next_map_color: str
    other_map_color: str
    display_legend: bool
    legend_title: str
    legend: list[str]
    display_last_refreshed: bool
    last_refresh_text: str

    @pydantic.field_validator("current_map_color", "next_map_color", "other_map_color")
    def must_be_valid_current_map_color(cls, v, field):
        if v not in constants.COLOR_TO_CODE_BLOCK.keys():
            raise ValueError(f"Invalid [display.map_rotation] {field}={v}")

        return v


class DisplayMapRotationEmbedConfig(pydantic.BaseModel):
    enabled: bool
    # pylance complains about this even though it's valid with pydantic
    time_between_refreshes: pydantic.conint(ge=1)  # type: ignore
    display_title: bool
    title: str
    current_map: str
    next_map: str
    other_map: str
    display_legend: bool
    legend: str
    footer: DisplayFooterConfig


class DisplayConfigMapRotation(pydantic.BaseModel):
    color: DisplayMapRotationColorConfig
    embed: DisplayMapRotationEmbedConfig


class PlayerStatsEmbedConfig(pydantic.BaseModel):
    name: str
    value: str
    inline: bool

    @pydantic.validator("value")
    def must_be_valid_embed(cls, v):
        if v not in constants.PLAYER_STATS_EMBEDS:
            raise ValueError(f"Invalid [[display.player_stats]] embed {v}")

        return v


class DisplayPlayerStatsConfig(pydantic.BaseModel):
    enabled: bool
    time_between_refreshes: pydantic.conint(ge=1)  # type: ignore
    display_title: bool
    title: str

    num_to_display: pydantic.conint(ge=1, le=25)  # type: ignore
    embeds: list[PlayerStatsEmbedConfig]

    footer: DisplayFooterConfig


class DisplayConfig(pydantic.BaseModel):
    header: DisplayHeaderConfig
    gamestate: DisplayGamestateConfig
    map_rotation: DisplayConfigMapRotation
    player_stats: DisplayPlayerStatsConfig


class Config(pydantic.BaseModel):
    settings: SettingsConfig
    output: OutputConfig
    discord: DiscordConfig
    api: APIConfig
    display: DisplayConfig
