import difflib
import re

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_DEFENSE_POSITIONS = {"D/ST", "DST", "DEF"}


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation/suffixes so 'Patrick Mahomes II' == 'patrick mahomes'."""
    if not name:
        return ""
    name = name.lower().replace(".", "").replace("'", "")
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    tokens = [t for t in name.split() if t not in _SUFFIXES]
    return " ".join(tokens).strip()


def is_defense(position: str) -> bool:
    return (position or "").upper() in _DEFENSE_POSITIONS


def defense_key(name: str) -> str:
    """Defenses are named inconsistently across sources ('San Francisco 49ers' vs
    '49ers' vs 'SF'). Use the last word (team nickname) as the join key."""
    normalized = normalize_name(name)
    return normalized.split()[-1] if normalized else ""


def build_lookup(rows, name_field="player", position_field="position"):
    """Index rows by normalized name, plus a defense-only index by nickname."""
    by_name = {}
    by_defense_key = {}
    for row in rows:
        name = row.get(name_field, "")
        key = normalize_name(name)
        if key:
            by_name[key] = row
        if is_defense(row.get(position_field, "")):
            dkey = defense_key(name)
            if dkey:
                by_defense_key[dkey] = row
    return by_name, by_defense_key


def find_match(name: str, position: str, by_name: dict, by_defense_key: dict, cutoff: float = 0.82):
    """Look up a player across two indexes: exact normalized name, then defense
    nickname, then a fuzzy fallback. Returns the matched row or None."""
    key = normalize_name(name)
    if key in by_name:
        return by_name[key]

    if is_defense(position):
        dkey = defense_key(name)
        if dkey in by_defense_key:
            return by_defense_key[dkey]

    close = difflib.get_close_matches(key, by_name.keys(), n=1, cutoff=cutoff)
    if close:
        return by_name[close[0]]
    return None
