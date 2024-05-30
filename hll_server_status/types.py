import re
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, Literal, TypedDict, Union

import httpx
import loguru
import pydantic
import typing_extensions

from hll_server_status import constants


class ServerName(pydantic.BaseModel):
    """Represents the server name from /api/get_status"""

    name: str
    short_name: str


class MapType(typing_extensions.TypedDict):
    id: str
    name: str
    tag: str
    pretty_name: str
    shortname: str
    allies: "Faction"
    axis: "Faction"


class LayerType(typing_extensions.TypedDict):
    id: str
    map: MapType
    game_mode: str
    attackers: str | None
    environment: str
    pretty_name: str
    image_name: str
    image_url: str | None


class GameMode(str, Enum):
    WARFARE = "warfare"
    OFFENSIVE = "offensive"
    CONTROL = "control"
    PHASED = "phased"
    MAJORITY = "majority"

    @classmethod
    def large(cls):
        return (
            cls.WARFARE,
            cls.OFFENSIVE,
        )

    @classmethod
    def small(cls):
        return (
            cls.CONTROL,
            cls.PHASED,
            cls.MAJORITY,
        )

    def is_large(self):
        return self in GameMode.large()

    def is_small(self):
        return self in GameMode.small()


class Team(str, Enum):
    ALLIES = "allies"
    AXIS = "axis"


class Environment(str, Enum):
    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
    OVERCAST = "overcast"
    RAIN = "rain"


class FactionName(Enum):
    CW = "cw"
    GB = "gb"
    GER = "ger"
    RUS = "rus"
    US = "us"


class Faction(pydantic.BaseModel):
    name: str
    team: Team


class Map(pydantic.BaseModel):
    id: str
    name: str
    tag: str
    pretty_name: str
    shortname: str
    allies: "Faction"
    axis: "Faction"

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if isinstance(other, (Map, str)):
            return str(self) == str(other)
        return NotImplemented


class Layer(pydantic.BaseModel):
    id: str
    map: Map
    game_mode: GameMode
    attackers: Union[Team, None] = None
    environment: Environment = Environment.DAY

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"{self.__class__}(id={self.id}, map={self.map}, attackers={self.attackers}, environment={self.environment})"

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if isinstance(other, (Layer, str)):
            return str(self) == str(other)
        return NotImplemented

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(
            self,
            *,
            mode: Literal["json", "python"] | str = "python",
            include: Any = None,
            exclude: Any = None,
            by_alias: bool = False,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool = True,
        ) -> LayerType:
            ...

    else:

        def model_dump(self, **kwargs):
            return super().model_dump(**kwargs)

    @property
    def attacking_faction(self):
        if self.attackers == Team.ALLIES:
            return self.map.allies
        elif self.attackers == Team.AXIS:
            return self.map.axis
        return None

    @pydantic.computed_field
    @property
    def pretty_name(self) -> str:
        out = self.map.pretty_name
        if self.game_mode == GameMode.OFFENSIVE:
            out += " Off."
            if self.attackers and self.attacking_faction:
                out += f" {self.attacking_faction.name.upper()}"
        elif self.game_mode.is_small():
            # TODO: Remove once more Skirmish modes release
            out += " Skirmish"
        else:
            out += f" {self.game_mode.value.capitalize()}"
        if self.environment != Environment.DAY:
            out += f" ({self.environment.value.title()})"
        return out

    @property
    def opposite_side(self) -> Literal[Team.AXIS, Team.ALLIES] | None:
        if self.attackers:
            return get_opposite_side(self.attackers)

    @pydantic.computed_field
    @property
    def image_name(self) -> str:
        return f"{self.map.id}-{self.environment.value}.webp".lower()


def get_opposite_side(team: Team) -> Literal[Team.AXIS, Team.ALLIES]:
    return Team.AXIS if team == Team.ALLIES else Team.ALLIES


class GameStateType(TypedDict):
    """TypedDict for Rcon.get_gamestate"""

    num_allied_players: int
    num_axis_players: int
    allied_score: int
    axis_score: int
    raw_time_remaining: str
    time_remaining: timedelta
    current_map: LayerType
    next_map: LayerType


class GameState(pydantic.BaseModel):
    num_allied_players: int
    num_axis_players: int
    allied_score: int
    axis_score: int
    raw_time_remaining: str
    time_remaining: float
    current_map: Layer
    next_map: Layer


class SlotsType(TypedDict):
    current_players: int
    max_players: int


class Slots(pydantic.BaseModel):
    """Response from api/get_slots"""

    player_count: int
    max_players: int


class PlayerStatsCrconType(TypedDict):
    player: str
    player_id: str

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
    player_id: str

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


@dataclass
class AppStore:
    server_identifier: str
    logger: "loguru.Logger"
    client: httpx.AsyncClient | None


class URL(pydantic.BaseModel):
    url: pydantic.HttpUrl


class SettingsConfig(pydantic.BaseModel):
    time_between_config_file_reads: int = pydantic.Field(ge=1)
    disabled_section_sleep_timer: int = pydantic.Field(ge=1)


class DiscordConfig(pydantic.BaseModel):
    webhook_url: pydantic.HttpUrl


class APIConfig(pydantic.BaseModel):
    base_server_url: pydantic.HttpUrl
    api_key: str


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
    text: str | None
    include_timestamp: bool
    last_refresh_text: str | None


class DisplayHeaderConfig(pydantic.BaseModel):
    enabled: bool
    time_between_refreshes: int = pydantic.Field(ge=1)
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
        # Support empty URL strings
        if v == "":
            return None
        else:
            return v


class DisplayGamestateConfig(pydantic.BaseModel):
    enabled: bool
    time_between_refreshes: int = pydantic.Field(ge=1)
    image: bool
    score_format: str
    score_format_ger_us: str | None
    score_format_ger_rus: str | None
    score_format_ger_uk: str | None
    footer: DisplayFooterConfig
    embeds: list[GamestateEmbedConfig]


class DisplayMapRotationEmbedConfig(pydantic.BaseModel):
    enabled: bool
    time_between_refreshes: int = pydantic.Field(ge=1)
    display_title: bool
    title: str
    current_map: str
    next_map: str
    other_map: str
    display_legend: bool
    legend: str
    footer: DisplayFooterConfig


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
    time_between_refreshes: int = pydantic.Field(ge=1)
    display_title: bool
    title: str

    num_to_display: int = pydantic.Field(ge=1, le=25)
    embeds: list[PlayerStatsEmbedConfig]

    footer: DisplayFooterConfig


class DisplayConfig(pydantic.BaseModel):
    header: DisplayHeaderConfig
    gamestate: DisplayGamestateConfig
    map_rotation: DisplayMapRotationEmbedConfig
    player_stats: DisplayPlayerStatsConfig


class Config(pydantic.BaseModel):
    name: str
    settings: SettingsConfig
    discord: DiscordConfig
    api: APIConfig
    display: DisplayConfig


class TeamVIPCount(TypedDict):
    allies: int
    axis: int
    none: int
