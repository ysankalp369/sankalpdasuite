/* Redevelopment DA Suite – single-page interface (no build step). */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let TOKEN = null, ME = null, SCHEMA = null;
try { TOKEN = sessionStorage.getItem("da_token"); } catch (e) { }

async function api(path, opts = {}) {
  const headers = opts.headers || {};
  if (TOKEN) headers.Authorization = "Bearer " + TOKEN;
  if (opts.json !== undefined) { headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(opts.json); }
  const r = await fetch(path, { ...opts, headers });
  if (r.status === 401) { showLogin(); throw new Error("Please sign in"); }
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (e) { } throw new Error(m); }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
function toast(msg, err) { const t = $("#toast"); t.textContent = msg; t.className = "toast" + (err ? " err" : ""); clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), 4500); }
async function download(url) {
  try {
    const r = await api(url); const blob = await r.blob();
    const cd = r.headers.get("content-disposition") || ""; const m = /filename\*=UTF-8''([^;]+)/.exec(cd);
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = m ? decodeURIComponent(m[1]) : "download";
    document.body.appendChild(a); a.click(); a.remove();
  } catch (e) { toast(e.message, true); }
}
const can = p => ME && ME.permissions.includes(p);
const pill = (s, cls) => `<span class="pill ${cls || "s-" + s}">${esc(String(s).replace("_", " "))}</span>`;
const sev = s => `<span class="pill sev-${esc(s)}">${esc(s)}</span>`;
const fmtDate = s => s ? new Date(s + (s.endsWith("Z") ? "" : "Z")).toLocaleString() : "";
const loading = () => `<p><span class="spin"></span> Working…</p>`;
function busy(btn, on) { if (!btn) return; btn.disabled = on; if (on) { btn._t = btn.innerHTML; btn.innerHTML = '<span class="spin"></span> ' + btn._t; } else if (btn._t) btn.innerHTML = btn._t; }

/* ---------------------------------------------------------------- auth */
function showLogin() { TOKEN = null; try { sessionStorage.removeItem("da_token"); } catch (e) { } $("#app").classList.add("hidden"); $("#login").classList.remove("hidden"); }
$("#loginForm").addEventListener("submit", async e => {
  e.preventDefault(); const f = new FormData(e.target);
  try {
    const r = await api("/api/login", { method: "POST", json: { username: f.get("username"), password: f.get("password") } });
    TOKEN = r.token; try { sessionStorage.setItem("da_token", TOKEN); } catch (e) { }
    $("#loginErr").textContent = ""; boot();
  } catch (err) { $("#loginErr").textContent = err.message; }
});
async function boot() {
  if (!TOKEN) return showLogin();
  try { ME = await api("/api/me"); SCHEMA = SCHEMA || await api("/api/schema"); } catch (e) { return; }
  $("#login").classList.add("hidden"); $("#app").classList.remove("hidden");
  $("#who").innerHTML = `<b>${esc(ME.full_name || ME.username)}</b>${esc(ME.role_label)}<br><a href="#/account">Account</a> · <a href="#" id="logout">Sign out</a>
    <div class="small" style="margin-top:6px">Claude AI: ${ME.ai_available ? "enabled" : "not configured"}</div>`;
  $("#logout").onclick = e => { e.preventDefault(); showLogin(); };
  $("#navAdmin").classList.toggle("hidden", !can("users.manage"));
  route();
}
window.addEventListener("hashchange", route);

/* ---------------------------------------------------------------- router */
const ROUTES = [
  [/^#?\/?$/, dashboard], [/^#\/new$/, newProject], [/^#\/projects$/, projectList], [/^#\/project\/(\d+)(?:\/(\w+))?$/, projectView],
  [/^#\/annexures$/, annexures], [/^#\/pending$/, pendingView], [/^#\/review$/, reviewHome], [/^#\/review\/(\d+)$/, reviewView],
  [/^#\/compare$/, compareView], [/^#\/clauses$/, clausesView], [/^#\/references$/, referencesView], [/^#\/legal$/, legalView],
  [/^#\/generated$/, generatedView], [/^#\/history$/, historyView], [/^#\/admin$/, adminView], [/^#\/account$/, accountView],
];
async function route() {
  if (!ME) return;
  const h = location.hash || "#/";
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("active", h === a.getAttribute("href") || (a.getAttribute("href") !== "#/" && h.startsWith(a.getAttribute("href")))));
  for (const [rx, fn] of ROUTES) { const m = rx.exec(h); if (m) { $("#main").innerHTML = loading(); try { await fn(...m.slice(1)); } catch (e) { $("#main").innerHTML = `<p class="err">${esc(e.message)}</p>`; } return; } }
  $("#main").innerHTML = "<p>Not found</p>";
}

/* ---------------------------------------------------------------- dashboard */
async function dashboard() {
  const d = await api("/api/dashboard");
  const tiles = [["#/new", "Create New Development Agreement", "Upload project documents → extract → resolve gaps → generate DA, schedules, annexures and PAAAs."],
  ["#/review", "Review Existing Development Agreement", "Upload a developer / third-party DA → genuine Word Track Changes, clean copy and 6 reports."],
  ["#/projects", "Project Database", `${d.projects} project(s)`], ["#/clauses", "Clause Library", `${d.clauses} clauses · ${d.clauses_pending} pending approval`],
  ["#/annexures", "Annexure Generator", "Schedules, BG format, PAAA, vacation undertaking, POA."], ["#/legal", "Legal Research", "Statute & circular register with verification status."],
  ["#/compare", "Document Comparison", "Redline any two versions of a DA."], ["#/pending", "Pending Information", `${d.pending_items} critical item(s) across projects`],
  ["#/generated", "Generated Documents", `${d.generated} file(s)`], ["#/history", "Project History", "Complete audit trail."]];
  $("#main").innerHTML = `<h1>Dashboard</h1><p class="sub">Society-side redevelopment drafting and review – Maharashtra / Navi Mumbai (CIDCO · NMMC · UDCPR · MahaRERA)</p>
  <div class="grid g4">${tiles.map(t => `<div class="card tile" onclick="location.hash='${t[0]}'"><h3>${t[1]}</h3><div class="muted small">${esc(t[2])}</div></div>`).join("")}</div>
  <h2>Recent projects</h2>${projTable(d.recent)}
  <p class="small muted">${d.references} reference agreement(s) in the knowledge base. ${d.ai_available ? "" : "Claude AI is not configured – deterministic engines are in use."}</p>`;
}
function projTable(rows) {
  if (!rows.length) return `<div class="card muted">No projects yet. <a href="#/new">Create one</a>.</div>`;
  return `<div class="tbl"><table><tr><th>Project</th><th>Society</th><th>Developer</th><th>Units</th><th>Docs</th><th>Critical missing</th><th>Conflicts</th><th>Status</th><th>Updated</th></tr>
  ${rows.map(p => `<tr><td><a href="#/project/${p.id}">${esc(p.name)}</a></td><td>${esc(p.society || "—")}</td><td>${esc(p.developer || "—")}</td><td>${p.units}</td><td>${p.documents}</td>
  <td>${p.critical_missing ? pill(p.critical_missing, "s-missing") : pill(0, "s-pass")}</td><td>${p.conflicts ? pill(p.conflicts, "s-conflict") : "0"}</td><td>${esc(p.status)}</td><td class="small">${fmtDate(p.updated_at)}</td></tr>`).join("")}</table></div>`;
}

/* ---------------------------------------------------------------- projects */
async function newProject() {
  $("#main").innerHTML = `<h1>Create New Development Agreement</h1><p class="sub">Start a project workspace, then upload the society, property, member, developer and technical documents. Information already in the documents is extracted automatically.</p>
  <div class="card" style="max-width:620px"><label>Project name<input id="pn" placeholder="e.g. Redevelopment – XYZ CHSL, Sector 9, Vashi"></label>
  <button class="btn primary" id="mk">Create project workspace</button></div>`;
  $("#mk").onclick = async () => { const n = $("#pn").value.trim(); if (!n) return toast("Enter a project name", true);
    try { const p = await api("/api/projects", { method: "POST", json: { name: n } }); location.hash = `#/project/${p.id}/documents`; } catch (e) { toast(e.message, true); } };
}
async function projectList() { const rows = await api("/api/projects"); $("#main").innerHTML = `<div class="row"><h1>Project Database</h1><span class="spacer"></span><a class="btn primary" href="#/new">New project</a></div>${projTable(rows)}`; }

const TABS = [["overview", "Overview"], ["documents", "Documents"], ["data", "Project Data"], ["members", "Members & Units"], ["gaps", "Gaps & Conflicts"], ["generate", "Validate & Generate"], ["versions", "Versions & History"]];
async function projectView(id, tab = "overview") {
  const P = await api(`/api/projects/${id}`);
  const head = `<div class="row"><h1>${esc(P.summary.name)}</h1><span class="spacer"></span>${pill(P.summary.status, "s-verify")}</div>
  <p class="sub">${esc(P.summary.society || "Society not identified")} · ${esc(P.summary.developer || "Developer not identified")}</p>
  <div class="tabs">${TABS.map(([k, l]) => `<a href="#/project/${id}/${k}" class="${k === tab ? "on" : ""}">${l}</a>`).join("")}</div><div id="tab"></div>`;
  $("#main").innerHTML = head;
  await ({ overview: tOverview, documents: tDocs, data: tData, members: tMembers, gaps: tGaps, generate: tGenerate, versions: tVersions }[tab] || tOverview)(P, id);
}
function tOverview(P, id) {
  const s = P.summary, d = P.data, v = k => d[k]?.value ?? "—";
  $("#tab").innerHTML = `<div class="grid g4">
  <div class="card"><div class="muted small">Documents</div><div class="kpi">${s.documents}</div></div><div class="card"><div class="muted small">Units in register</div><div class="kpi">${s.units}</div></div>
  <div class="card"><div class="muted small">Critical fields missing</div><div class="kpi">${s.critical_missing}</div></div><div class="card"><div class="muted small">Conflicts to verify</div><div class="kpi">${s.conflicts}</div></div></div>
  <div class="grid g3" style="margin-top:14px">
  <div class="card"><h3>Society</h3>${kv(d, ["society.name", "society.reg_no", "society.chairman", "society.secretary", "society.order_79a_date"])}</div>
  <div class="card"><h3>Property</h3>${kv(d, ["property.plot_no", "property.sector", "property.node", "property.plot_area_sqm", "property.units_count", "property.members_count"])}</div>
  <div class="card"><h3>Developer & PMC</h3>${kv(d, ["developer.name", "developer.cin", "developer.pan", "pmc.name", "legal.name"])}</div>
  <div class="card"><h3>Commercial terms</h3>${kv(d, ["comm.rent_monthly", "comm.rent_escalation_percent", "comm.brokerage", "comm.shifting", "comm.corpus", "security.bg_amount"])}</div>
  <div class="card"><h3>Timeline</h3>${kv(d, ["time.approval_months", "time.construction_months", "time.grace_months", "time.longstop_months", "time.dlp_years"])}</div>
  <div class="card"><h3>Next steps</h3><ol class="small"><li><a href="#/project/${id}/documents">Upload documents</a></li><li><a href="#/project/${id}/gaps">Resolve gaps & conflicts</a></li><li><a href="#/project/${id}/members">Check member register</a></li><li><a href="#/project/${id}/generate">Validate & generate</a></li></ol></div></div>`;
}
function kv(d, keys) { return `<table>${keys.map(k => { const f = SCHEMA.fields.find(x => x.key === k); const e = d[k] || {}; return `<tr><td class="small muted">${esc(f?.label || k)}</td><td>${esc(fmtVal(e.value))} ${pill(e.status || "missing")}</td></tr>`; }).join("")}</table>`; }
function fmtVal(v) { if (v == null || v === "") return "—"; if (Array.isArray(v)) return v.map(x => typeof x === "object" ? `${x.milestone}: ${x.amount}` : x).join("; "); return String(v); }

async function tDocs(P, id) {
  const cats = SCHEMA.doc_categories;
  $("#tab").innerHTML = `<div class="grid g2"><div class="card"><h3>Upload documents</h3>
  <label>Category<select id="cat">${Object.entries(cats).map(([k, l]) => `<option value="${k}">${l}</option>`).join("")}</select></label>
  <div class="drop" id="drop">Drop PDF / DOCX / XLSX / scanned PDF / images here, or <a href="#" id="pick">choose files</a><input type="file" id="files" multiple class="hidden" accept=".pdf,.docx,.xlsx,.xlsm,.csv,.png,.jpg,.jpeg,.tif,.tiff,.txt"></div>
  ${ME.ai_available ? `<label class="row" style="margin-top:8px"><input type="checkbox" id="useai" style="width:auto"> Also extract with Claude (facts are verified against quoted text)</label>` : ""}
  <p class="small muted">Scanned pages are OCR-read; OCR facts are marked “verify”. Each fact keeps its document, page and paragraph reference.</p><div id="upres"></div></div>
  <div class="card"><h3>What to upload</h3><p class="small">A. Society: registration, bye-laws, SGBM notices/minutes, 79A order, PMC & legal appointments, tender, comparative report, accepted offer, appointment letter.<br>
  B. Property: CIDCO agreement to lease, lease deed, NOCs, plans, existing OC, structural audit, tax/dues, litigation, encumbrances.<br>C. Members: member register (XLSX preferred), share certificates, mortgages / bank NOCs, consents, heirship.<br>
  D. Developer: incorporation, PAN/GST, board resolution, financials, net-worth, solvency, experience, RERA, litigation, final offer.<br>E. Technical: feasibility, FSI, area statement, rehab/free-sale allocation, specifications, schedule.</p></div></div>
  <h2>Project documents</h2><div class="tbl"><table><tr><th>File</th><th>Category</th><th>Identified as</th><th>Pages</th><th>OCR</th><th>Facts</th><th>Units</th><th>Uploaded</th><th></th></tr>
  ${P.documents.map(d => `<tr><td><a href="#" data-doc="${d.id}">${esc(d.filename)}</a></td><td>${esc(d.category)}</td><td>${esc(d.doc_type_label)}</td><td>${d.pages}</td><td>${d.ocr_used ? "yes" : ""}</td>
  <td>${d.meta?.facts ?? ""}</td><td>${d.meta?.units || ""}</td><td class="small">${fmtDate(d.uploaded_at)}</td><td><button class="btn sm" data-dl="${d.id}">Original</button></td></tr>`).join("") || `<tr><td colspan=9 class="muted">No documents yet.</td></tr>`}</table></div><div id="docdetail"></div>`;
  const send = async files => {
    if (!files.length) return; const fd = new FormData(); fd.append("category", $("#cat").value); fd.append("use_ai", $("#useai")?.checked ? "true" : "false");
    [...files].forEach(f => fd.append("files", f)); $("#upres").innerHTML = loading();
    try { const r = await api(`/api/projects/${id}/documents`, { method: "POST", body: fd });
      $("#upres").innerHTML = r.map(d => d.error ? `<div class="err">${esc(d.filename)}: ${esc(d.error)}</div>` : `<div class="small">✓ ${esc(d.filename)} → ${esc(d.doc_type_label)} (${d.meta?.facts || 0} facts, ${d.meta?.units || 0} units${d.ocr_used ? ", OCR" : ""})</div>`).join("");
      setTimeout(() => projectView(id, "documents"), 1200); } catch (e) { $("#upres").innerHTML = `<p class="err">${esc(e.message)}</p>`; } };
  const drop = $("#drop"); $("#pick").onclick = e => { e.preventDefault(); $("#files").click(); }; $("#files").onchange = e => send(e.target.files);
  drop.ondragover = e => { e.preventDefault(); drop.classList.add("over"); }; drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = e => { e.preventDefault(); drop.classList.remove("over"); send(e.dataTransfer.files); };
  document.querySelectorAll("[data-dl]").forEach(b => b.onclick = () => download(`/api/documents/${b.dataset.dl}/download`));
  document.querySelectorAll("[data-doc]").forEach(a => a.onclick = async e => { e.preventDefault(); const r = await api(`/api/documents/${a.dataset.doc}`);
    $("#docdetail").innerHTML = `<h2>Extracted from ${esc(r.document.filename)}</h2><div class="tbl"><table><tr><th>Field</th><th>Value</th><th>Category</th><th>Page / para</th><th>Method</th><th>Source text</th></tr>
    ${r.facts.map(f => `<tr><td>${esc(f.label)}</td><td><b>${esc(f.value)}</b></td><td>${esc(f.category)}</td><td>p.${f.page ?? "?"} ¶${f.paragraph ?? "?"}</td><td>${esc(f.method)}</td><td class="small">…${esc(f.snippet)}…</td></tr>`).join("") || `<tr><td colspan=6 class="muted">No facts matched.</td></tr>`}</table></div>`;
    $("#docdetail").scrollIntoView({ behavior: "smooth" }); });
}

function fieldInput(f, v) {
  const val = v == null ? "" : (Array.isArray(v) || typeof v === "object" ? JSON.stringify(v) : v);
  if (f.choices?.length) return `<select data-k="${f.key}"><option value=""></option>${f.choices.map(c => `<option ${c === val ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>`;
  if (f.type === "longtext" || f.type === "list") return `<textarea data-k="${f.key}" placeholder="${f.type === "list" ? (f.key === "security.bg_milestones" ? 'JSON e.g. [{"milestone":"Plinth","amount":5000000}]' : "One item per line") : ""}">${esc(f.type === "list" && Array.isArray(v) && f.key !== "security.bg_milestones" ? v.join("\n") : val)}</textarea>`;
  return `<input data-k="${f.key}" value="${esc(val)}" ${f.type === "date" ? 'type="date"' : ""}>`;
}
function parseInput(f, raw) {
  if (raw === "") return null;
  if (f.key === "security.bg_milestones") return JSON.parse(raw);
  if (f.type === "list") return raw.split("\n").map(x => x.trim()).filter(Boolean);
  if (["int", "months", "years"].includes(f.type)) return parseInt(raw.replace(/,/g, ""), 10);
  if (["money", "number", "percent", "area_sqm", "area_sqft"].includes(f.type)) return parseFloat(raw.replace(/,/g, ""));
  return raw;
}
async function tData(P, id) {
  const groups = SCHEMA.groups;
  $("#tab").innerHTML = `<p class="small legend"><span>${pill("confirmed")}</span><span>${pill("extracted")} found in a document</span><span>${pill("verify")} OCR / weak source</span><span>${pill("conflict")} documents disagree</span><span>${pill("missing")}</span><span>${pill("na")} not applicable</span></p>
  <div class="row"><select id="grp" style="width:auto">${groups.map(g => `<option>${g}</option>`).join("")}</select><span class="spacer"></span><span class="small muted">Values are saved per field. Saving marks a value “confirmed”.</span></div><div id="flds"></div>`;
  const draw = () => {
    const g = $("#grp").value;
    $("#flds").innerHTML = `<div class="tbl"><table><tr><th style="width:24%">Field</th><th style="width:34%">Value</th><th>Status / sources</th><th></th></tr>${SCHEMA.fields.filter(f => f.group === g).map(f => {
      const e = P.data[f.key] || {};
      return `<tr><td>${esc(f.label)}${f.critical ? ' <span class="pill s-missing">critical</span>' : ""}<div class="src">${esc(f.help || "")}</div></td><td>${fieldInput(f, e.value)}</td>
      <td>${pill(e.status || "missing")} <div class="src">${esc(e.note || "")}</div>${(e.sources || []).slice(0, 3).map(s => `<div class="src">${esc(s.doc || "")}${s.page ? ` p.${s.page}` : ""}${s.para ? ` ¶${s.para}` : ""}${s.snippet ? ` – “${esc(s.snippet.slice(0, 90))}…”` : ""}</div>`).join("")}
      ${(e.candidates || []).map(c => `<div class="cand"><b>${esc(fmtVal(c.display || c.value))}</b> ${c.label ? `<i>(${esc(c.label)})</i>` : ""} <button class="btn sm" data-use="${f.key}" data-v='${esc(JSON.stringify(c.value))}'>Use this</button>${(c.sources || []).map(s => `<div class="src">${esc(s.doc)} p.${s.page ?? "?"} ¶${s.para ?? "?"} – “${esc((s.snippet || "").slice(0, 90))}”</div>`).join("")}</div>`).join("")}</td>
      <td><button class="btn sm primary" data-save="${f.key}">Save</button> <button class="btn sm" data-na="${f.key}">N/A</button></td></tr>`; }).join("")}</table></div>`;
    const put = async (k, value, status) => { try { await api(`/api/projects/${id}/fields/${encodeURIComponent(k)}`, { method: "PUT", json: { value, status } }); toast("Saved"); P = await api(`/api/projects/${id}`); draw(); } catch (e) { toast(e.message, true); } };
    document.querySelectorAll("[data-save]").forEach(b => b.onclick = () => { const f = SCHEMA.fields.find(x => x.key === b.dataset.save); const el = document.querySelector(`[data-k="${f.key}"]`);
      try { put(f.key, parseInput(f, el.value.trim()), "confirmed"); } catch (e) { toast("Invalid value: " + e.message, true); } });
    document.querySelectorAll("[data-na]").forEach(b => b.onclick = () => put(b.dataset.na, null, "na"));
    document.querySelectorAll("[data-use]").forEach(b => b.onclick = () => put(b.dataset.use, JSON.parse(b.dataset.v), "confirmed"));
  };
  $("#grp").onchange = draw; draw();
}

const UCOLS = [["unit_no", "Unit"], ["building", "Bldg"], ["floor", "Floor"], ["unit_type", "Type"], ["holders", "Member(s)"], ["existing_rera_carpet_sqft", "Existing RERA sq.ft"], ["existing_mofa_carpet_sqft", "MOFA sq.ft"],
["new_rera_carpet_sqft", "New RERA sq.ft"], ["balcony_sqft", "Balcony"], ["parking", "Parking"], ["monthly_rent", "Rent (override)"], ["mortgage", "Mortgage / lender"], ["status", "Status"], ["consent", "Consent"], ["notes", "Notes"]];
async function tMembers(P, id) {
  const U = P.units, names = new Set();
  U.forEach(u => (u.holders || []).forEach(h => h.status !== "deceased" && names.add((h.name || "").toLowerCase().replace(/[^a-z]/g, ""))));
  $("#tab").innerHTML = `<div class="row"><div class="card"><b>${U.length}</b> units · <b>${names.size}</b> distinct living members · <b>${U.filter(u => (u.holders || []).length > 1).length}</b> jointly held · <b>${U.filter(u => u.status !== "regular").length}</b> with status issues</div>
  <span class="spacer"></span><button class="btn" id="addu">Add unit</button></div><p class="small muted">Units and members are counted separately – one member may hold several units, and a unit may have joint holders. Holders: separate names with “ / ”; prefix “Late ” for deceased.</p>
  <div class="tbl"><table><tr>${UCOLS.map(c => `<th>${c[1]}</th>`).join("")}<th></th></tr>${U.map(u => `<tr data-u="${u.id}">${UCOLS.map(([k]) => `<td><input data-f="${k}" value="${esc(k === "holders" ? (u.holders || []).map(h => (h.status === "deceased" ? "Late " : "") + h.name).join(" / ") : (u[k] ?? ""))}" style="min-width:${k === "holders" || k === "notes" ? 200 : 70}px"></td>`).join("")}
  <td><button class="btn sm primary" data-su="${u.id}">Save</button> <button class="btn sm" data-du="${u.id}">✕</button></td></tr>`).join("")}</table></div>`;
  const collect = tr => { const o = {}; tr.querySelectorAll("[data-f]").forEach(i => { const k = i.dataset.f, v = i.value.trim();
    if (k === "holders") o.holders = v ? v.split(/\s*\/\s*/).map(n => ({ name: n.replace(/^late\.?\s+/i, ""), status: /^late\b/i.test(n) ? "deceased" : "alive" })) : [];
    else o[k] = v === "" ? null : v; }); return o; };
  document.querySelectorAll("[data-su]").forEach(b => b.onclick = async () => { try { await api(`/api/units/${b.dataset.su}`, { method: "PUT", json: { data: collect(b.closest("tr")) } }); toast("Unit saved"); } catch (e) { toast(e.message, true); } });
  document.querySelectorAll("[data-du]").forEach(b => b.onclick = async () => { if (!confirm("Delete this unit from the register?")) return; await api(`/api/units/${b.dataset.du}`, { method: "DELETE" }); projectView(id, "members"); });
  $("#addu").onclick = async () => { await api(`/api/projects/${id}/units`, { method: "POST", json: { data: { unit_no: "NEW" } } }); projectView(id, "members"); };
}
async function tGaps(P, id) {
  const g = await api(`/api/projects/${id}/gaps`);
  const sec = (title, rows, kind) => `<h2>${title} (${rows.length})</h2>${rows.length ? `<div class="tbl"><table><tr><th>Field</th><th>Group</th><th>Critical</th><th>Detail</th></tr>${rows.map(r => `<tr><td><a href="#/project/${id}/data">${esc(r.label)}</a></td><td>${esc(r.group)}</td><td>${r.critical ? "Yes" : ""}</td><td>${kind === "conflict" ? r.candidates.map(c => `<div class="cand"><b>${esc(fmtVal(c.display || c.value))}</b>${(c.sources || []).map(s => `<div class="src">${esc(s.doc)} p.${s.page ?? "?"} ¶${s.para ?? "?"}</div>`).join("")}</div>`).join("") : kind === "verify" ? esc(fmtVal(r.value)) : ""}</td></tr>`).join("")}</table></div>` : `<p class="muted">None.</p>`}`;
  $("#tab").innerHTML = `<p class="sub">The system never chooses between contradictory values. Resolve conflicts and confirm extracted values in <a href="#/project/${id}/data">Project Data</a>.</p>
  ${sec("Contradictory information", g.conflict, "conflict")}${sec("Critical information missing", g.missing.filter(x => x.critical), "missing")}${sec("Information requiring verification", g.verify, "verify")}
  <h2>Member register issues (${g.member_issues.length})</h2>${g.member_issues.length ? `<div class="tbl"><table><tr><th>Unit</th><th>Issue</th></tr>${g.member_issues.map(m => `<tr><td>${esc(m.unit)}</td><td>${esc(m.issue)}</td></tr>`).join("")}</table></div>` : "<p class='muted'>None.</p>"}
  ${sec("Other missing information", g.missing.filter(x => !x.critical), "missing")}${sec("Marked not applicable", g.na, "na")}`;
}
async function tGenerate(P, id) {
  $("#tab").innerHTML = loading();
  const v = await api(`/api/projects/${id}/validate`);
  const s = v.summary;
  $("#tab").innerHTML = `<div class="card"><div class="row"><div><b>${s.pass}</b> passed · <b>${s.fail}</b> failed · <b>${s.warn}</b> warnings · <b>${v.outstanding.length}</b> outstanding fields (${v.outstanding.filter(o => o.critical).length} critical)</div><span class="spacer"></span>
  ${s.execution_ready ? pill("execution-ready (subject to advocate review)", "s-pass") : pill("draft only – not for execution", "s-fail")}</div>
  <p class="small muted">Drafts with unresolved critical items are generated with a “DRAFT – NOT FOR EXECUTION” banner, yellow [●] markers for outstanding information and turquoise highlighting for unverified extracted values.</p>
  <div class="row">${can("draft.generate") ? `<button class="btn gold" id="gen">Generate DA + schedules + annexures + PAAAs + validation report</button>` : `<span class="muted">Your role cannot generate drafts.</span>`}</div><div id="genres"></div></div>
  <h2>Validation checks</h2><div class="tbl"><table><tr><th>Result</th><th>Severity</th><th>Category</th><th>Check</th></tr>${v.checks.sort((a, b) => (a.status === "pass") - (b.status === "pass")).map(c => `<tr><td>${pill(c.status)}</td><td>${sev(c.severity)}</td><td>${esc(c.category)}</td><td>${esc(c.message)}</td></tr>`).join("")}</table></div>
  <h2>Outstanding information</h2><div class="tbl"><table><tr><th>Field</th><th>Critical</th><th>Status</th><th>Where in draft</th></tr>${v.outstanding.map(o => `<tr><td>${esc(o.label)}</td><td>${o.critical ? "Yes" : ""}</td><td>${pill(o.status || "missing")}</td><td class="small">${esc(o.where)}</td></tr>`).join("") || "<tr><td colspan=4>None</td></tr>"}</table></div>`;
  const b = $("#gen"); if (b) b.onclick = async () => { busy(b, true); try { const r = await api(`/api/projects/${id}/generate`, { method: "POST", json: {} });
    $("#genres").innerHTML = `<h3>Generated</h3>${r.files.map(f => `<div class="row"><button class="btn sm primary" data-g="${f.id}">Download</button> ${esc(f.title)} – ${esc(f.filename)} (v${f.version})</div>`).join("")}`;
    document.querySelectorAll("[data-g]").forEach(x => x.onclick = () => download(`/api/generated/${x.dataset.g}/download`)); } catch (e) { toast(e.message, true); } busy(b, false); };
}
async function tVersions(P, id) {
  let au = []; if (can("audit.view")) au = await api(`/api/audit?project_id=${id}`);
  $("#tab").innerHTML = `<h2>DA version history & generated documents</h2>${genTable(P.generated)}
  <h2>Legal review history</h2>${P.reviews.length ? P.reviews.map(r => `<div><a href="#/review/${r.id}">${esc(r.title)}</a> – ${fmtDate(r.created_at)}</div>`).join("") : "<p class='muted'>None</p>"}
  <h2>Audit trail</h2>${auditTable(au)}`;
  wireGen();
}
function genTable(rows) {
  return `<div class="tbl"><table><tr><th>Document</th><th>File</th><th>Version</th><th>Status</th><th>Created</th><th></th></tr>${rows.map(g => `<tr><td>${esc(g.title)}</td><td class="small">${esc(g.filename)}</td><td>v${g.version}</td><td>${pill(g.status, g.status === "finalised" ? "s-pass" : "s-verify")}</td><td class="small">${fmtDate(g.created_at)}</td>
  <td><button class="btn sm primary" data-g="${g.id}">Download</button> ${g.kind === "da" && g.status !== "finalised" && can("draft.finalise") ? `<button class="btn sm" data-fin="${g.id}">Finalise</button>` : ""}</td></tr>`).join("") || "<tr><td colspan=6 class='muted'>None</td></tr>"}</table></div>`;
}
function wireGen() {
  document.querySelectorAll("[data-g]").forEach(x => x.onclick = () => download(`/api/generated/${x.dataset.g}/download`));
  document.querySelectorAll("[data-fin]").forEach(x => x.onclick = async () => { try { await api(`/api/generated/${x.dataset.fin}/finalise`, { method: "POST" }); toast("Finalised"); route(); } catch (e) { toast(e.message, true); } });
}
function auditTable(rows) { return `<div class="tbl"><table><tr><th>When</th><th>User</th><th>Action</th><th>Detail</th></tr>${rows.map(a => `<tr><td class="small">${fmtDate(a.at)}</td><td>${esc(a.user)}</td><td>${esc(a.action)}</td><td class="mono small">${esc(JSON.stringify(a.detail)).slice(0, 300)}</td></tr>`).join("") || "<tr><td colspan=4 class='muted'>None</td></tr>"}</table></div>`; }

/* ---------------------------------------------------------------- annexures / pending / generated / history */
async function annexures() {
  const ps = await api("/api/projects");
  $("#main").innerHTML = `<h1>Annexure Generator</h1><p class="sub">Generates the nine Schedules (property, existing premises, member-wise area, allocation, member-wise financials, amenities, BG schedule, completion schedule, disclosures) and the annexure formats from the project database – all cross-referenced to the master DA numbering.</p>
  <div class="card" style="max-width:640px"><label>Project<select id="ap">${ps.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label>
  <div class="row"><button class="btn gold" id="ga">Generate Schedules & Annexures</button><button class="btn" id="gp">Generate member-wise PAAA pack</button></div><div id="ares"></div></div>`;
  const run = async (kinds, b) => { busy(b, true); try { const r = await api(`/api/projects/${$("#ap").value}/generate`, { method: "POST", json: { kinds } });
    $("#ares").innerHTML = r.files.map(f => `<div class="row"><button class="btn sm primary" data-g="${f.id}">Download</button> ${esc(f.filename)}</div>`).join("") || "<p class='muted'>Nothing generated (no units?)</p>"; wireGen(); } catch (e) { toast(e.message, true); } busy(b, false); };
  $("#ga").onclick = e => run(["annexures"], e.target); $("#gp").onclick = e => run(["paaa"], e.target);
}
async function pendingView() {
  const rows = await api("/api/pending");
  $("#main").innerHTML = `<h1>Pending Information</h1><p class="sub">Across all projects: contradictions, critical missing information, unverified values and member-register issues.</p>
  <div class="tbl"><table><tr><th>Project</th><th>Type</th><th>Item</th><th>Group</th></tr>${rows.map(r => `<tr><td><a href="#/project/${r.project_id}/gaps">${esc(r.project)}</a></td><td>${pill(r.kind === "member" ? "member" : r.kind, r.kind === "member" ? "s-warn" : "s-" + r.kind)}</td><td>${esc(r.label)}</td><td>${esc(r.group)}</td></tr>`).join("") || "<tr><td colspan=4>Nothing pending.</td></tr>"}</table></div>`;
}
async function generatedView() { const rows = await api("/api/generated"); $("#main").innerHTML = `<h1>Generated Documents</h1>${genTable(rows)}`; wireGen(); }
async function historyView() { if (!can("audit.view")) { $("#main").innerHTML = "<p>Your role cannot view the audit trail.</p>"; return; } const rows = await api("/api/audit"); $("#main").innerHTML = `<h1>Project History</h1><p class="sub">Uploads, edits, approvals, generated versions, downloads.</p>${auditTable(rows)}`; }

/* ---------------------------------------------------------------- review */
async function reviewHome() {
  const [rows, ps] = await Promise.all([api("/api/reviews"), api("/api/projects")]);
  $("#main").innerHTML = `<h1>Review Existing Development Agreement</h1><p class="sub">Upload a DA drafted by a developer, advocate or consultant (.docx). The original is preserved unchanged; the review produces genuine Word Track Changes with explanatory comments, a clean copy and six reports. Satisfactory clauses are retained as drafted.</p>
  <div class="card" style="max-width:720px">${can("review.run") ? `<div class="drop" id="rdrop">Drop the DA (.docx) here or <a href="#" id="rpick">choose file</a><input type="file" id="rfile" accept=".docx" class="hidden"></div>
  <div class="row" style="margin-top:8px"><label style="flex:1">Link to project (optional)<select id="rproj"><option value="">—</option>${ps.map(p => `<option value="${p.id}">${esc(p.name)}</option>`).join("")}</select></label>
  ${ME.ai_available ? `<label class="row"><input type="checkbox" id="rai" style="width:auto"> add Claude suggestions</label>` : ""}</div><div id="rres"></div>` : "<p>Your role cannot run reviews.</p>"}</div>
  <h2>Previous reviews</h2><div class="tbl"><table><tr><th>Document</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Tracked changes</th><th>Reviewed</th></tr>
  ${rows.map(r => `<tr><td><a href="#/review/${r.id}">${esc(r.title)}</a></td>${["Critical", "High", "Medium", "Low"].map(s => `<td>${r.summary.counts?.[s] ?? 0}</td>`).join("")}<td class="small">${r.summary.stats?.insertions ?? 0} ins · ${r.summary.stats?.deletions ?? 0} del · ${r.summary.stats?.comments ?? 0} comments</td><td class="small">${fmtDate(r.created_at)}</td></tr>`).join("") || "<tr><td colspan=7 class='muted'>None</td></tr>"}</table></div>`;
  if (!can("review.run")) return;
  const send = async f => { if (!f) return; const fd = new FormData(); fd.append("file", f); if ($("#rproj").value) fd.append("project_id", $("#rproj").value); fd.append("use_ai", $("#rai")?.checked ? "true" : "false");
    $("#rres").innerHTML = loading(); try { const r = await api("/api/reviews", { method: "POST", body: fd }); location.hash = `#/review/${r.id}`; } catch (e) { $("#rres").innerHTML = `<p class="err">${esc(e.message)}</p>`; } };
  const d = $("#rdrop"); $("#rpick").onclick = e => { e.preventDefault(); $("#rfile").click(); }; $("#rfile").onchange = e => send(e.target.files[0]);
  d.ondragover = e => { e.preventDefault(); d.classList.add("over"); }; d.ondragleave = () => d.classList.remove("over"); d.ondrop = e => { e.preventDefault(); d.classList.remove("over"); send(e.dataTransfer.files[0]); };
}
async function reviewView(id) {
  const r = await api(`/api/reviews/${id}`); const s = r.summary;
  const order = ["review.original", "review.redline", "review.clean", "review.report", "review.missing", "review.risk", "review.compare", "review.negotiation", "review.checklist"];
  const files = order.map(k => r.files.find(f => f.kind === k)).filter(Boolean);
  $("#main").innerHTML = `<h1>Review: ${esc(r.title)}</h1><p class="sub">${s.counts.Critical} critical · ${s.counts.High} high · ${s.counts.Medium} medium · ${s.counts.Low} low · ${s.stats.insertions} tracked insertions · ${s.stats.deletions} tracked deletions · ${s.stats.comments} comments · ${s.refused} not auto-applied</p>
  <div class="grid g3">${files.map((f, i) => `<div class="card"><div class="small muted">${i + 1}.</div><b>${esc(f.title)}</b><div class="small muted">${esc(f.filename)}</div><button class="btn sm primary" data-g="${f.id}" style="margin-top:6px">Download</button></div>`).join("")}</div>
  <p class="small muted">Original SHA-256: <span class="mono">${esc(s.original_sha256)}</span> – the original upload is stored unchanged. Terminology detected: members = “${esc(s.terms.M)}”, new premises = “${esc(s.terms.NP)}”.</p>
  <div class="row"><h2>Findings</h2><span class="spacer"></span><select id="fsev" style="width:auto"><option value="">All severities</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select>
  <select id="fcat" style="width:auto"><option value="">All categories</option><option>Legal</option><option>Commercial</option><option>Construction</option><option>Society Protection</option><option>Missing Clause</option></select></div><div id="flist"></div>
  <h2>Execution checklist (${s.checklist.length})</h2><div class="tbl"><table><tr><th>Type</th><th>Where</th><th>Detail</th></tr>${s.checklist.map(c => `<tr><td>${esc(c.type)}</td><td>${esc(c.where)}</td><td class="small">${esc(c.detail)}</td></tr>`).join("")}</table></div>`;
  wireGen();
  const draw = () => { const fs = r.findings.filter(f => (!$("#fsev").value || f.severity === $("#fsev").value) && (!$("#fcat").value || f.category === $("#fcat").value));
    $("#flist").innerHTML = fs.map(f => `<div class="card" style="margin-bottom:10px"><div class="row">${sev(f.severity)} <b>${esc(f.id)} · ${esc(f.title)}</b> <span class="small muted">${esc(f.category)} · ${esc(f.clause_ref)} · ${f.negotiable ? "Negotiable" : "Mandatory"} · ${esc(f.kind)}</span><span class="spacer"></span>${pill(f.status)}</div>
    <div class="grid g2" style="margin-top:8px"><div><div class="small muted">Original</div><div class="diffo small">${esc(f.original)}</div></div><div><div class="small muted">Proposed</div><div class="diffn small">${esc(f.proposed)}</div></div></div>
    <p class="small"><b>Reason:</b> ${esc(f.reason)}<br><b>Society's benefit:</b> ${esc(f.benefit)}<br><b>Risk addressed:</b> ${esc(f.risk)}${f.legal ? `<br><b>Reference:</b> ${esc(f.legal)} <i>(verify)</i>` : ""}${f.note ? `<br><b>Note:</b> ${esc(f.note)}` : ""}</p></div>`).join("") || "<p class='muted'>No findings.</p>"; };
  $("#fsev").onchange = draw; $("#fcat").onchange = draw; draw();
}
async function compareView() {
  $("#main").innerHTML = `<h1>Document Comparison</h1><p class="sub">Compare two versions of an agreement (e.g. the developer's revised draft against the Society's last draft). Output: a Word document with the differences as genuine tracked changes.</p>
  <div class="card" style="max-width:640px"><label>Earlier version (.docx)<input type="file" id="ca" accept=".docx"></label><label>Later version (.docx)<input type="file" id="cb" accept=".docx"></label><button class="btn gold" id="cgo">Compare</button><div id="cres"></div></div>`;
  $("#cgo").onclick = async e => { const a = $("#ca").files[0], b = $("#cb").files[0]; if (!a || !b) return toast("Choose both files", true);
    const fd = new FormData(); fd.append("file_a", a); fd.append("file_b", b); busy(e.target, true);
    try { const g = await api("/api/compare", { method: "POST", body: fd }); $("#cres").innerHTML = `<p><button class="btn sm primary" data-g="${g.id}">Download</button> ${esc(g.filename)}</p>`; wireGen(); } catch (er) { toast(er.message, true); } busy(e.target, false); };
}

/* ---------------------------------------------------------------- knowledge */
async function clausesView() {
  $("#main").innerHTML = `<h1>Clause Library</h1><p class="sub">Structured, searchable clauses. Clauses ingested from reference or uploaded agreements remain <i>pending review</i> until approved by the Legal Head; clauses containing project-specific facts cannot be approved until made generic.</p>
  <div class="row"><input id="cq" placeholder="Search e.g. bank guarantee vacation, force majeure rent" style="max-width:380px"><select id="ct" style="width:auto"></select><select id="cs" style="width:auto"><option value="">Any status</option><option value="approved">Approved</option><option value="pending_review">Pending review</option><option value="rejected">Rejected</option></select>
  <select id="cc" style="width:auto"><option value="">Any classification</option><option>Preferred</option><option>Acceptable alternative</option><option>Negotiable</option><option>Not recommended</option><option>Critical Society protection</option></select><select id="csrc" style="width:auto"></select>
  <button class="btn primary" id="cgo">Search</button>${can("clause.propose") ? `<button class="btn" id="cnew">Propose clause</button>` : ""}</div><div id="clist" style="margin-top:12px"></div>`;
  const load = async () => { $("#clist").innerHTML = loading();
    const qs = new URLSearchParams({ q: $("#cq").value, topic: $("#ct").value || "", status: $("#cs").value, classification: $("#cc").value, source: $("#csrc").value || "" });
    const r = await api("/api/clauses?" + qs);
    if (!$("#ct").options.length) { $("#ct").innerHTML = `<option value="">Any topic</option>` + r.topics.map(t => `<option>${t}</option>`).join(""); $("#csrc").innerHTML = `<option value="">Any source</option>` + r.sources.map(s => `<option>${esc(s)}</option>`).join(""); }
    $("#clist").innerHTML = r.items.map(c => `<div class="card" style="margin-bottom:8px"><div class="row"><b>${esc(c.clause_code)}</b> ${esc(c.subject)} <span class="spacer"></span>${pill(c.classification, "s-verify")} ${pill(c.approval_status)} ${c.contains_project_facts ? pill("contains project facts", "s-warn") : ""}</div>
      <div class="small muted">${esc(c.article)} · topic: ${esc(c.topic)} · source: ${esc(c.source_agreement)}</div>
      <details><summary class="small">Wording & notes</summary><p class="small wrap"><b>Standard / society-favourable:</b> ${esc(c.society_favourable || c.standard_wording)}</p>${c.neutral_version ? `<p class="small wrap"><b>Neutral version:</b> ${esc(c.neutral_version)}</p>` : ""}
      <p class="small"><b>Explanation:</b> ${esc(c.explanation)}<br><b>Risk addressed:</b> ${esc(c.risk_addressed)}<br><b>Legal provision:</b> ${esc(c.legal_provision)}<br><b>Recommended use:</b> ${esc(c.recommended_use)}</p></details>
      ${can("clause.approve") ? `<div class="row"><button class="btn sm" data-ca="approve" data-id="${c.id}">Approve</button><button class="btn sm" data-ca="reject" data-id="${c.id}">Reject</button><button class="btn sm" data-ca="reopen" data-id="${c.id}">Reopen</button></div>` : ""}</div>`).join("") || "<p class='muted'>No clauses.</p>";
    document.querySelectorAll("[data-ca]").forEach(b => b.onclick = async () => { try { await api(`/api/clauses/${b.dataset.id}/${b.dataset.ca}`, { method: "POST" }); toast("Updated"); load(); } catch (e) { toast(e.message, true); } }); };
  $("#cgo").onclick = load; $("#cq").onkeydown = e => e.key === "Enter" && load();
  if ($("#cnew")) $("#cnew").onclick = () => { $("#clist").innerHTML = `<div class="card"><label>Subject<input id="ns"></label><label>Society-favourable wording<textarea id="nw"></textarea></label><label>Neutral version<textarea id="nn"></textarea></label><label>Explanation<textarea id="ne"></textarea></label><label>Risk addressed<input id="nr"></label><label>Legal provision<input id="nl"></label><button class="btn primary" id="nsave">Submit for approval</button></div>`;
    $("#nsave").onclick = async () => { await api("/api/clauses", { method: "POST", json: { subject: $("#ns").value, standard_wording: $("#nw").value, society_favourable: $("#nw").value, neutral_version: $("#nn").value, explanation: $("#ne").value, risk_addressed: $("#nr").value, legal_provision: $("#nl").value } }); toast("Submitted – pending approval"); load(); }; };
  load();
}
async function referencesView() {
  const [refs, matrix] = await Promise.all([api("/api/references"), api("/api/references/matrix")]);
  const names = matrix.length ? Object.keys(matrix[0]).filter(k => !["topic", "master"].includes(k)) : [];
  const cls = v => v.startsWith("Absent") ? "s-missing" : v.includes("deficient") ? "s-conflict" : "s-pass";
  $("#main").innerHTML = `<h1>Reference Agreements</h1><p class="sub">Reference agreements are a drafting knowledge base only – their names, amounts and property facts are never carried into new projects (the validator checks for this). Upload further reference DAs to extend the library and the comparison matrix.</p>
  ${can("clause.propose") ? `<div class="card" style="max-width:600px"><input type="file" id="rf" multiple accept=".docx,.pdf"><button class="btn primary" id="rgo" style="margin-top:6px">Ingest reference agreement(s)</button></div>` : ""}
  <h2>Ingested (${refs.length})</h2><div class="tbl"><table><tr><th>Agreement</th><th>Candidate clauses</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Ingested</th></tr>${refs.map(r => `<tr><td>${esc(r.filename)}</td><td>${r.clauses?.added ?? ""} (${r.clauses?.with_project_facts ?? 0} with facts)</td>${["Critical", "High", "Medium", "Low"].map(s => `<td>${r.counts[s]}</td>`).join("")}<td class="small">${fmtDate(r.uploaded_at)}</td></tr>`).join("")}</table></div>
  <h2>Comparative clause matrix</h2><div class="tbl"><table><tr><th>Protection</th>${names.map(n => `<th>${esc(n)}</th>`).join("")}<th>Master DA</th></tr>${matrix.map(r => `<tr><td>${esc(r.topic)}</td>${names.map(n => `<td>${pill(r[n], cls(r[n]))}</td>`).join("")}<td class="small">${esc(r.master)}</td></tr>`).join("")}</table></div>`;
  if ($("#rgo")) $("#rgo").onclick = async e => { const fs = $("#rf").files; if (!fs.length) return; const fd = new FormData(); [...fs].forEach(f => fd.append("files", f)); busy(e.target, true);
    try { await api("/api/references", { method: "POST", body: fd }); toast("Ingested"); referencesView(); } catch (er) { toast(er.message, true); } busy(e.target, false); };
}
async function legalView() {
  $("#main").innerHTML = `<h1>Legal Research</h1><p class="sub">Register of statutes, rules, circulars and judgments with source, effective version and verification status. Nothing here is to be relied upon until verified by the advocate; the system never invents authorities.</p>
  <div class="row"><input id="lq" placeholder="Search e.g. carpet area, 79A, arbitration interim" style="max-width:420px"><button class="btn primary" id="lgo">Search</button></div>
  ${ME.ai_available ? `<div class="card" style="margin-top:10px"><label>Ask a question (answered only from the register)<textarea id="ask"></textarea></label><button class="btn" id="askgo">Ask Claude</button><div id="ans"></div></div>` : ""}<div id="llist"></div>`;
  const load = async () => { const rows = await api("/api/legal?q=" + encodeURIComponent($("#lq").value));
    $("#llist").innerHTML = `<div class="tbl" style="margin-top:10px"><table><tr><th>Code</th><th>Source</th><th>Provision</th><th>Proposition</th><th>Version</th><th>Status</th>${can("legal.edit") ? "<th></th>" : ""}</tr>${rows.map(l => `<tr><td class="mono">${esc(l.code)}</td><td>${esc(l.title)}<div class="src">${esc(l.kind)}</div></td><td>${esc(l.provision)}</td><td class="small">${esc(l.proposition)}</td><td class="small">${esc(l.effective_version)}${l.verified_on ? `<br>verified ${esc(l.verified_on)}` : ""}</td><td>${pill(l.verification_status, l.verification_status === "verified" ? "s-pass" : "s-warn")}</td>
    ${can("legal.edit") ? `<td><button class="btn sm" data-ver="${l.id}">Mark verified</button></td>` : ""}</tr>`).join("")}</table></div>`;
    document.querySelectorAll("[data-ver]").forEach(b => b.onclick = async () => { const l = rows.find(x => x.id == b.dataset.ver); const src = prompt("Source verified against (Gazette / bare act edition / URL):", l.source_ref); if (src == null) return;
      await api(`/api/legal/${l.id}`, { method: "PUT", json: { ...l, source_ref: src, verified_on: new Date().toISOString().slice(0, 10), verification_status: "verified" } }); load(); }); };
  $("#lgo").onclick = load; $("#lq").onkeydown = e => e.key === "Enter" && load();
  if ($("#askgo")) $("#askgo").onclick = async e => { busy(e.target, true); try { const r = await api("/api/legal/ask", { method: "POST", json: { question: $("#ask").value } });
    $("#ans").innerHTML = `<p class="wrap">${esc(r.answer)}</p><p class="small">Sources: ${esc(r.sources_used.join(", "))}</p>${r.uncertain_points.length ? `<p class="small"><b>Uncertain:</b> ${esc(r.uncertain_points.join("; "))}</p>` : ""}<p class="small err">${esc(r.verification)}</p>`; } catch (er) { toast(er.message, true); } busy(e.target, false); };
  load();
}

/* ---------------------------------------------------------------- admin */
async function adminView() {
  const [us, roles] = await Promise.all([api("/api/users"), api("/api/roles")]);
  $("#main").innerHTML = `<h1>Users & Roles</h1><div class="tbl"><table><tr><th>User</th><th>Name</th><th>Role</th><th>Permissions</th></tr>${us.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.full_name)}</td><td>${esc(u.role_label)}</td><td class="small">${esc(u.permissions.join(", "))}</td></tr>`).join("")}</table></div>
  <h2>Add user</h2><div class="card" style="max-width:520px"><label>Username<input id="uu"></label><label>Full name<input id="un"></label><label>Role<select id="ur">${Object.entries(roles).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label><label>Initial password (min. 10 characters)<input id="up" type="password"></label><button class="btn primary" id="ugo">Create user</button></div>`;
  $("#ugo").onclick = async () => { try { await api("/api/users", { method: "POST", json: { username: $("#uu").value, full_name: $("#un").value, role: $("#ur").value, password: $("#up").value } }); toast("User created"); adminView(); } catch (e) { toast(e.message, true); } };
}
async function accountView() {
  $("#main").innerHTML = `<h1>Account</h1><div class="card" style="max-width:420px"><label>Current password<input id="op" type="password"></label><label>New password (min. 10)<input id="np" type="password"></label><button class="btn primary" id="pgo">Change password</button></div>`;
  $("#pgo").onclick = async () => { try { await api("/api/me/password", { method: "POST", json: { old_password: $("#op").value, new_password: $("#np").value } }); toast("Password changed"); } catch (e) { toast(e.message, true); } };
}
boot();
