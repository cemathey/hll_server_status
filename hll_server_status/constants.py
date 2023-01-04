EMPTY_EMBED = "\u200B"

SESSION_ID_COOKIE = "sessionid"
CONFIG_DIR = "config/"
CONFIG_FILENAME = "config.toml"

MESSAGES_DIR = "messages/"
# MESSAGES_FILENAME_SUFFIX = "_messages.toml"

API_PREFIX = "api/"
MAP_PICTURES = "maps/"

DISPLAY_NAMES = ("name", "short_name")
DISPLAY_EMBEDS = ("reserved_vip_slots", "current_vips")
GAMESTATE_EMBEDS = (
    "num_allied_players",
    "num_axis_players",
    "slots",
    "score",
    "time_remaining",
    "current_map",
    "next_map",
    EMPTY_EMBED,
)

MAP_ROTATION_FORMAT_STYLES = ("color", "emoji")

COLOR_TO_CODE_BLOCK = {
    "auto": "",
    "cyan": "yaml",
    "green": "diff",
    "orange": "css",
    "red": "diff",
    "yellow": "fix",  # works
}

ALL_MAPS = (
    "carentan_offensive_ger",
    "carentan_offensive_us",
    "carentan_warfare",
    "foy_offensive_ger",
    "foy_offensive_us",
    "foy_warfare_night",
    "foy_warfare",
    "hill400_offensive_ger",
    "hill400_offensive_US",
    "hill400_warfare",
    "hurtgenforest_offensive_ger",
    "hurtgenforest_offensive_US",
    "hurtgenforest_warfare_V2_night",
    "hurtgenforest_warfare_V2",
    "kharkov_offensive_ger",
    "kharkov_offensive_rus",
    "kharkov_warfare",
    "kursk_offensive_ger",
    "kursk_offensive_rus",
    "kursk_warfare_night",
    "kursk_warfare",
    "omahabeach_offensive_ger",
    "omahabeach_offensive_us",
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
    "stalingrad_warfare",
    "stmariedumont_off_ger",
    "stmariedumont_off_us",
    "stmariedumont_warfare",
    "stmereeglise_offensive_ger",
    "stmereeglise_offensive_us",
    "stmereeglise_warfare",
    "utahbeach_offensive_ger",
    "utahbeach_offensive_us",
    "utahbeach_warfare",
)

LONG_HUMAN_MAP_NAMES = {
    "carentan_offensive_ger": "Carentan Offensive (GER)",
    "carentan_offensive_us": "Carentan Offensive (US)",
    "carentan_warfare": "Carentan",
    "foy_offensive_ger": "Foy Offensive (GER)",
    "foy_offensive_us": "Foy Offensive (US)",
    "foy_warfare_night": "Foy (Night)",
    "foy_warfare": "Foy",
    "hill400_offensive_ger": "Hill 400 Offensive (GER)",
    "hill400_offensive_US": "Hill 400 Offensive (US)",
    "hill400_warfare": "Hill 400",
    "hurtgenforest_offensive_ger": "Hürtgen Forest Offensive (GER)",
    "hurtgenforest_offensive_US": "Hürtgen Forest Offensive (US)",
    "hurtgenforest_warfare_V2_night": "Hürtgen Forest (Night)",
    "hurtgenforest_warfare_V2": "Hürtgen Forest",
    "kharkov_offensive_ger": "Kharkov Offensive (GER)",
    "kharkov_offensive_rus": "Kharkov Offensive (RUS)",
    "kharkov_warfare": "Kharkov",
    "kursk_offensive_ger": "Kursk Offensive (GER)",
    "kursk_offensive_rus": "Kursk Offensive (RUS)",
    "kursk_warfare_night": "Kursk (Night)",
    "kursk_warfare": "Kursk",
    "omahabeach_offensive_ger": "Omaha Beach Offensive (GER)",
    "omahabeach_offensive_us": "Omaha Beach Offensive (US)",
    "omahabeach_warfare": "Omaha Beach",
    "purpleheartlane_offensive_ger": "Purple Heart Lane Offensive (GER)",
    "purpleheartlane_offensive_us": "Purple Heart Lane Offensive (US)",
    "purpleheartlane_warfare_night": "Purple Heart Lane (Night)",
    "purpleheartlane_warfare": "Purple Heart Lane",
    "remagen_offensive_ger": "Remagen Offensive (GER)",
    "remagen_offensive_us": "Remagen Offensive (US)",
    "remagen_warfare_night": "Remagen (Night)",
    "remagen_warfare": "Remagen",
    "stalingrad_offensive_ger": "Stalingrad Offensive (GER)",
    "stalingrad_offensive_rus": "Stalingrad Offensive (RUS)",
    "stalingrad_warfare": "Stalingrad",
    "stmariedumont_off_ger": "Ste Marie du Mont Offensive (GER)",
    "stmariedumont_off_us": "Ste Marie du Mont Offensive (US)",
    "stmariedumont_warfare": "Ste Marie du Mont",
    "stmereeglise_offensive_ger": "Ste Mère Église Offensive (GER)",
    "stmereeglise_offensive_us": "Ste Mère Église Offensive (US)",
    "stmereeglise_warfare": "Ste Mère Église",
    "utahbeach_offensive_ger": "Utah Beach Offensive (GER)",
    "utahbeach_offensive_us": "Utah Beach Offensive (US)",
    "utahbeach_warfare": "Utah Beach",
}

MAP_TO_PICTURE = {
    "carentan": "carentan.webp",
    "foy": "foy.webp",
    "hill400": "hill400.webp",
    "hurtgen": "hurtgen.webp",
    "kharkov": "kharkov.webp",
    "kursk": "kursk.webp",
    "omaha": "omaha.webp",
    "purpleheartlane": "phl.webp",
    "remagen": "remagen.webp",
    "stalingrad": "stalingrad.webp",
    "stmariedumont": "smdm.webp",
    "stmereeglise": "sme.webp",
    "utahbeach": "utah.webp",
}

RUSSIAN_MAPS = (
    "kharkov_offensive_ger",
    "kharkov_offensive_rus",
    "kharkov_warfare",
    "kursk_offensive_ger",
    "kursk_offensive_rus",
    "kursk_warfare_night",
    "kursk_warfare",
    "stalingrad_offensive_ger",
    "stalingrad_offensive_rus",
    "stalingrad_warfare",
)

# Could just do set intersections to get russian vs. us but making it explicit
# especially for when more factions come along
US_MAPS = (
    "carentan_offensive_ger",
    "carentan_offensive_us",
    "carentan_warfare",
    "foy_offensive_ger",
    "foy_offensive_us",
    "foy_warfare_night",
    "foy_warfare",
    "hill400_offensive_ger",
    "hill400_offensive_US",
    "hill400_warfare",
    "hurtgenforest_offensive_ger",
    "hurtgenforest_offensive_US",
    "hurtgenforest_warfare_V2_night",
    "hurtgenforest_warfare_V2",
    "omahabeach_offensive_ger",
    "omahabeach_offensive_us",
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
    "stmereeglise_warfare",
    "utahbeach_offensive_ger",
    "utahbeach_offensive_us",
    "utahbeach_warfare",
)
