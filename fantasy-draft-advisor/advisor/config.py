import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    pass


def _require_int(name: str) -> int:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"Missing required env var: {name}")
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{name} must be an integer, got {value!r}")


class Config:
    """Loads all app settings from environment variables (.env)."""

    def __init__(self):
        self.espn_league_id = _require_int("ESPN_LEAGUE_ID")
        self.espn_year = int(os.environ.get("ESPN_YEAR", "2026"))
        self.espn_team_id = _require_int("ESPN_TEAM_ID")
        # Only required for private leagues. Leave unset for public leagues.
        self.espn_s2 = os.environ.get("ESPN_S2") or None
        self.espn_swid = os.environ.get("ESPN_SWID") or None

        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.anthropic_api_key:
            raise ConfigError("Missing required env var: ANTHROPIC_API_KEY")
        self.anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

        self.fantasypros_csv_path = os.environ.get(
            "FANTASYPROS_CSV_PATH", os.path.join("data", "fantasypros_rankings.csv")
        )
        self.scoring_label = os.environ.get("SCORING_LABEL", "PPR")

        self.free_agent_pool_size = int(os.environ.get("FREE_AGENT_POOL_SIZE", "300"))
