import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import NotRequired, TypedDict

import pydantic
import tomlkit

from hll_server_status import constants


class ServerName(pydantic.BaseModel):
    """Represents the server name from /api/get_status"""

    name: str
    short_name: str


class Map(pydantic.BaseModel):
    """Represents a RCON map name such as foy_offensive_ger"""

    class Config:
        underscore_attrs_are_private = True

    raw_name: str

    @pydantic.validator("raw_name")
    def must_be_valid_map_name(cls, v):
        if v not in constants.ALL_MAPS:
            raise ValueError("Invalid Map Name")

        return v

    @property
    def name(self):
        return constants.LONG_HUMAN_MAP_NAMES[self.raw_name]

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


class LoginParameters(pydantic.BaseModel):
    """Body for api/login"""

    username: str
    password: str

    def as_dict(self) -> dict[str, str]:
        return {"username": self.username, "password": self.password}

    def as_json(self):
        return json.dumps(self.as_dict())


class Cookies(TypedDict):
    sessionid: NotRequired[str]


@dataclass
class AppStore:
    server_identifier: str
    message_ids: tomlkit.TOMLDocument = field(default_factory=tomlkit.TOMLDocument)
    cookies: Cookies = field(default_factory=Cookies)


class URL(pydantic.BaseModel):
    url: pydantic.HttpUrl


class OutputConfig(pydantic.BaseModel):
    message_id_directory: str | None
    message_id_filename: str | None


class DiscordConfig(pydantic.BaseModel):
    webhook_url: pydantic.HttpUrl

    def as_dict(self):
        return {"webhook_url": self.webhook_url}


class APIConfig(pydantic.BaseModel):
    base_server_url: str
    username: str
    password: str

    def as_dict(self):
        return {"base_server_url": self.base_server_url}


class DisplayEmbedConfig(pydantic.BaseModel):
    name: str
    value: str
    inline: bool

    @pydantic.validator("value")
    def must_be_valid_embed(cls, v):
        if v not in constants.DISPLAY_EMBEDS:
            raise ValueError(f"Invalid [[display.header]] embed {v}")

        return v

    def as_dict(self):
        return {
            "name": self.name,
            "value": self.value,
            "inline": self.inline,
        }


class GamestateEmbedConfig(pydantic.BaseModel):
    name: str
    value: str
    inline: bool

    @pydantic.validator("value")
    def must_be_valid_embed(cls, v):
        if v not in constants.GAMESTATE_EMBEDS:
            print(f"{v=}")
            raise ValueError(f"Invalid [[display.gamestate]] embed {v}")

        return v

    def as_dict(self):
        return {
            "name": self.name,
            "value": self.value,
            "inline": self.inline,
        }


class DisplayHeaderConfig(pydantic.BaseModel):
    enabled: bool
    server_name: str
    quick_connect_url: pydantic.AnyUrl | None
    battlemetrics_url: pydantic.HttpUrl | None
    embeds: list[DisplayEmbedConfig]

    @pydantic.validator("server_name")
    def must_be_valid_name(cls, v):
        if v not in constants.DISPLAY_NAMES:
            raise ValueError(f"Invalid [[display.header]] name={v}")

        return v

    def as_dict(self):
        return {
            "enabled": self.enabled,
            "name": self.server_name,
            "embeds": [embed.as_dict() for embed in self.embeds],
        }


class DisplayGamestateConfig(pydantic.BaseModel):
    enabled: bool
    image: bool
    score_format: str
    score_format_ger_us: str | None
    score_format_ger_rus: str | None
    embeds: list[GamestateEmbedConfig]

    def as_dict(self):
        return {
            "enabled": self.enabled,
            "image": self.image,
            "embeds": [embed.as_dict() for embed in self.embeds],
        }


class DisplayMapRotationColorConfig(pydantic.BaseModel):
    enabled: bool
    display_title: bool
    title: str
    current_map_color: str
    next_map_color: str
    other_map_color: str
    display_legend: bool
    legend_title: str
    legend: list[str]

    @pydantic.validator("current_map_color", "next_map_color", "other_map_color")
    def must_be_valid_current_map_color(cls, v, field):
        if v not in constants.COLOR_TO_CODE_BLOCK.keys():
            raise ValueError(f"Invalid [display.map_rotation] {field}={v}")

        return v


class DisplayMapRotationEmojiConfig(pydantic.BaseModel):
    enabled: bool
    display_title: bool
    title: str
    current_map_emoji: str
    next_map_emoji: str
    other_map_emoji: str
    display_legend: bool
    legend: str


class DisplayConfigMapRotation(pydantic.BaseModel):
    color: DisplayMapRotationColorConfig
    emoji: DisplayMapRotationEmojiConfig


class DisplayConfig(pydantic.BaseModel):
    header: DisplayHeaderConfig
    gamestate: DisplayGamestateConfig
    map_rotation: DisplayConfigMapRotation

    # def as_dict(self):
    #     return {
    #         "header": self.header.as_dict(),
    #         "gamestate": self.gamestate.as_dict(),
    #         "map_rotation": self.map_rotation.as_dict(),
    #     }


class Config(pydantic.BaseModel):
    output: OutputConfig
    discord: DiscordConfig
    api: APIConfig
    display: DisplayConfig

    # def as_dict(self):
    #     return {
    #         "discord": self.discord.as_dict(),
    #         "api": self.api.as_dict(),
    #         "display": self.display.as_dict(),
    #     }
