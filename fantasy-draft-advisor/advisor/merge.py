def espn_player_to_dict(player) -> dict:
    return {
        "name": player.name,
        "position": player.position,
        "pro_team": player.proTeam,
        "injury_status": player.injuryStatus,
        "percent_owned": player.percent_owned,
        "espn_projected_points": player.projected_total_points,
        "espn_avg_points": player.avg_points,
        "espn_pos_rank": player.posRank,
    }


def merge_available_players(espn_players, fp_rankings) -> list:
    """Join ESPN free-agent data with FantasyPros rankings by player name."""
    merged = []
    for player in espn_players:
        row = espn_player_to_dict(player)
        fp_row = fp_rankings.lookup(player.name, player.position)
        if fp_row:
            row["fp_rank"] = fp_row.get("rank")
            row["fp_tier"] = fp_row.get("tier")
            row["fp_adp"] = fp_row.get("adp")
        else:
            row["fp_rank"] = None
            row["fp_tier"] = None
            row["fp_adp"] = None
        merged.append(row)

    # Best-available-first: FantasyPros rank when we have it, else ESPN's own
    # ranking signal (ownership % as a proxy), unmatched-and-unowned last.
    def sort_key(row):
        if row["fp_rank"] is not None:
            return (0, row["fp_rank"])
        return (1, -row["percent_owned"])

    merged.sort(key=sort_key)
    return merged


def my_roster_to_dict(team) -> list:
    return [espn_player_to_dict(p) for p in team.roster]
