import enum
from typing import Final

EMPTY_EMBED: Final = "\u200B"
NONE_MESSAGE_ID: Final = 0

API_KEY_FORMAT: Final = "Bearer: {api_key}"
AUTH_HEADER: Final = "Authorization"

ROOT_LOGGER_NAME: Final = "hll_server_status"
CONFIG_DIR: Final = "config/"
MESSAGES_DIR: Final = "messages/"
LOG_DIR: Final = "logs/"

MANDATORY_DIRECTORIES: Final = (CONFIG_DIR, MESSAGES_DIR, LOG_DIR)

LOG_EXTENSION: Final = "log"
LOG_SIZE: Final = "5 MB"
LOG_RETENTION_DAYS: Final = "3 days"
LOG_FORMAT: Final = "{time:YYYY-MM-DD at HH:mm:ss} {level} {message}"

API_PREFIX: Final = "api/"
MAP_PICTURES: Final = "maps/"

NS_TO_SECONDS_FACTOR: Final = 1_000_000_000


DISPLAY_NAMES: Final = ("name", "short_name")
DISPLAY_EMBEDS: Final = ("reserved_vip_slots", "current_vips")
GAMESTATE_EMBEDS: Final = (
    "num_allied_players",
    "num_axis_players",
    "num_allied_vips",
    "num_axis_vips",
    "slots",
    "score",
    "time_remaining",
    "current_map",
    "next_map",
    EMPTY_EMBED,
)


class PlayerStatsEnum(enum.Enum):
    highest_kills = "highest_kills"
    kills_per_minute = "kills_per_minute"
    highest_deaths = "highest_deaths"
    deaths_per_minute = "deaths_per_minute"
    highest_kdr = "highest_kdr"
    kill_streak = "kill_streak"
    death_streak = "death_streak"
    highest_team_kills = "highest_team_kills"
    team_kill_streak = "team_kill_streak"
    longest_life = "longest_life"
    shortest_life = "shortest_life"


PLAYER_STATS_EMBEDS: Final = (
    PlayerStatsEnum.highest_kills.value,
    PlayerStatsEnum.kills_per_minute.value,
    PlayerStatsEnum.highest_deaths.value,
    PlayerStatsEnum.deaths_per_minute.value,
    PlayerStatsEnum.highest_kdr.value,
    PlayerStatsEnum.kill_streak.value,
    PlayerStatsEnum.death_streak.value,
    PlayerStatsEnum.highest_team_kills.value,
    PlayerStatsEnum.team_kill_streak.value,
    PlayerStatsEnum.longest_life.value,
    PlayerStatsEnum.shortest_life.value,
    EMPTY_EMBED,
)


UNKNOWN_MAP_NAME = "unknown"
BETWEEN_MATCHES_MAP_NAME: Final = "Untitled"
MAP_RESTART_SUFFIX: Final = "_RESTART"

SCORE_EMBEDS: Final = (
    "TOP_KILLERS",
    "TOP_RATIO",
    "TOP_PERFORMANCE",
    "TRY_HARDERS",
    "TOP_STAMINA",
    "TOP_KILL_STREAK",
    "I_NEVER_GIVE_UP",
    "MOST_PATIENT",
    "I_M_CLUMSY",
    "I_NEED_GLASSES",
    "I_LOVE_VOTING",
    "WHAT_IS_A_BREAK",
    "SURVIVORS",
    "U_R_STILL_A_MAN",
)
