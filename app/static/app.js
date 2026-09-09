const $ = id => document.getElementById(id);
const ago = iso => { if (!iso) return "—"; const s = (Date.now() - new Date(iso)) / 1e3;
  if (s < 3600) return Math.max(1, Math.round(s / 60)) + "m ago";
  if (s < 86400) return Math.round(s / 3600) + "h ago"; return Math.round(s / 86400) + "d ago"; };
let searches = [], cur = null, sort = "newest", typeF = "";
let charts = {};
function chart(id, cfg) { if (charts[id]) charts[id].destroy(); charts[id] = new Chart($(id), cfg); }
function toast(m) { $("toast").textContent = m; $("toast").classList.remove("hidden");
  setTimeout(() => $("toast").classList.add("hidden"), 3200); }
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }

/* ---------- guide ---------- */
async function loadGuide() {
  const g = await fetch("/api/guide").then(r => r.json());
  $("stepsMini").innerHTML = g.steps.map(s =>
    `<div class="step-mini"><b>${s.n}</b><span>${esc(s.t)}</span></div>`).join("");
  $("guideBody").innerHTML =
    g.sections.map(s => `<div class="card"><h3>${esc(s.t)}</h3><p>${esc(s.body)}</p>
      ${(s.links || []).map(([t, u]) => `<a href="${u}" target="_blank">↗ ${esc(t)}</a>`).join(" · ")}</div>`).join("") +
    `<div class="card"><h3>Job portals (tracked here + manual)</h3>
      <table><thead><tr><th>Portal</th><th>Notes</th></tr></thead><tbody>` +
      g.portals.map(([t, u, n]) => `<tr><td><a href="${u}" target="_blank">${esc(t)} ↗</a></td><td>${esc(n)}</td></tr>`).join("") +
      `</tbody></table></div>
     <div class="card"><h3>Sources</h3><p>` +
      g.sources.map(([t, u]) => `<a href="${u}" target="_blank">↗ ${esc(t)}</a>`).join(" · ") +
      `</p><p class="mut small">Guide curated 2026-09-09 from BAG/PsyKo pages. Verify before acting.</p></div>`;
}

/* ---------- searches ---------- */
async function loadSearches(selectId) {
  searches = await fetch("/api/searches").then(r => r.json());
  if (selectId) cur = selectId;
  if (!cur || !searches.find(s => s.id === cur)) cur = searches[0]?.id ?? null;
  $("searchList").innerHTML = searches.map(s => `
    <div class="search-item ${s.id === cur ? "on" : ""}" data-id="${s.id}">
      <div class="t"><b>${esc(s.name)}</b><span>
        <button class="icon-btn" data-edit="${s.id}">✎</button>
        <button class="icon-btn" data-del="${s.id}">🗑</button></span></div>
      <small>“${esc(s.term)}” · ${s.lang.toUpperCase()} · ${s.pages}p${s.active ? "" : ' · <span class="badge off">paused</span>'}</small>
      <small>${s.last_snapshot ? "last scrape " + ago(s.last_snapshot) : "never scraped"} · ${s.run_count} runs</small>
    </div>`).join("") || "<small>No searches yet — create one.</small>";
  document.querySelectorAll(".search-item").forEach(el => el.addEventListener("click", e => {
    if (e.target.dataset.edit || e.target.dataset.del) return;
    cur = +el.dataset.id; loadSearches(); load();
  }));
  document.querySelectorAll("[data-edit]").forEach(b => b.onclick = e => { e.stopPropagation(); openModal(+b.dataset.edit); });
  document.querySelectorAll("[data-del]").forEach(b => b.onclick = async e => {
    e.stopPropagation();
    if (!confirm("Delete this search and its history?")) return;
    await fetch(`/api/searches/${b.dataset.del}`, { method: "DELETE" });
    if (cur === +b.dataset.del) cur = null;
    toast("Deleted"); loadSearches(); load();
  });
}

async function loadRuns() {
  const runs = await fetch("/api/runs?limit=12").then(r => r.json());
  $("runFeed").innerHTML = runs.map(r => `
    <div class="run"><b>${esc(r.search_name || "")}</b> · ${r.listings ?? "?"} jobs<br>
    <small>${ago(r.finished_at)} · <span style="color:var(--green)">+${r.new_count ?? 0}</span> /
    <span style="color:var(--red)">−${r.removed_count ?? 0}</span></small></div>`).join("")
    || "<small>No runs yet.</small>";
}

/* ---------- jobs ---------- */
async function loadFacets() {
  const f = await fetch(`/api/facets?search_id=${cur}`).then(r => r.json());
  if (f.detail) return;
  $("typeSel").innerHTML = `<option value="">Any contract (${f.total})</option>` +
    (f.types || []).map(t => `<option ${typeF === t.value ? "selected" : ""}>${esc(t.value)} (${t.n})</option>`).join("");
}

async function load() {
  if (!cur) { $("status").textContent = "Create a saved search to begin."; return; }
  await loadFacets();
  $("status").textContent = "loading…";
  const q = $("q").value.trim();
  const p = new URLSearchParams({ search_id: cur, sort, limit: 200 });
  if (q) p.set("q", q);
  if (typeF) p.set("type", typeF);
  const [stats, changes, jobs] = await Promise.all([
    fetch(`/api/stats?search_id=${cur}`).then(r => r.json()),
    fetch(`/api/changes?search_id=${cur}`).then(r => r.json()),
    fetch(`/api/listings?${p}`).then(r => r.json()),
  ]);
  $("status").textContent = stats.latest ? `Snapshot ${ago(stats.latest)} · ${jobs.length} shown` : (stats.detail || "");
  $("dbInfo").textContent = stats.latest ? `latest ${new Date(stats.latest).toLocaleString()}` : "";
  $("kpis").innerHTML = [["Jobs", stats.total ?? "—", ""], ["New", stats.new ?? "—", "good"],
    ["Back", stats.returning ?? "—", ""], ["Gone", stats.removed ?? "—", "bad"],
    ["Watching", stats.removed_watch ?? "—", "warn"],
  ].map(([k, v, c]) => `<div class="kpi ${c}"><span>${k}</span><b>${v}</b></div>`).join("");
  const t = stats.trend || [];
  chart("chTrend", { type: "bar",
    data: { labels: t.map(x => new Date(x.scraped_at).toLocaleDateString()),
      datasets: [{ data: t.map(x => x.n), backgroundColor: "#4da3ff" }] },
    options: { plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#8fa0bb" } }, y: { ticks: { color: "#8fa0bb" } } } } });
  $("trendNote").textContent = t.length < 2 ? "Run 2+ scrapes to see the trend." : `${t.length} snapshots`;
  chart("chType", { type: "doughnut",
    data: { labels: (stats.by_type || []).map(x => `${x.employment_type || "?"} (${x.n})`),
      datasets: [{ data: (stats.by_type || []).map(x => x.n),
        backgroundColor: ["#4da3ff", "#34d399", "#fbbf24", "#f87171", "#a78bfa"] }] },
    options: { plugins: { legend: { position: "right", labels: { color: "#e9eef7", boxWidth: 12 } } } } });
  const n = changes.new || [], ret = changes.returning || [],
        remC = changes.removed_confirmed || [], remW = changes.removed_watch || [];
  $("cntChg").textContent = n.length + ret.length + remC.length + remW.length;
  $("nNew").textContent = `(${n.length})`; $("nRet").textContent = `(${ret.length})`;
  $("nRem").textContent = `(${remC.length + remW.length})`;
  feed($("lNew"), n, j => jobRow(j, "first time seen"));
  feed($("lRet"), ret, j => jobRow(j, "back in results"));
  feed($("lRem"), [...remC.map(j => [j, "likely filled"]), ...remW.map(j => [j, "left window — watching"])],
    ([j, tag]) => jobRow(j, tag));
  $("cntJobs").textContent = jobs.length;
  $("cards").innerHTML = jobs.map(j => `
    <div class="prop" data-open="${j.ext_id}">
      <div class="body"><div class="price-row"><span class="price" style="font-size:15px">${esc(j.title)}</span></div>
        <div class="addr">${esc(j.company)} · ${esc(j.city)}${j.postcode ? " " + esc(j.postcode) : ""}</div>
        <div class="meta"><span>${esc(j.employment_type || "")}</span><span>${j.posted_date ? "posted " + j.posted_date.slice(0, 10) : ""}</span></div>
        <div class="status">${esc((j.description || "").slice(0, 140))}…</div></div>
    </div>`).join("") || `<div class="empty">No jobs match.</div>`;
  document.querySelectorAll("#cards [data-open]").forEach(el => el.onclick = () => openDrawer(el.dataset.open));
}

function jobRow(j, tag) {
  return `<div data-open="${j.ext_id}"><b>${esc(j.title)}</b> — ${esc(j.company)} · ${esc(j.city)}<br><small>${esc(j.employment_type || "")} · ${tag}</small></div>`;
}
function feed(el, items, fn) {
  el.innerHTML = items.slice(0, 60).map(x => `<li>${fn(x)}</li>`).join("") || "<li><small>none</small></li>";
  el.querySelectorAll("[data-open]").forEach(n => n.onclick = () => openDrawer(n.dataset.open));
}

async function openDrawer(id) {
  $("drawerWrap").classList.remove("hidden");
  $("drawerBody").innerHTML = "loading…";
  const r = await fetch(`/api/job/${id}?search_id=${cur}`).then(r => r.json());
  const j = r.job;
  if (!j) { $("drawerBody").innerHTML = "Not found."; return; }
  $("drawerBody").innerHTML = `
    <h2 style="margin:6px 0">${esc(j.title)}</h2>
    <div style="color:var(--mut)">${esc(j.company)} · ${esc(j.city)}${j.postcode ? " " + esc(j.postcode) : ""}${j.region ? ", " + esc(j.region) : ""}</div>
    <div class="row" style="margin-top:10px">
      <div class="kv"><span>Contract</span><b style="font-size:13px">${esc(j.employment_type || "—")}</b></div>
      <div class="kv"><span>Posted</span><b style="font-size:13px">${esc((j.posted_date || "").slice(0, 10))}</b></div>
      <div class="kv"><span>Seen</span><b>${r.sightings}×</b></div>
    </div>
    <h4>Description</h4><p class="desc">${esc(j.description || "")}</p>
    <a href="${j.url}" target="_blank">Open on jobup.ch ↗</a>
    <div style="color:var(--mut);font-size:12px;margin-top:4px">first seen ${r.first_seen ? ago(r.first_seen) : "—"} · last seen ${r.last_seen ? ago(r.last_seen) : "—"}</div>`;
}
$("drawerClose").onclick = $("drawerBg").onclick = () => $("drawerWrap").classList.add("hidden");

/* ---------- tabs / filters ---------- */
document.querySelectorAll(".tabs-v button, .tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll(".tabs-v button").forEach(x => x.classList.remove("on")); b.classList.add("on");
  document.querySelectorAll(".tab").forEach(t => t.classList.add("hidden"));
  $("tab-" + b.dataset.tab).classList.remove("hidden");
});
let deb;
$("q").addEventListener("input", () => {
  $("qClear").classList.toggle("hidden", !$("q").value);
  clearTimeout(deb); deb = setTimeout(load, 350);
});
$("qClear").onclick = () => { $("q").value = ""; $("qClear").classList.add("hidden"); load(); };
$("sortSel").onchange = () => { sort = $("sortSel").value; load(); };
$("typeSel").onchange = () => { typeF = $("typeSel").value; load(); };
document.addEventListener("keydown", e => { if (e.key === "Escape") ["drawerWrap", "modalWrap"].forEach(id => $(id).classList.add("hidden")); });

/* ---------- scrape (blocking overlay) ---------- */
let scrapeTimer = null, scrapeStart = 0;
function scrapeShow(title) {
  $("scrapeOverlay").classList.remove("hidden");
  $("scrapeSpinner").className = "spinner";
  $("scrapeTitle").textContent = title;
  $("scrapeMsg").textContent = "Fetching jobup.ch…";
  $("scrapeResult").classList.add("hidden"); $("scrapeResult").innerHTML = "";
  $("scrapeDismiss").classList.add("hidden");
  scrapeStart = Date.now();
  clearInterval(scrapeTimer);
  scrapeTimer = setInterval(() => { $("scrapeElapsed").textContent = `${Math.round((Date.now() - scrapeStart) / 1000)}s elapsed`; }, 1000);
  document.body.style.overflow = "hidden";
}
function scrapeFinish(ok, html) {
  clearInterval(scrapeTimer);
  $("scrapeSpinner").className = "spinner " + (ok ? "done" : "failed");
  $("scrapeTitle").textContent = ok ? "Scrape complete" : "Scrape failed";
  $("scrapeResult").innerHTML = html; $("scrapeResult").classList.remove("hidden");
  $("scrapeDismiss").classList.remove("hidden");
  document.body.style.overflow = "";
}
$("scrapeDismiss").onclick = () => $("scrapeOverlay").classList.add("hidden");
async function scrape(url, label) {
  scrapeShow(label || "Scraping…");
  try {
    const r = await fetch(url, { method: "POST" }).then(r => r.json());
    const rows = r.searches || [r];
    const bad = rows.filter(x => x.error);
    scrapeFinish(!bad.length, rows.map(x => x.error
      ? `<div><b>${esc(x.name || "")}</b>: <span class="bad">${esc(x.error)}</span></div>`
      : `<div><b>${esc(x.name || "")}</b>: <span class="ok">${x.listings} jobs · +${x.new} new · −${x.removed} gone</span></div>`).join(""));
  } catch (e) { scrapeFinish(false, `<div class="bad">${esc(String(e))}</div>`); }
  loadSearches(); loadRuns(); load();
}
$("btnScrapeAll").onclick = () => scrape("/api/scrape", "Scraping all active searches…");
$("btnScrapeOne").onclick = () => cur ? scrape(`/api/scrape?search_id=${cur}`, "Scraping this search…") : toast("Pick a search first");

/* ---------- modal ---------- */
function openModal(id) {
  $("modalWrap").classList.remove("hidden");
  const s = searches.find(x => x.id === id);
  $("modalTitle").textContent = s ? "Edit saved search" : "New saved search";
  $("fId").value = s?.id ?? ""; $("fName").value = s?.name ?? "";
  $("fTerm").value = s?.term ?? ""; $("fLang").value = s?.lang ?? "en";
  $("fPages").value = s?.pages ?? 2; $("fActive").checked = s ? !!s.active : true;
}
$("btnNew").onclick = () => openModal(null);
$("modalCancel").onclick = () => $("modalWrap").classList.add("hidden");
document.querySelector("[data-close]").onclick = () => $("modalWrap").classList.add("hidden");
$("modalSave").onclick = async () => {
  const id = $("fId").value;
  const body = { name: $("fName").value.trim() || "Untitled", term: $("fTerm").value.trim() || "psychology",
    lang: $("fLang").value, pages: Math.max(1, Math.min(10, +$("fPages").value || 2)), active: $("fActive").checked };
  const r = await fetch(id ? `/api/searches/${id}` : "/api/searches",
    { method: id ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const saved = await r.json();
  if (!r.ok) { toast(saved.error || "Save failed"); return; }
  $("modalWrap").classList.add("hidden"); cur = saved.id;
  await loadSearches(cur); scrape(`/api/scrape?search_id=${saved.id}`, `Scraping “${saved.name}”…`);
};

(async function init() { await loadGuide(); await loadSearches(); await loadRuns(); load(); })();
