# Fantasy Draft Advisor

A local web app for your ESPN Fantasy Football draft. It pulls your live roster and
available players from ESPN (with ESPN's own projections/ownership data), blends in
your FantasyPros rankings, and asks Claude — acting as a world-class GM — for the
top 3 picks and one clear recommendation for your next selection.

Runs entirely on your machine. Your ESPN cookies and API key stay in a local `.env`
file that is never committed to git.

## How it works

- **ESPN data**: pulled live via the `espn_api` library using your league ID and
  (for private leagues) your `espn_s2`/`SWID` session cookies. Gives your roster,
  the free-agent/available-player pool, and each player's ESPN projected points,
  average points, and ownership %.
- **FantasyPros data**: FantasyPros' API requires a separate developer/partner
  agreement that a normal subscription doesn't include. Instead, this app reads a
  rankings CSV that you export from the FantasyPros website (a feature included
  with a paid subscription) — no scraping, no extra credentials.
- **The GM**: Claude receives your roster, your remaining starting-lineup needs,
  and the merged available-player pool (ESPN + FantasyPros side by side), and
  returns a structured top-3 plus a single decisive recommendation.

> Note on "other public websites": rather than build fragile scrapers against
> sites that can change or block automated access at any time, this app is built
> around two solid, reliable inputs (ESPN + FantasyPros). You can drop in more
> ranking sources later the same way FantasyPros is loaded — as a CSV in `data/`
> — if you want to blend in another site's rankings.

## Setup

### 1. Install dependencies

```bash
cd fantasy-draft-advisor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get your ESPN league info

Open your league in a browser: `https://fantasy.espn.com/football/team?leagueId=...&teamId=...`

- `ESPN_LEAGUE_ID` and `ESPN_TEAM_ID` are both in that URL.
- `ESPN_YEAR` is the season (e.g. `2026`).

**If your league is private** (most are), you also need two cookies:

1. Log into fantasy.espn.com in your browser.
2. Open DevTools → Application/Storage → Cookies → `https://fantasy.espn.com`.
3. Copy the values of `espn_s2` and `SWID` (SWID includes the curly braces, e.g. `{ABC-123...}`).

Public leagues can leave `ESPN_S2` / `ESPN_SWID` blank.

### 3. Get a FantasyPros rankings CSV

On fantasypros.com, open your sport's **Cheat Sheet** (or the ADP page) for the
scoring format you draft with (PPR/Half/Standard). Subscribers get an
**Export to CSV** (or similar) button — use it, then save the file as:

```
fantasy-draft-advisor/data/fantasypros_rankings.csv
```

Re-export and overwrite that file whenever you want fresher rankings (e.g. the
morning of your draft).

### 4. Get a Claude API key

Create a key at [console.anthropic.com](https://console.anthropic.com/) (this is
a separate product from a claude.ai subscription — it's pay-as-you-go by API
usage, typically a few cents per recommendation).

### 5. Configure

```bash
cp .env.example .env
```

Fill in `.env` with the league info, cookies, and API key from the steps above.

### 6. Run

```bash
python app.py
```

Open **http://localhost:5050**.

## Using it on draft day

1. Before your pick, click **Refresh from ESPN** to sync the latest picks/roster.
2. Optionally narrow by position in the **Get My Pick** panel.
3. Click **Ask the GM** — you'll get a team assessment, 3 ranked candidates, and
   one clear "draft this player" recommendation with reasoning.
4. Make your pick in the actual ESPN app, then refresh here before your next turn.

The **Available Players** table below is a searchable/filterable browser of the
full pool (ESPN + FantasyPros side by side) if you want to dig in yourself.

## Limitations to know about

- ESPN's fantasy API is undocumented and unofficial (there's no public/supported
  API for fantasy data) — the `espn_api` library reverse-engineers it, so ESPN
  changes could break it. If refresh fails, the error message will say so.
- FantasyPros rankings are only as fresh as your last CSV export — there's no
  live sync, since that needs their paid API partnership.
- Player name matching between ESPN and FantasyPros is automatic (handles suffixes
  like "II"/"Jr." and D/ST naming differences) but isn't 100% guaranteed on edge
  cases — a player with no FantasyPros match will just show blank FP columns and
  the GM will lean on ESPN's own data for them.
