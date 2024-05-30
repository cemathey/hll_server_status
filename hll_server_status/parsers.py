import re
from datetime import timedelta
from typing import Any

from hll_server_status.types import (
    AppStore,
    GameState,
    GameStateType,
    Layer,
    LayerType,
    Map,
    PlayerStats,
    PlayerStatsCrconType,
    ServerName,
    Slots,
    SlotsType,
    TeamVIPCount,
)

TIME_REMAINING_PATTERN = re.compile(r"(\d{1}):(\d{2}):(\d{2})")


def parse_gamestate(app_store: AppStore, result: GameStateType) -> GameState:
    """Parse and validate the result of /api/get_gamestate"""
    return GameState.model_validate(result)


def parse_slots(result: SlotsType) -> Slots:
    """Parse and validate the result of /api/get_slots"""
    player_count = result["current_players"]
    max_players = result["max_players"]
    return Slots(player_count=int(player_count), max_players=int(max_players))


def parse_map_rotation(result: dict[str, Any]) -> list[Layer]:
    """Parse and validate the result of /api/get_map_rotation"""
    map_layers: list[LayerType] = result["result"]
    return [Layer.model_validate(map_) for map_ in map_layers]


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
            player_id=raw_player["player_id"],
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


def parse_vips_by_team(result: dict[str, Any]) -> TeamVIPCount:
    teams: TeamVIPCount = {"allies": 0, "axis": 0, "none": 0}

    for team in teams:
        try:
            for squad_key in result[team]["squads"].keys():
                for player in result[team]["squads"][squad_key]["players"]:
                    if player["is_vip"]:
                        teams[team] += 1
        except KeyError:
            continue

        commander = result[team]["commander"] or {}
        if commander.get("is_vip"):
            teams[team] += 1

    return teams
