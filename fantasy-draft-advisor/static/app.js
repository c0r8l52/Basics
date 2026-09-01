const statusEl = document.getElementById("status");
const rosterListEl = document.getElementById("rosterList");
const rosterNeedsEl = document.getElementById("rosterNeeds");
const playersBodyEl = document.getElementById("playersBody");
const recommendOutputEl = document.getElementById("recommendOutput");

let cachedPlayers = [];

function setStatus(text, isError) {
  statusEl.textContent = text;
  statusEl.className = "status" + (isError ? " error" : "");
}

function renderRoster(roster) {
  rosterListEl.innerHTML = "";
  if (!roster.length) {
    rosterListEl.innerHTML = "<li>No players drafted yet.</li>";
    return;
  }
  for (const p of roster) {
    const li = document.createElement("li");
    li.innerHTML = `${p.name} <span class="pos">${p.position} - ${p.pro_team}</span>`;
    rosterListEl.appendChild(li);
  }
}

function renderNeeds(needs) {
  rosterNeedsEl.innerHTML = "";
  const entries = Object.entries(needs || {});
  if (!entries.length) {
    rosterNeedsEl.innerHTML = "<p class='loading'>No roster settings loaded.</p>";
    return;
  }
  for (const [slot, info] of entries) {
    const row = document.createElement("div");
    row.className = "need-row";
    const cls = info.still_needed > 0 ? "unmet" : "met";
    row.innerHTML = `<span>${slot}</span><span class="${cls}">${info.rostered}/${info.required}</span>`;
    rosterNeedsEl.appendChild(row);
  }
}

function renderPlayers(players) {
  playersBodyEl.innerHTML = "";
  for (const p of players) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.name}</td>
      <td>${p.position}</td>
      <td>${p.pro_team}</td>
      <td>${p.injury_status || ""}</td>
      <td>${p.espn_projected_points ?? ""}</td>
      <td>${p.percent_owned ?? ""}</td>
      <td>${p.fp_rank ?? "-"}</td>
      <td>${p.fp_tier ?? "-"}</td>
      <td>${p.fp_adp ?? "-"}</td>
    `;
    playersBodyEl.appendChild(tr);
  }
}

function applyPlayerFilters() {
  const q = document.getElementById("searchBox").value.trim().toLowerCase();
  const pos = document.getElementById("tablePositionFilter").value;
  let filtered = cachedPlayers;
  if (pos) filtered = filtered.filter((p) => p.position === pos);
  if (q) filtered = filtered.filter((p) => p.name.toLowerCase().includes(q));
  renderPlayers(filtered.slice(0, 200));
}

async function loadState() {
  setStatus("loading...");
  const res = await fetch("/api/state");
  const data = await res.json();
  applyState(data);
}

async function refresh() {
  setStatus("refreshing from ESPN...");
  const res = await fetch("/api/refresh", { method: "POST" });
  const data = await res.json();
  applyState(data);
}

function applyState(data) {
  if (data.error) {
    setStatus("ESPN error - see below", true);
    rosterListEl.innerHTML = `<li class="error-box">${data.error}</li>`;
    return;
  }
  const fpNote = data.fantasypros_loaded
    ? "FantasyPros loaded"
    : `FantasyPros CSV not found at ${data.fantasypros_csv_path}`;
  setStatus(`${data.my_roster.length} rostered, ${data.available_players.length} available - ${fpNote}`);
  renderRoster(data.my_roster);
  renderNeeds(data.roster_needs);
  cachedPlayers = data.available_players;
  applyPlayerFilters();
}

async function getRecommendation() {
  const position = document.getElementById("positionFilter").value;
  recommendOutputEl.innerHTML = '<p class="loading">Asking the GM...</p>';
  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position: position || null }),
    });
    const data = await res.json();
    if (!res.ok) {
      recommendOutputEl.innerHTML = `<div class="error-box">${data.error}</div>`;
      return;
    }
    renderRecommendation(data);
  } catch (err) {
    recommendOutputEl.innerHTML = `<div class="error-box">${err}</div>`;
  }
}

function renderRecommendation(data) {
  const rec = data.recommendation;
  const picks = data.top_picks || [];
  const picksHtml = picks
    .sort((a, b) => a.rank - b.rank)
    .map(
      (p) => `
      <li>
        <div class="pick-title">#${p.rank} ${p.player} <span class="pick-meta">${p.position}${p.pro_team ? " - " + p.pro_team : ""}</span></div>
        <div>${p.reasoning}</div>
      </li>`
    )
    .join("");

  recommendOutputEl.innerHTML = `
    ${data.team_assessment ? `<p class="loading">${data.team_assessment}</p>` : ""}
    <div class="rec-card">
      <h3>Draft: ${rec.player} (${rec.position || ""}${rec.pro_team ? " - " + rec.pro_team : ""})</h3>
      <p>${rec.why}</p>
    </div>
    <ul class="pick-list">${picksHtml}</ul>
  `;
}

document.getElementById("refreshBtn").addEventListener("click", refresh);
document.getElementById("recommendBtn").addEventListener("click", getRecommendation);
document.getElementById("searchBox").addEventListener("input", applyPlayerFilters);
document.getElementById("tablePositionFilter").addEventListener("change", applyPlayerFilters);

loadState();
