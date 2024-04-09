import re
from datetime import timedelta
from typing import Any

from hll_server_status.types import (
    AppStore,
    GameState,
    Map,
    PlayerStats,
    PlayerStatsCrconType,
    ServerName,
    Slots,
)

TIME_REMAINING_PATTERN = re.compile(r"(\d{1}):(\d{2}):(\d{2})")


def parse_gamestate(app_store: AppStore, result: dict[str, Any]) -> GameState:
    """Parse and validate the result of /api/get_gamestate"""
    matched = re.match(TIME_REMAINING_PATTERN, result["raw_time_remaining"])
    if not matched:
        raise ValueError("Received an invalid response from your CRCON Server")
    hours, minutes, seconds = matched.groups()

    result["time_remaining"] = timedelta(
        hours=int(hours), minutes=int(minutes), seconds=int(seconds)
    )

    try:
        result["current_map"] = Map(raw_name=result["current_map"])
    except ValueError:
        app_store.logger.error(
            f"Invalid map name received current_map={result['current_map']}"
        )
        raise
    try:
        result["next_map"] = Map(raw_name=result["next_map"])
    except ValueError:
        app_store.logger.error(
            f"Invalid map name received next_map={result['next_map']}"
        )
        raise

    return GameState(
        num_allied_players=result["num_allied_players"],
        num_axis_players=result["num_axis_players"],
        allied_score=result["allied_score"],
        axis_score=result["axis_score"],
        raw_time_remaining=result["raw_time_remaining"],
        time_remaining=result["time_remaining"],
        current_map=result["current_map"],
        next_map=result["next_map"],
    )


def parse_slots(result: dict[str, Any]) -> Slots:
    """Parse and validate the result of /api/get_slots"""
    player_count, max_players = result["result"].split("/")
    return Slots(player_count=int(player_count), max_players=int(max_players))


def parse_map_rotation(result: dict[str, Any]) -> list[Map]:
    """Parse and validate the result of /api/get_map_rotation"""
    result = result["result"]
    return [Map(raw_name=map_name) for map_name in result]


def parse_server_name(result: dict[str, Any]) -> ServerName:
    """Parse and validate the server name/short name from /api/get_status"""
    return ServerName(name=result["name"], short_name=result["short_name"])


def parse_vip_slots_num(result: dict[str, Any]):
    """Parse and validate the number of reserved VIP slots from /api/get_vip_slots_num"""
    return int(result["result"])


def parse_vips_count(result: dict[str, Any]):
    """Parse and validate the number of VIPs on the server from /api/get_vips_count"""
    return int(result["result"])


def parse_player_stats(result: dict[str, Any]) -> list[PlayerStats]:
    """Parse and validate player stats from /api/get_live_game_stats"""
    raw_result: list[PlayerStatsCrconType] = result["stats"]
    return [
        PlayerStats(
            player=raw_player["player"],
            steam_id_64=raw_player["steam_id_64"],
            kills=raw_player["kills"],
            kill_streak=raw_player["kills_streak"],
            deaths=raw_player["deaths"],
            death_streak=raw_player["deaths_without_kill_streak"],
            teamkills=raw_player["teamkills"],
            teamkills_streak=raw_player["teamkills_streak"],
            deaths_by_tk=raw_player["deaths_by_tk"],
            deaths_by_tk_streak=raw_player["deaths_by_tk_streak"],
            longest_life_secs=raw_player["longest_life_secs"],
            shortest_life_secs=raw_player["shortest_life_secs"],
            kills_by_weapons=raw_player["weapons"],
            deaths_by_weapons=raw_player["death_by_weapons"],
            most_killed_players=raw_player["most_killed"],
            death_by_players=raw_player["death_by"],
            combat=raw_player["combat"],
            offense=raw_player["offense"],
            defense=raw_player["defense"],
            support=raw_player["support"],
            kills_per_minute_=raw_player["kills_per_minute"],
            deaths_per_minute_=raw_player["deaths_per_minute"],
            kill_death_ratio_=raw_player["kill_death_ratio"],
        )
        for raw_player in raw_result
    ]
