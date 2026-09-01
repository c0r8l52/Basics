import anthropic

SYSTEM_PROMPT = """You are a world-class fantasy football general manager with decades of \
championship experience. You have built title teams in PPR, half-PPR, and standard formats \
by combining hard data with sharp team-building judgment.

You are handed, for a single live draft pick:
  - the manager's current roster and remaining starting-lineup needs
  - a pool of available players, each carrying ESPN's own platform rating/ownership data \
AND FantasyPros' consensus expert ranking, tier, and ADP

Weigh both data sources together with your own judgment: best-player-available vs. roster \
need, positional scarcity and tier cliffs (a run on a position about to dry up matters more \
than raw rank), bye-week collisions with players already rostered, injury/workload risk, and \
upside vs. floor given how many roster spots are left. Two sources disagreeing is a signal to \
think, not to average blindly.

Be decisive. Fantasy managers drafting live do not have time for hedging. Give exactly three \
ranked candidates, then commit to ONE single clear recommendation with a concrete reason a \
manager could read in five seconds and act on.

Respond only by calling the submit_draft_recommendation tool.
"""

RECOMMENDATION_TOOL = {
    "name": "submit_draft_recommendation",
    "description": "Submit the top-3 draft candidates and one clear recommended pick.",
    "input_schema": {
        "type": "object",
        "properties": {
            "team_assessment": {
                "type": "string",
                "description": "1-2 sentences on the roster's current state and biggest need.",
            },
            "top_picks": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "enum": [1, 2, 3]},
                        "player": {"type": "string"},
                        "position": {"type": "string"},
                        "pro_team": {"type": "string"},
                        "reasoning": {
                            "type": "string",
                            "description": "Why this player, citing ESPN and/or FantasyPros data plus team fit.",
                        },
                    },
                    "required": ["rank", "player", "position", "reasoning"],
                },
            },
            "recommendation": {
                "type": "object",
                "description": "The single player to pick right now.",
                "properties": {
                    "player": {"type": "string"},
                    "position": {"type": "string"},
                    "pro_team": {"type": "string"},
                    "why": {"type": "string", "description": "One clear, concrete, decisive rationale."},
                },
                "required": ["player", "why"],
            },
        },
        "required": ["top_picks", "recommendation"],
    },
}


class GMAdvisor:
    def __init__(self, config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def _build_user_prompt(self, roster_needs, my_roster, available_players, scoring_label, position_filter, pool_size):
        pool = available_players
        if position_filter:
            pool = [p for p in pool if p["position"] == position_filter]
        pool = pool[:pool_size]

        lines = [f"League scoring format: {scoring_label}", ""]

        lines.append("STARTING LINEUP NEEDS (required vs. currently rostered):")
        if roster_needs:
            for slot, info in roster_needs.items():
                lines.append(
                    f"  - {slot}: needs {info['still_needed']} more "
                    f"(requires {info['required']}, have {info['rostered']})"
                )
        else:
            lines.append("  - (no starting slots configured)")

        lines.append("")
        lines.append("CURRENT ROSTER:")
        if my_roster:
            for p in my_roster:
                lines.append(
                    f"  - {p['name']} ({p['position']}, {p['pro_team']}) "
                    f"injury={p['injury_status']}"
                )
        else:
            lines.append("  - (empty roster so far)")

        lines.append("")
        if position_filter:
            lines.append(f"AVAILABLE PLAYERS (filtered to position={position_filter}):")
        else:
            lines.append("AVAILABLE PLAYERS (best-available first):")
        lines.append(
            "  name | position | pro_team | injury | ESPN_proj_pts | ESPN_avg_pts | "
            "ESPN_pct_owned | FantasyPros_rank | FantasyPros_tier | FantasyPros_ADP"
        )
        for p in pool:
            lines.append(
                f"  - {p['name']} | {p['position']} | {p['pro_team']} | {p['injury_status']} | "
                f"{p['espn_projected_points']} | {p['espn_avg_points']} | {p['percent_owned']}% | "
                f"{p['fp_rank']} | {p['fp_tier']} | {p['fp_adp']}"
            )

        lines.append("")
        lines.append(
            "Pick the top 3 candidates for this pick and one single clear recommendation. "
            "Call submit_draft_recommendation now."
        )
        return "\n".join(lines)

    def recommend(self, roster_needs, my_roster, available_players, position_filter=None, pool_size=50):
        user_prompt = self._build_user_prompt(
            roster_needs, my_roster, available_players, self.config.scoring_label, position_filter, pool_size
        )

        response = self.client.messages.create(
            model=self.config.anthropic_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=[RECOMMENDATION_TOOL],
            tool_choice={"type": "tool", "name": "submit_draft_recommendation"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_draft_recommendation":
                return block.input

        raise RuntimeError("Claude did not return a submit_draft_recommendation tool call.")
