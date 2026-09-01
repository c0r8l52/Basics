import csv
import os
import re

from .matching import build_lookup, find_match

# FantasyPros CSV exports vary by report (cheat sheet vs ADP vs weekly rankings).
# Map every header variant we've seen to a canonical column name.
_HEADER_ALIASES = {
    "rank": "rank",
    "rk": "rank",
    "overall rank": "rank",
    "tier": "tier",
    "tiers": "tier",
    "player name": "player",
    "player": "player",
    "team": "team",
    "pos": "position",
    "position": "position",
    "bye": "bye",
    "bye week": "bye",
    "adp": "adp",
    "avg": "adp",
    "sos season": "sos",
    "ecr vs. adp": "ecr_vs_adp",
}


def _canonical_headers(fieldnames):
    return {name: _HEADER_ALIASES.get(name.strip().lower()) for name in fieldnames}


class FantasyProsRankings:
    """Loads a rankings CSV exported from FantasyPros (Cheat Sheets -> Export to CSV,
    or the ADP page's CSV export). No API key needed since these are simple file
    exports available to any paid subscriber."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.rows = []
        self.loaded = False
        self._by_name = {}
        self._by_defense_key = {}

    def load(self):
        self.rows = []
        self.loaded = False
        if not os.path.exists(self.csv_path):
            return self

        with open(self.csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_map = _canonical_headers(reader.fieldnames or [])
            for raw_row in reader:
                row = {}
                for raw_key, value in raw_row.items():
                    canonical = header_map.get(raw_key)
                    if canonical:
                        row[canonical] = (value or "").strip()
                if row.get("player"):
                    row["rank"] = _to_int(row.get("rank"))
                    row["tier"] = _to_int(row.get("tier"))
                    # FantasyPros exports pack position + positional rank into one
                    # field, e.g. "RB1", "DST1", "WR23" - strip the trailing digits.
                    if row.get("position"):
                        row["position"] = re.sub(r"\d+$", "", row["position"]).strip()
                    self.rows.append(row)

        self._by_name, self._by_defense_key = build_lookup(self.rows)
        self.loaded = bool(self.rows)
        return self

    def lookup(self, player_name: str, position: str = ""):
        if not self.loaded:
            return None
        return find_match(player_name, position, self._by_name, self._by_defense_key)


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
