from collections import Counter

from espn_api.football import League

# Bench/IR slots don't represent a "need" to fill during drafting.
NON_STARTING_SLOTS = {"BE", "IR"}


class ESPNError(RuntimeError):
    pass


class ESPNClient:
    """Thin wrapper around espn_api.football.League for this app's needs."""

    def __init__(self, config):
        self.config = config
        self._league = None

    def refresh(self):
        """Force a fresh pull from ESPN (call between draft picks)."""
        try:
            self._league = League(
                league_id=self.config.espn_league_id,
                year=self.config.espn_year,
                espn_s2=self.config.espn_s2,
                swid=self.config.espn_swid,
            )
        except Exception as exc:  # espn_api raises plain Exceptions on HTTP errors
            raise ESPNError(
                "Could not reach ESPN with the configured league/credentials. "
                "Double-check ESPN_LEAGUE_ID, ESPN_YEAR, and (for private leagues) "
                f"ESPN_S2/ESPN_SWID. Underlying error: {exc}"
            ) from exc
        return self._league

    def league(self):
        if self._league is None:
            self.refresh()
        return self._league

    def my_team(self):
        league = self.league()
        for team in league.teams:
            if team.team_id == self.config.espn_team_id:
                return team
        valid_ids = ", ".join(str(t.team_id) for t in league.teams)
        raise ESPNError(
            f"No team with ESPN_TEAM_ID={self.config.espn_team_id} in this league. "
            f"Valid team IDs: {valid_ids}"
        )

    def starting_slot_counts(self) -> dict:
        """{'QB': 1, 'RB': 2, 'RB/WR/TE': 1, ...} excluding bench/IR."""
        slots = self.league().settings.position_slot_counts
        return {pos: n for pos, n in slots.items() if pos not in NON_STARTING_SLOTS and n > 0}

    def roster_needs(self) -> dict:
        """Compares starting slots against what's currently rostered by position."""
        team = self.my_team()
        rostered = Counter(p.position for p in team.roster)
        needs = {}
        for slot, required in self.starting_slot_counts().items():
            have = rostered.get(slot, 0)
            needs[slot] = {"required": required, "rostered": have, "still_needed": max(0, required - have)}
        return needs

    def available_players(self, size: int = None):
        """Undrafted / free-agent players, ranked by ESPN's own ownership + rank sort."""
        size = size or self.config.free_agent_pool_size
        return self.league().free_agents(size=size)
