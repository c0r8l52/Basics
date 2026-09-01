import sys

from flask import Flask, jsonify, render_template, request

from advisor.config import Config, ConfigError
from advisor.espn_client import ESPNClient, ESPNError
from advisor.fantasypros import FantasyProsRankings
from advisor.gm_advisor import GMAdvisor
from advisor.merge import merge_available_players, my_roster_to_dict

try:
    config = Config()
except ConfigError as exc:
    print(f"\nConfig error: {exc}\n\nCopy .env.example to .env and fill in your values.\n", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)
espn = ESPNClient(config)
fp_rankings = FantasyProsRankings(config.fantasypros_csv_path)
advisor = GMAdvisor(config)

# Cache of the last successful pull, refreshed on demand between picks.
_state = {"my_roster": [], "available_players": [], "roster_needs": {}, "error": None}


def _refresh_state():
    fp_rankings.load()
    try:
        espn.refresh()
        team = espn.my_team()
        available = espn.available_players()
        _state["my_roster"] = my_roster_to_dict(team)
        _state["available_players"] = merge_available_players(available, fp_rankings)
        _state["roster_needs"] = espn.roster_needs()
        _state["error"] = None
    except ESPNError as exc:
        _state["error"] = str(exc)
    return _state


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    if not _state["my_roster"] and not _state["available_players"] and _state["error"] is None:
        _refresh_state()
    return jsonify(
        {
            **_state,
            "fantasypros_loaded": fp_rankings.loaded,
            "fantasypros_csv_path": config.fantasypros_csv_path,
        }
    )


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    _refresh_state()
    return api_state()


@app.route("/api/players")
def api_players():
    position = request.args.get("position") or None
    query = (request.args.get("q") or "").strip().lower()
    players = _state["available_players"]
    if position:
        players = [p for p in players if p["position"] == position]
    if query:
        players = [p for p in players if query in p["name"].lower()]
    return jsonify(players[:200])


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    if _state["error"]:
        return jsonify({"error": _state["error"]}), 400
    if not _state["available_players"]:
        return jsonify({"error": "No available-player data loaded yet. Click Refresh first."}), 400

    body = request.get_json(silent=True) or {}
    position_filter = body.get("position") or None

    try:
        result = advisor.recommend(
            roster_needs=_state["roster_needs"],
            my_roster=_state["my_roster"],
            available_players=_state["available_players"],
            position_filter=position_filter,
        )
    except Exception as exc:  # surface Claude/API errors to the UI instead of a 500 page
        return jsonify({"error": f"GM advisor failed: {exc}"}), 502

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
