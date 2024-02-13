import enum
from typing import Final

EMPTY_EMBED: Final = "\u200B"
NONE_MESSAGE_ID: Final = 0

API_KEY_FORMAT = "Bearer: {api_key}"
AUTH_HEADER = "Authorization"

ROOT_LOGGER_NAME = "hll_server_status"
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

BETWEEN_MATCHES_MAP_NAME: Final = "Untitled"
MAP_RESTART_SUFFIX: Final = "_RESTART"

ALL_MAPS: Final = (
    "carentan_offensive_ger",
    "carentan_offensive_us",
    "carentan_warfare_night",
    "carentan_warfare",
    "driel_offensive_ger",
    "driel_offensive_us",
    "driel_warfare_night",
    "driel_warfare",
    "elalamein_offensive_CW",
    "elalamein_offensive_ger",
    "elalamein_warfare_night",
    "elalamein_warfare",
    "foy_offensive_ger",
    "foy_offensive_us",
    "foy_warfare_night",
    "foy_warfare",
    "hill400_offensive_ger",
    "hill400_offensive_us",
    "hill400_offensive_US",
    "hill400_warfare_night",
    "hill400_warfare",
    "hurtgenforest_offensive_ger",
    "hurtgenforest_offensive_US",
    "hurtgenforest_warfare_V2_night",
    "hurtgenforest_warfare_V2",
    "kharkov_offensive_ger",
    "kharkov_offensive_rus",
    "kharkov_warfare_night",
    "kharkov_warfare",
    "kursk_offensive_ger",
    "kursk_offensive_rus",
    "kursk_warfare_night",
    "kursk_warfare",
    "omahabeach_offensive_ger",
    "omahabeach_offensive_us",
    "omahabeach_warfare_night",
    "omahabeach_warfare",
    "purpleheartlane_offensive_ger",
    "purpleheartlane_offensive_us",
    "purpleheartlane_warfare_night",
    "purpleheartlane_warfare",
    "remagen_offensive_ger",
    "remagen_offensive_us",
    "remagen_warfare_night",
    "remagen_warfare",
    "stalingrad_offensive_ger",
    "stalingrad_offensive_rus",
    "stalingrad_warfare_night",
    "stalingrad_warfare",
    "stmariedumont_off_ger",
    "stmariedumont_off_us",
    "stmariedumont_warfare",
    "stmereeglise_offensive_ger",
    "stmereeglise_offensive_us",
    "stmereeglise_warfare_night",
    "stmereeglise_warfare",
    "utahbeach_offensive_ger",
    "utahbeach_offensive_us",
    "utahbeach_warfare_night",
    "utahbeach_warfare",
)

LONG_HUMAN_MAP_NAMES: Final = {
    "Untitled": "End of Match",
    "carentan_offensive_ger": "Carentan Offensive GER",
    "carentan_offensive_us": "Carentan Offensive US",
    "carentan_warfare_night": "Carentan (Night)",
    "carentan_warfare": "Carentan",
    "driel_offensive_ger": "Driel Offensive (GER)",
    "driel_offensive_us": "Driel Offensive (UK)",
    "driel_warfare_night": "Driel (Night)",
    "driel_warfare": "Driel",
    "elalamein_offensive_CW": "El Alamein Offensive (UK)",
    "elalamein_offensive_ger": "El Alamein Offensive (GER)",
    "elalamein_warfare_night": "El Alamein (Night)",
    "elalamein_warfare": "El Alamein",
    "foy_offensive_ger": "Foy Offensive GER",
    "foy_offensive_us": "Foy Offensive US",
    "foy_warfare_night": "Foy Night",
    "foy_warfare": "Foy",
    "hill400_offensive_ger": "Hill 400 Offensive GER",
    "hill400_offensive_us": "Hill 400 Offensive US",
    "hill400_offensive_US": "Hill 400 Offensive US",
    "hill400_warfare_night": "Hill 400 (Night)",
    "hill400_warfare": "Hill 400",
    "hurtgenforest_offensive_ger": "Hurtgen Forest Offensive GER",
    "hurtgenforest_offensive_US": "Hurtgen Forest Offensive US",
    "hurtgenforest_warfare_V2_night": "Hurtgen Forest Night",
    "hurtgenforest_warfare_V2": "Hurtgen Forest",
    "kharkov_offensive_ger": "Kharkov Offensive GER",
    "kharkov_offensive_rus": "Kharkov Offensive RUS",
    "kharkov_warfare_night": "Kharkov (Night)",
    "kharkov_warfare": "Kharkov",
    "kursk_offensive_ger": "Kursk Offensive GER",
    "kursk_offensive_rus": "Kursk Offensive RUS",
    "kursk_warfare_night": "Kursk Night",
    "kursk_warfare": "Kursk",
    "omahabeach_offensive_ger": "Omaha Beach Offensive GER",
    "omahabeach_offensive_us": "Omaha Beach Offensive US",
    "omahabeach_warfare_night": "Omaha (Night)",
    "omahabeach_warfare": "Omaha Beach",
    "purpleheartlane_offensive_ger": "Purple Heart Lane Offensive GER",
    "purpleheartlane_offensive_us": "Purple Heart Lane Offensive US",
    "purpleheartlane_warfare_night": "Purple Heart Lane Night",
    "purpleheartlane_warfare": "Purple Heart Lane",
    "remagen_offensive_ger": "Remagen Offensive GER",
    "remagen_offensive_us": "Remagen Offensive US",
    "remagen_warfare_night": "Remagen Night",
    "remagen_warfare": "Remagen",
    "stalingrad_offensive_ger": "Stalingrad Offensive GER",
    "stalingrad_offensive_rus": "Stalingrad Offensive RUS",
    "stalingrad_warfare_night": "Stalingrad (Night)",
    "stalingrad_warfare": "Stalingrad",
    "stmariedumont_off_ger": "Ste Marie du Mont Offensive GER",
    "stmariedumont_off_us": "Ste Marie du Mont Offensive US",
    "stmariedumont_warfare": "Ste Marie du Mont",
    "stmereeglise_offensive_ger": "Ste Mere Eglise Offensive GER",
    "stmereeglise_offensive_us": "Ste Mere Eglise Offensive US",
    "stmereeglise_warfare_night": "Ste Mere Eglise (Night)",
    "stmereeglise_warfare": "Ste Mere Eglise",
    "utahbeach_offensive_ger": "Utah Beach Offensive GER",
    "utahbeach_offensive_us": "Utah Beach Offensive US",
    "utahbeach_warfare_night": "Utah (Night)",
    "utahbeach_warfare": "Utah Beach",
}

MAP_TO_PICTURE: Final = {
    "driel": "driel.webp",
    "driel_night": "driel-night.webp",
    "elalamein": "elalamein.webp",
    "elalamein_night": "elalamein-night.webp",
    "carentan": "carentan.webp",
    "carentan_night": "carentan-night.webp",
    "foy": "foy.webp",
    "foy_night": "foy-night.webp",
    "hill400": "hill400.webp",
    "hill400_night": "hill400-night.webp",
    "hurtgenforest": "hurtgen.webp",
    "hurtgenforest_night": "hurtgen-night.webp",
    "kharkov": "kharkov.webp",
    "kharkov_night": "kharkov-night.webp",
    "kursk": "kursk.webp",
    "kursk_night": "kursk-night.webp",
    "omahabeach": "omaha.webp",
    "omahabeach_night": "omaha-night.webp",
    "purpleheartlane": "phl.webp",
    "purpleheartlane_night": "phl-night.webp",
    "remagen": "remagen.webp",
    "remagen_night": "remagen-night.webp",
    "stalingrad": "stalingrad.webp",
    "stalingrad_night": "stalingrad-night.webp",
    "stmariedumont": "smdm.webp",
    "stmariedumont_night": "smdm-night.webp",
    "stmereeglise": "sme.webp",
    "stmereeglise_night": "sme-night.webp",
    "utahbeach": "utah.webp",
    "utahbeach_night": "utah-night.webp",
}

RUSSIAN_MAPS: Final = (
    "kharkov_offensive_ger",
    "kharkov_offensive_rus",
    "kharkov_warfare_night",
    "kharkov_warfare",
    "kursk_offensive_ger",
    "kursk_offensive_rus",
    "kursk_warfare_night",
    "kursk_warfare",
    "stalingrad_offensive_ger",
    "stalingrad_offensive_rus",
    "stalingrad_warfare_night",
    "stalingrad_warfare",
)

# Could just do set intersections to get russian vs. us but making it explicit
# especially for when more factions come along
US_MAPS: Final = (
    "carentan_offensive_ger",
    "carentan_offensive_us",
    "carentan_warfare_night",
    "carentan_warfare",
    "foy_offensive_ger",
    "foy_offensive_us",
    "foy_warfare_night",
    "foy_warfare",
    "hill400_offensive_ger",
    "hill400_offensive_us",
    "hill400_offensive_US",
    "hill400_warfare_night",
    "hill400_warfare",
    "hurtgenforest_offensive_ger",
    "hurtgenforest_offensive_US",
    "hurtgenforest_warfare_V2_night",
    "hurtgenforest_warfare_V2",
    "omahabeach_offensive_ger",
    "omahabeach_offensive_us",
    "omahabeach_warfare_night",
    "omahabeach_warfare",
    "purpleheartlane_offensive_ger",
    "purpleheartlane_offensive_us",
    "purpleheartlane_warfare_night",
    "purpleheartlane_warfare",
    "remagen_offensive_ger",
    "remagen_offensive_us",
    "remagen_warfare_night",
    "remagen_warfare",
    "stmariedumont_off_ger",
    "stmariedumont_off_us",
    "stmariedumont_warfare",
    "stmereeglise_offensive_ger",
    "stmereeglise_offensive_us",
    "stmereeglise_warfare_night",
    "stmereeglise_warfare",
    "utahbeach_offensive_ger",
    "utahbeach_offensive_us",
    "utahbeach_warfare_night",
    "utahbeach_warfare",
)

UK_MAPS: Final = (
    "driel_offensive_ger",
    "driel_offensive_us",
    "driel_warfare_night",
    "driel_warfare",
    "elalamein_offensive_CW",
    "elalamein_offensive_ger",
    "elalamein_warfare_night",
    "elalamein_warfare",
)

# TODO: Update with British maps on U14 release

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
