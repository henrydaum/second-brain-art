// TIPS is defined in tips.js, loaded before this script.
function pickTip() {
  const el = document.querySelector("#tipText");
  if (!el) return;
  const pool = Array.isArray(TIPS) ? TIPS : [];
  if (pool.length) el.textContent = pool[Math.floor(Math.random() * pool.length)];
}
pickTip();

const sid = localStorage.sbDemoSession || (localStorage.sbDemoSession = crypto.randomUUID());
// Mirror sid into a cookie so /files image requests carry the browser identity.
document.cookie = `sb_sid=${encodeURIComponent(sid)}; path=/; SameSite=Strict; max-age=31536000`;
const messages = document.querySelector("#messages");
const chat = document.querySelector(".chat");
const form = document.querySelector("#chatForm");
const input = document.querySelector("#chatInput");
const showcase = document.querySelector(".showcase");
const heroImage = document.querySelector("#heroImage");
const renderMeter = document.querySelector("#renderMeter");
const renderMeterFill = document.querySelector("#renderMeterFill");
const renderMeterLabel = document.querySelector("#renderMeterLabel");
const downloadImage = document.querySelector("#downloadImage");
const downloadPanel = document.querySelector("#downloadPanel");
const headerCanvasActions = document.querySelector("#headerCanvasActions");
const shareBtn = document.querySelector("#shareImage");
const sharePanel = document.querySelector("#sharePanel");
const shareLinkInput = document.querySelector("#shareLink");
const shareQrImg = document.querySelector("#shareQr");
const shareQrDownload = document.querySelector("#downloadQr");
const copyShareLinkBtn = document.querySelector("#copyShareLink");
const toggleShareQrBtn = document.querySelector("#toggleShareQr");
const shareQrWrap = document.querySelector("#shareQrWrap");
const linkModal = document.querySelector("#linkModal");
const linkModalUrl = document.querySelector("#linkModalUrl");
const linkModalQr = document.querySelector("#linkModalQr");
const linkModalCopy = document.querySelector("#linkModalCopy");
const linkModalDownload = document.querySelector("#linkModalDownload");
const settingsBtn = document.querySelector("#settingsBtn");
const settingsModal = document.querySelector("#settingsModal");
const settingsStatus = document.querySelector("#settingsStatus");
const prefTechniqueAuthoring = document.querySelector("#prefTechniqueAuthoring");
const prefCommunityTechniques = document.querySelector("#prefCommunityTechniques");
const aspectPresets = document.querySelector("#aspectPresets");
const controlsPanel = document.querySelector("#controlsPanel");
const controlsDrawer = document.querySelector("#controlsDrawer");
const controlsToggle = document.querySelector("#controlsToggle");
const techniqueSearchResults = document.querySelector("#techniqueSearchResults");
const emptyState = document.querySelector("#emptyState");
const NEAR_BOTTOM_PX = 80;
let palettesCache = [];
let currentControlsPanels = [];
const pendingControls = new Map();
const videoSliders = new Set();
let videoFpsValue = 24;
let videoSecondsValue = 3;
let videoRendering = false;
let videoCanceling = false;
let typingEl = null;
const TOOL_LABELS = {
  search_techniques: "Searching techniques",
  read_technique: "Reading technique",
  read_technique_guide: "Reading technique guide",
  create_technique: "Creating technique",
  update_technique: "Updating technique",
  delete_technique: "Deleting technique",
  execute_technique: "Executing technique",
  manage_layers: "Managing layers",
  web_search: "Searching the web",
  sql_query: "Querying database",
  ask_user_question: "Asking a question",
  propose_plan: "Proposing a plan",
};
function toolLabel(name) {
  if (!name) return "";
  if (TOOL_LABELS[name]) return TOOL_LABELS[name];
  return name.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
}
function setStatusText(text) {
  if (typingEl && typingEl.isConnected) {
    typingEl.textContent = text;
    bottom();
    return;
  }
  typingEl = document.createElement("article");
  typingEl.className = "status typing";
  typingEl.textContent = text;
  messages.appendChild(typingEl);
  bottom();
}
function clearStatus() {
  if (typingEl) { typingEl.remove(); typingEl = null; }
}
let agentBusy = false;
const sendBtn = form.querySelector("button:not(#controlsToggle)");

// ----- Technique search (used when the controls drawer is open) -----
let techniquesCache = [];            // last /api/techniques response
let techniquesLoading = null;        // in-flight fetch promise (dedup)
let inSearchMode = false;        // drawer open → input is a technique picker
const CHAT_PLACEHOLDER = input.placeholder;
const SEARCH_PLACEHOLDER = "Search techniques...";

function refreshControlsToggleEnabled() {
  // Single source of truth for the gear's disabled state. The only gate is
  // agentBusy — the drawer is useful even on a blank canvas because the
  // search input adds a background technique directly.
  if (agentBusy) {
    controlsToggle.disabled = true;
    controlsToggle.title = "Wait for the current turn to finish";
  } else {
    controlsToggle.disabled = false;
    controlsToggle.title = "Controls";
  }
}
const atBottom = () => messages.scrollHeight - messages.scrollTop - messages.clientHeight < NEAR_BOTTOM_PX;
const bottom = (force = false) => {
  const stick = force || atBottom();
  if (stick) requestAnimationFrame(() => messages.scrollTop = messages.scrollHeight);
};
const reveal = el => requestAnimationFrame(() => el.scrollIntoView({block: "nearest"}));
const add = (role, text, useMd = false) => {
  const stick = atBottom();
  const el = document.createElement("article");
  el.className = role;
  if (useMd) el.innerHTML = mdToHtml(text);
  else el.textContent = text;
  messages.appendChild(el);
  if (role === "error") reveal(el); else bottom(stick);
  return el;
};
function refillText(seconds) {
  if (seconds == null) return "Usage will be available again later.";
  if (seconds <= 60) return "Usage will be available again in less than a minute.";
  if (seconds < 3600) return `Usage will be available again in about ${Math.ceil(seconds / 60)} minutes.`;
  const hours = Math.ceil(seconds / 3600);
  return `Usage will be available again in about ${hours} hour${hours === 1 ? "" : "s"}.`;
}
function renderCreditError(error) {
  const d = error?.details || {}, available = Number(d.total_available || 0);
  const el = document.createElement("article");
  el.className = "error credit-error";
  const title = document.createElement("strong");
  title.textContent = available ? "Not enough usage available for that" : "Usage is paused for now";
  const body = document.createElement("p");
  body.textContent = available
    ? `That needs ${Number(d.required || 1)} units, and you have ${available}. You can still try a manual edit.`
    : "The current usage limit has been reached.";
  const refill = document.createElement("p");
  refill.className = "credit-refill";
  refill.textContent = refillText(d.next_refill_seconds);
  el.append(title, body, refill);
  messages.appendChild(el);
  reveal(el);
}
function mdToHtml(src) {
  let s = String(src ?? "").replace(/[&<>]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[m]));
  s = s.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${c.replace(/^\n/, "")}</code></pre>`);
  s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
  s = s.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?;:]|$)/g, '$1<em>$2</em>');
  s = s.replace(/(^|[\s(])_([^_\n]+)_(?=[\s).,!?;:]|$)/g, '$1<em>$2</em>');
  s = s.replace(/^(#{1,3})\s+(.+)$/gm, (_, h, t) => `<h${h.length + 2}>${t}</h${h.length + 2}>`);
  s = s.replace(/(?:^|\n)((?:- .+(?:\n|$))+)/g, m => {
    const items = m.trim().split(/\n/).map(l => `<li>${l.replace(/^- /, "")}</li>`).join("");
    return `\n<ul>${items}</ul>`;
  });
  return s;
}
function readCookie(name) {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/([.$?*|{}()\[\]\\\/\+^])/g, "\\$1") + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : "";
}
async function post(url, body = {}) {
  const headers = {"Content-Type": "application/json"};
  const csrf = readCookie("sb_csrf");
  if (csrf) headers["X-CSRF-Token"] = csrf;
  const res = await fetch(url, {method:"POST", headers, body:JSON.stringify({session_id:sid, ...body})});
  return res.json();
}
async function poll() { try { render((await fetch(`/api/events?session_id=${encodeURIComponent(sid)}`).then(r => r.json())).events); } catch {} }
let eventSource = null, fallbackPoll = 0;
function startFallbackPoll() {
  if (!fallbackPoll) fallbackPoll = setInterval(poll, 5000);
}
function connectEvents() {
  if (!("EventSource" in window)) return startFallbackPoll();
  eventSource = new EventSource(`/api/events/stream?session_id=${encodeURIComponent(sid)}`);
  eventSource.onmessage = e => { try { render([JSON.parse(e.data)]); } catch {} };
}
async function get(url) { return fetch(`${url}${url.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sid)}`).then(r => r.json()); }
function approval(ev) {
  const el = document.createElement("article");
  el.className = "assistant";
  el.textContent = `${ev.title}\n${ev.body}`;
  const actions = document.createElement("div");
  actions.className = "approval-actions";
  for (const [label, value, cls] of [["Approve", true, "approve"], ["Deny", false, "deny"]]) {
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = cls; btn.textContent = label;
    btn.onclick = async () => { actions.querySelectorAll("button").forEach(b => b.disabled = true); render((await post("/api/approval", {value})).events); };
    actions.appendChild(btn);
  }
  el.appendChild(actions);
  messages.appendChild(el);
  bottom();
}
function renderToolStatus(ev) {
  // Tool-status chips are intentionally not shown in chat — the loader and the
  // agent's own step-by-step messages cover what the user needs to see.
  // We still drive the loader so "Thinking…" stays alive across tool calls.
  const id = ev.call_id || `${ev.name}:${Date.now()}`;
  if (ev.status === "started") { loaderToolStart(id); setStatusText(`${toolLabel(ev.name)}…`); }
  else if (ev.status === "progressed") setStatusText(`${toolLabel(ev.name)}…`);
  else if (ev.status === "finished") loaderToolEnd(id);
}
let renderMeterFrame = 0, renderMeterHide = 0, renderMeterValue = 0;
function setRenderMeter(v) {
  renderMeterValue = Math.max(0, Math.min(1, v || 0));
  renderMeterFill.style.transform = `scaleX(${renderMeterValue})`;
}
function animateRenderMeter(from, to, seconds) {
  cancelAnimationFrame(renderMeterFrame);
  const start = performance.now(), dur = Math.max(0.3, Number(seconds) || 30) * 1000;
  const tick = now => {
    const t = Math.min(1, (now - start) / dur);
    setRenderMeter(from + (to - from) * t);
    if (t < 1) renderMeterFrame = requestAnimationFrame(tick);
  };
  tick(start);
}
function renderRenderStatus(ev) {
  clearTimeout(renderMeterHide);
  const total = Math.max(1, Number(ev.total_layers) || 1);
  const cached = Math.max(0, Number(ev.cached_layers) || 0);
  const idx = Math.max(1, Number(ev.layer_index) || cached + 1);
  renderMeter.hidden = false;
  if (ev.status === "video_frame") {
    const f = Math.max(0, Number(ev.frame) || 0);
    const t = Math.max(1, Number(ev.total_frames) || 1);
    renderMeterLabel.textContent = `Rendering video · frame ${f}/${t}`;
    setRenderMeter(f / t);
    return;
  }
  if (ev.status === "cached") {
    renderMeterLabel.textContent = `Cached render · ${total}/${total} layers · seed ${ev.seed}`;
    setRenderMeter(1);
    renderMeterHide = setTimeout(() => renderMeter.hidden = true, 900);
  } else if (ev.status === "started") {
    renderMeterLabel.textContent = cached ? `Rendering · reused ${cached}/${total} cached layers` : `Rendering · ${total} layer${total === 1 ? "" : "s"}`;
    setRenderMeter(cached / total);
  } else if (ev.status === "layer_started") {
    renderMeterLabel.textContent = `Rendering layer ${idx}/${total} · ${ev.technique_slug || "technique"} · seed ${ev.seed}`;
    animateRenderMeter((idx - 1) / total, idx / total, ev.timeout_s);
  } else if (ev.status === "layer_finished") {
    setRenderMeter(idx / total);
  } else if (ev.status === "finished") {
    renderMeterLabel.textContent = cached ? `Rendered · reused ${cached}/${total} cached layers` : "Rendered";
    setRenderMeter(1);
    renderMeterHide = setTimeout(() => renderMeter.hidden = true, 1000);
  } else if (ev.status === "error") {
    renderMeterLabel.textContent = `Render failed · ${ev.error || "error"}`;
    setRenderMeter(1);
    renderMeterHide = setTimeout(() => renderMeter.hidden = true, 1800);
  }
}
function render(events) {
  for (const ev of events || []) {
    if (ev.type === "message") { clearStatus(); add("assistant", ev.content, true); }
    else if (ev.type === "status") add("status", ev.content);
    else if (ev.type === "tool_status") renderToolStatus(ev);
    else if (ev.type === "render_status") renderRenderStatus(ev);
    else if (ev.type === "error") {
      clearStatus(); loaderForceStop();
      if (ev.error?.code === "out_of_credits") {
        renderCreditError(ev.error);
        if (ev.error.details?.action === "render") renderRenderStatus({status:"error", error:ev.content});
      }
      else { add("error", ev.content); renderRenderStatus({status:"error", error:ev.content}); }
    }
    else if (ev.type === "form") add("assistant", `${ev.form?.display?.prompt || "Input required"}\n${(ev.form?.display?.choices || []).map(c => c.label || c.value).join(" / ")}`);
    else if (ev.type === "approval") approval(ev);
    else if (ev.type === "hero_image") {
      clearPendingControls(false);
      setCanvas(ev.canvas || {url: ev.url, name: ev.name});
    }
    else if (ev.type === "canvas_reset") { clearPendingControls(false); setCanvas(null); }
    else if (ev.type === "share_link") {
      setShareLink(ev.url, ev.qr_url);
    }
    else if (ev.type === "attachment") add("assistant", `Attachment: ${ev.name}`);
    else if (ev.type === "typing") setTyping(!!ev.on);
  }
  bottom();
}

function setBusy(on) {
  agentBusy = !!on;
  form.classList.toggle("busy", agentBusy);
  form.setAttribute("aria-busy", agentBusy ? "true" : "false");
  input.readOnly = agentBusy;
  if (agentBusy) {
    sendBtn.type = "button";
    sendBtn.textContent = "Cancel";
    sendBtn.classList.add("cancel");
    sendBtn.disabled = false;
  } else {
    sendBtn.type = "submit";
    sendBtn.textContent = inSearchMode ? "Search" : "Send";
    sendBtn.classList.remove("cancel");
    sendBtn.disabled = inSearchMode && !input.value.trim();
  }
  refreshControlsToggleEnabled();
}
sendBtn.addEventListener("click", async e => {
  if (!agentBusy) return; // let submit handler run
  e.preventDefault();
  // Stay disabled until the in-flight chat() returns and setBusy(false) re-enables.
  sendBtn.disabled = true;
  try { render((await post("/api/cancel")).events); }
  catch (err) { add("error", err.message); }
});

function setTyping(on) {
  if (!on) clearStatus();
}

// ----- settings -----
function openModal(el) { el.hidden = false; }
function closeModal(el) { el.hidden = true; }
document.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => closeModal(document.getElementById(b.dataset.close))));
if (settingsModal) settingsModal.addEventListener("click", e => { if (e.target === settingsModal) closeModal(settingsModal); });

function applySettings(settings) {
  prefTechniqueAuthoring.checked = !!settings?.technique_authoring_enabled;
  prefCommunityTechniques.checked = !!settings?.community_techniques_enabled;
}
async function refreshSettings() {
  try { applySettings((await get(`/api/settings?_=${Date.now()}`)).settings); }
  catch (err) { console.warn("[settings] refresh failed:", err); }
}
async function saveSetting(key, value) {
  settingsStatus.hidden = true;
  try {
    const r = await post("/api/settings", {settings: {[key]: value}});
    if (!r.ok) throw new Error(r.error || "Could not save setting.");
    applySettings(r.settings);
    settingsStatus.hidden = false;
    settingsStatus.className = "modal-status ok";
    settingsStatus.textContent = "Saved.";
    techniquesCache = [];
    techniquesLoading = null;
    loadTechniques();
  } catch (err) {
    settingsStatus.hidden = false;
    settingsStatus.className = "modal-status err";
    settingsStatus.textContent = err.message;
  }
}
settingsBtn?.addEventListener("click", () => { openModal(settingsModal); refreshSettings(); syncAspectUI(); });
prefTechniqueAuthoring?.addEventListener("change", () => saveSetting("technique_authoring_enabled", prefTechniqueAuthoring.checked));
prefCommunityTechniques?.addEventListener("change", () => saveSetting("community_techniques_enabled", prefCommunityTechniques.checked));

// ----- Aspect ratio (Settings) -----
// Presets are stored in their landscape (w ≥ h) form; the orientation toggle
// flips non-square ratios. The backend anchors on the long edge, so picking a
// ratio re-renders the current chain at the new shape.
const ASPECT_PRESETS = [
  {label: "1:1",   w: 1,  h: 1},
  {label: "5:4",   w: 5,  h: 4},
  {label: "4:3",   w: 4,  h: 3},
  {label: "3:2",   w: 3,  h: 2},
  {label: "16:10", w: 16, h: 10},
  {label: "16:9",  w: 16, h: 9},
  {label: "25:16", w: 25, h: 16},
  {label: "21:9",  w: 21, h: 9},
];
let aspectOrient = "landscape";
if (aspectPresets) {
  aspectPresets.innerHTML = ASPECT_PRESETS.map((p, i) =>
    `<button type="button" class="aspect-chip" data-i="${i}">${p.label}</button>`).join("");
}
function presetRatioFor(p) {
  if (p.w === p.h) return [1, 1];
  return aspectOrient === "portrait" ? [p.h, p.w] : [p.w, p.h];
}
function updateOrientButtons() {
  document.querySelectorAll(".aspect-orient-btn").forEach(b =>
    b.classList.toggle("is-active", b.dataset.orient === aspectOrient));
}
function highlightActiveChip() {
  if (!aspectPresets) return;
  const w = currentCanvasWidth, h = currentCanvasHeight;
  const curRatio = (w && h) ? Math.max(w, h) / Math.min(w, h) : 0;
  aspectPresets.querySelectorAll(".aspect-chip").forEach(chip => {
    const p = ASPECT_PRESETS[Number(chip.dataset.i)];
    const pr = Math.max(p.w, p.h) / Math.min(p.w, p.h);
    chip.classList.toggle("is-active", !!curRatio && Math.abs(pr - curRatio) < 0.02);
  });
}
// Called when the live canvas changes: derive orientation from the canvas so the
// toggle reflects reality, then repaint button + chip highlights.
function syncAspectUI() {
  const w = currentCanvasWidth, h = currentCanvasHeight;
  if (w && h) {
    if (w > h) aspectOrient = "landscape";
    else if (h > w) aspectOrient = "portrait";
  }
  updateOrientButtons();
  highlightActiveChip();
}
async function postAspect(rw, rh) {
  try {
    const r = await post("/api/set_aspect", {ratio_w: rw, ratio_h: rh});
    if (r?.events) render(r.events);
  } catch (err) { add("error", err.message); }
}
function applyAspect(p) {
  const [rw, rh] = presetRatioFor(p);
  postAspect(rw, rh);
}
// Orientation toggle: set the intent, and if the canvas is already non-square,
// immediately flip it into the chosen orientation. (A square has no orientation,
// so we just record the intent for the next preset pick.)
function applyOrientation(orient) {
  aspectOrient = orient === "portrait" ? "portrait" : "landscape";
  updateOrientButtons();
  const w = currentCanvasWidth, h = currentCanvasHeight;
  if (w && h && w !== h) {
    const lo = Math.max(w, h), sh = Math.min(w, h);
    const [rw, rh] = aspectOrient === "portrait" ? [sh, lo] : [lo, sh];
    postAspect(rw, rh);
  }
}
aspectPresets?.addEventListener("click", e => {
  const chip = e.target.closest(".aspect-chip");
  if (chip) applyAspect(ASPECT_PRESETS[Number(chip.dataset.i)]);
});
document.querySelectorAll(".aspect-orient-btn").forEach(b =>
  b.addEventListener("click", () => applyOrientation(b.dataset.orient)));

// ----- Canvas + theming -----
let currentCanvasSize = 0;     // tracks live canvas long edge for download tier labels
let currentCanvasWidth = 0;    // live canvas width  (for non-square aspect)
let currentCanvasHeight = 0;   // live canvas height (for non-square aspect)
let currentCanvasHasImage = false;
function setCanvas(c) {
  currentCanvasSize = Number(c?.size) || 0;
  currentCanvasWidth = Number(c?.width) || currentCanvasSize;
  currentCanvasHeight = Number(c?.height) || currentCanvasSize;
  currentCanvasHasImage = !!c?.url;
  syncAspectUI();
  if (headerCanvasActions) headerCanvasActions.hidden = !currentCanvasHasImage;
  if (!c?.url) {
    showcase.classList.remove("has-image");
    renderControlsPanel([]);
    heroImage.removeAttribute("src");
    setDownloadPanelOpen(false);
    setSharePanelOpen(false);
    resetAccents();
    return;
  }
  const newUrl = c.url, newName = c.name || "canvas.png";
  const apply = () => {
    heroImage.src = newUrl; heroImage.alt = newName;
    showcase.classList.add("has-image");
    renderControlsPanel(c?.controls_panels || []);
  };
  if (!showcase.classList.contains("has-image")) { apply(); heroImage.addEventListener("load", () => applyAccents(heroImage), {once: true}); return; }
  const pre = new Image();
  pre.crossOrigin = "anonymous";
  pre.onload = () => {
    apply();
    heroImage.addEventListener("load", () => applyAccents(heroImage), {once: true});
  };
  pre.onerror = () => { apply(); };
  pre.src = newUrl;
}

// ----- Dynamic accent extraction -----
const DEFAULT_ACCENT = "#3df2ff";
const DEFAULT_ACCENT_2 = "#ff4d8d";
function applyAccents(imgEl) {
  try {
    const c = document.createElement("canvas");
    c.width = 32; c.height = 32;
    const ctx = c.getContext("2d");
    ctx.drawImage(imgEl, 0, 0, 32, 32);
    const data = ctx.getImageData(0, 0, 32, 32).data;
    const bins = new Map(); // hue bucket (12°) → {weight, h, s, l}
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i+1], b = data[i+2];
      const [h, s, l] = rgbToHsl(r, g, b);
      if (s < 0.28 || l < 0.25 || l > 0.78) continue;
      const bucket = Math.floor(h / 12);
      const w = s * (1 - Math.abs(l - 0.55) * 1.4);
      const cur = bins.get(bucket) || {weight: 0, h: 0, s: 0, l: 0, count: 0};
      cur.weight += w; cur.h += h * w; cur.s += s * w; cur.l += l * w; cur.count += 1;
      bins.set(bucket, cur);
    }
    if (!bins.size) { resetAccents(); return; }
    const sorted = [...bins.values()].sort((a, b) => b.weight - a.weight);
    const a1 = avgBin(sorted[0]);
    // Find a second bin > 60° away on the hue wheel
    const a2 = avgBin(sorted.find(b => Math.min(Math.abs(b.h/b.weight - a1.h), 360 - Math.abs(b.h/b.weight - a1.h)) > 60) || sorted[1] || sorted[0]);
    const accent = hslToHex(a1.h, Math.min(0.55, a1.s), Math.min(0.66, Math.max(0.55, a1.l * 0.5 + 0.31)));
    const accent2 = hslToHex(a2.h, Math.min(0.55, a2.s), Math.min(0.66, Math.max(0.55, a2.l * 0.5 + 0.31)));
    document.documentElement.style.setProperty("--accent", accent);
    document.documentElement.style.setProperty("--accent-2", accent2);
    const glow = hexWithAlpha(accent, 0.10);
    const glow2 = hexWithAlpha(accent2, 0.14);
    document.documentElement.style.setProperty("--accent-glow", glow);
    document.documentElement.style.setProperty("--accent-2-glow", glow2);
    try { localStorage.sbAccents = JSON.stringify({accent, accent2, glow, glow2}); } catch {}
  } catch (e) {
    // Likely a canvas taint (cross-origin) — silently fall back to defaults.
    resetAccents();
  }
}
function avgBin(b) { return {h: b.h / b.weight, s: b.s / b.weight, l: b.l / b.weight}; }
function resetAccents() {
  document.documentElement.style.removeProperty("--accent");
  document.documentElement.style.removeProperty("--accent-2");
  document.documentElement.style.removeProperty("--accent-glow");
  document.documentElement.style.removeProperty("--accent-2-glow");
}
function rgbToHsl(r, g, b) {
  r/=255; g/=255; b/=255;
  const max = Math.max(r,g,b), min = Math.min(r,g,b);
  let h = 0, s = 0; const l = (max+min)/2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d/(2-max-min) : d/(max+min);
    switch (max) { case r: h = (g-b)/d + (g<b?6:0); break; case g: h = (b-r)/d + 2; break; case b: h = (r-g)/d + 4; break; }
    h *= 60;
  }
  return [h, s, l];
}
function hslToHex(h, s, l) {
  const c = (1 - Math.abs(2*l - 1)) * s;
  const x = c * (1 - Math.abs(((h/60) % 2) - 1));
  const m = l - c/2;
  let r=0,g=0,b=0;
  if (h < 60) [r,g,b] = [c,x,0];
  else if (h < 120) [r,g,b] = [x,c,0];
  else if (h < 180) [r,g,b] = [0,c,x];
  else if (h < 240) [r,g,b] = [0,x,c];
  else if (h < 300) [r,g,b] = [x,0,c];
  else [r,g,b] = [c,0,x];
  const to = v => Math.round((v+m)*255).toString(16).padStart(2,"0");
  return `#${to(r)}${to(g)}${to(b)}`;
}
function hexWithAlpha(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`;
}

async function loadCanvas() { const r = await get("/api/canvas"); setCanvas(r.canvas); }

async function loadPalettes() {
  const r = await get("/api/palettes");
  palettesCache = r.palettes || [];
  renderControlsPanel(currentControlsPanels);
}
function paletteSwatchHtml(p, activeId) {
  const cls = p.id === activeId ? "swatch active" : "swatch";
  const colors = Object.values(p.colors || {});
  if (!colors.length) return "";
  const bars = colors.map(c => `<span style="background:${esc(c)}"></span>`).join("");
  return `<button type="button" class="${cls}" title="${esc(p.name)}" aria-label="${esc(p.name)}" aria-pressed="${p.id === activeId ? "true" : "false"}" data-palette="${esc(p.id)}">${bars}</button>`;
}
function paletteCurBars(activeId) {
  const p = palettesCache.find(x => x.id === activeId);
  if (!p) return "";
  return Object.values(p.colors || {}).map(c => `<span style="background:${esc(c)}"></span>`).join("");
}

// ----- Controls drawer -----
function renderControlsPanel(panels) {
  currentControlsPanels = panels || [];
  pruneVideoSliders();
  const hasImage = showcase.classList.contains("has-image");
  controlsToggle.hidden = false;
  refreshControlsToggleEnabled();
  controlsDrawer.hidden = false;
  if (!hasImage) {
    // Blank canvas: no layers to edit and no Regenerate button to offer,
    // but the search input above is fully functional — let the user add
    // their first background from here.
    controlsPanel.innerHTML = `<div class="ctl-empty-canvas">No layers yet — search below to add layers to the canvas,\n or press the controls icon to go back.</div>`;
    if (localStorage.sbDrawerOpen === "1") setControlsOpen(true);
    return;
  }
  const movableLayers = currentControlsPanels.filter(p => Number(p.chain_index) > 0).length;
  const maxChain = currentControlsPanels.reduce((m, p) => Math.max(m, Number(p.chain_index) || 0), 0);
  const stack = [...currentControlsPanels].sort((a, b) => b.chain_index - a.chain_index).map(p => renderPanel(p, movableLayers, maxChain)).join("");
  const dirty = pendingControls.size ? " dirty" : "";
  const videoDisabled = selectedVideoSpecs().length ? "" : " disabled";
  const regen = `<section class="ctl-actions"><button type="button" class="ctl-global${dirty}" id="globalRegenerate" title="Apply staged controls with the current seed"><span>Regenerate</span></button><button type="button" class="ctl-global${dirty}" id="globalRandomize" title="Apply staged controls with a fresh random seed"><span>Randomize</span></button><span class="video-action-wrap"><button type="button" class="ctl-global" id="globalVideo" title="Render a GIF from checked sliders"${videoDisabled}><span>Video</span></button>${renderVideoPopup()}</span></section>`;
  controlsPanel.innerHTML = stack + regen;
  if (localStorage.sbDrawerOpen === "1") setControlsOpen(true);
  markDirtyControls();
}
function setControlsOpen(open) {
  controlsDrawer.classList.toggle("open", open);
  controlsToggle.classList.toggle("open", open);
  chat.classList.toggle("controls-open", open);
  localStorage.sbDrawerOpen = open ? "1" : "0";
  setSearchMode(!!open);
}

// ----- Technique search wiring -----
async function loadTechniques() {
  if (techniquesLoading) return techniquesLoading;
  techniquesLoading = (async () => {
    try {
      const r = await get("/api/techniques");
      techniquesCache = Array.isArray(r.techniques) ? r.techniques : [];
    } catch { techniquesCache = []; }
    finally { techniquesLoading = null; }
  })();
  return techniquesLoading;
}

function tokenize(s) {
  // Split on whitespace, underscores, and case boundaries (e.g. mandelbrotExplorer
  // → ["mandelbrot", "explorer"]). Lowercase. Drops empties.
  return String(s || "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .split(/[\s_\-./,]+/)
    .filter(Boolean);
}

function rankTechniques(query) {
  const qTokens = tokenize(query);
  if (!qTokens.length) return [];
  const out = [];
  for (const s of techniquesCache) {
    const nameTokens = new Set([...tokenize(s.slug), ...tokenize(s.name)]);
    const descTokens = new Set(tokenize(s.description));
    let score = 0;
    let allMatched = true;
    for (const qt of qTokens) {
      let best = 0;
      for (const ht of nameTokens) {
        if (ht === qt) { best = 3; break; }
        if (ht.startsWith(qt)) best = Math.max(best, 2);
      }
      if (best < 3) {
        for (const ht of descTokens) {
          if (ht.startsWith(qt)) { best = Math.max(best, 1); break; }
        }
      }
      if (best === 0) { allMatched = false; break; }
      score += best;
    }
    if (allMatched) out.push({ technique: s, score });
  }
  out.sort((a, b) => b.score - a.score || a.technique.slug.length - b.technique.slug.length || a.technique.slug.localeCompare(b.technique.slug));
  // Cap kept tight (10) because results render inline with the controls
  // panel in a shared scroll container — a long tail would push layer
  // controls off-screen. Keep typing to narrow if 10 isn't enough.
  return out.slice(0, 10).map(r => r.technique);
}

function renderSearchResults(rows, { semantic = false } = {}) {
  if (!rows || !rows.length) {
    techniqueSearchResults.innerHTML = `<div class="technique-search-empty">${semantic ? "No semantic matches." : "No matches. Click <strong>Search</strong> for a semantic lookup."}</div>`;
    return;
  }
  const html = rows.map(s => {
    const kind = esc(s.kind || "");
    const name = esc(s.name || s.slug || "");
    const slug = esc(s.slug || "");
    const desc = esc((s.description || "").trim().split(/\s+/).slice(0, 28).join(" "));
    return `<div class="technique-result-row" data-slug="${slug}">
      <div class="technique-result-meta">
        <span class="technique-result-kind kind-${kind}">${kind}</span>
        <div class="technique-result-text">
          <div class="technique-result-name">${name}</div>
          <div class="technique-result-desc">${desc}</div>
        </div>
      </div>
      <button type="button" class="technique-result-add" data-slug="${slug}" title="Add to canvas">+ Add</button>
    </div>`;
  }).join("");
  techniqueSearchResults.innerHTML = html;
}

function showSearchResults(show) {
  // Results coexist with the layer controls in one scroll zone — only the
  // results visibility toggles. The controls stay visible underneath.
  techniqueSearchResults.hidden = !show;
}

function updateSearch() {
  if (!inSearchMode) return;
  const q = input.value.trim();
  // Enable the Search button only when the agent isn't busy and there's a query
  if (!agentBusy) sendBtn.disabled = !q;
  if (!q) { showSearchResults(false); return; }
  renderSearchResults(rankTechniques(q));
  showSearchResults(true);
}

function setSearchMode(on) {
  inSearchMode = !!on;
  if (on) {
    input.placeholder = SEARCH_PLACEHOLDER;
    if (!agentBusy) {
      sendBtn.textContent = "Search";
      sendBtn.disabled = !input.value.trim();
    }
    loadTechniques().then(() => updateSearch());
  } else {
    input.placeholder = CHAT_PLACEHOLDER;
    if (!agentBusy) {
      sendBtn.textContent = "Send";
      sendBtn.disabled = false;
    }
    showSearchResults(false);
  }
  form.classList.toggle("search-mode", inSearchMode);
}

input.addEventListener("input", updateSearch);
input.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && inSearchMode) {
    e.preventDefault();
    input.value = "";
    setControlsOpen(false);
  }
});

techniqueSearchResults.addEventListener("click", async (e) => {
  const btn = e.target.closest(".technique-result-add");
  if (!btn) return;
  const slug = btn.dataset.slug;
  if (!slug) return;
  btn.disabled = true;
  try {
    const r = await post("/api/add_layer", { technique_slug: slug });
    render(r.events || []);
  } catch (err) {
    add("error", err.message);
  } finally {
    btn.disabled = false;
  }
});
function renderPanel(panel, movableLayers = 0, maxChain = 0) {
  const widgets = (panel.schema || []).map(spec => renderWidget(panel, spec)).join("");
  const empty = widgets || `<div class="ctl-empty">No controls for this layer.</div>`;
  const ci = Number(panel.chain_index);
  const movable = ci > 0 && movableLayers > 1;
  const upDisabled = ci >= maxChain;
  const downDisabled = ci <= 1;
  const moveBtns = movable
    ? `<div class="ctl-move">
        <button type="button" class="ctl-move-btn" data-chain="${ci}" data-dir="up" ${upDisabled ? "disabled" : ""} title="Move layer up" aria-label="Move layer up">▲</button>
        <button type="button" class="ctl-move-btn" data-chain="${ci}" data-dir="down" ${downDisabled ? "disabled" : ""} title="Move layer down" aria-label="Move layer down">▼</button>
      </div>`
    : "";
  const kind = String(panel.kind || "").toLowerCase();
  const depth = maxChain > 0 ? ci / maxChain : 0;
  const subtitle = panel.kind ? esc(panel.kind) : `Layer ${panel.chain_index}`;
  return `<section class="ctl-panel kind-${esc(kind)}" style="--depth:${depth.toFixed(3)}" data-chain="${panel.chain_index}" data-kind="${esc(panel.kind || "")}" data-technique="${esc(panel.technique_name)}">
    <header class="ctl-head">
      <div class="ctl-controls">
        <button type="button" class="ctl-remove" data-chain="${panel.chain_index}" title="Remove layer" aria-label="Remove layer"></button>
        ${moveBtns}
      </div>
      <div><strong>${esc(panel.technique_name)}</strong><span>${subtitle}</span></div>
      <span class="ctl-layer-num" aria-hidden="true">${ci}</span>
    </header>
    <div class="ctl-body">${empty}</div>
  </section>`;
}
controlsToggle.addEventListener("click", () => setControlsOpen(!controlsDrawer.classList.contains("open")));
controlsPanel.addEventListener("click", async e => {
  const global = e.target.closest("#globalRegenerate,#globalRandomize");
  if (global) {
    applyControls(global.id === "globalRandomize", global);
    return;
  }
  const videoTier = e.target.closest(".vp-size-btn");
  if (videoTier) { runVideoTier(videoTier); return; }
  const videoToggle = e.target.closest("[data-video-toggle]");
  if (videoToggle) {
    const key = controlKey(videoToggle.dataset.chain, videoToggle.dataset.name);
    if (videoSliders.has(key)) videoSliders.delete(key);
    else videoSliders.add(key);
    renderControlsPanel(currentControlsPanels);
    return;
  }
  const videoBtn = e.target.closest("#globalVideo");
  if (videoBtn) {
    if (!videoBtn.disabled) setVideoPopupOpen(controlsPanel.querySelector("#videoPopup")?.hidden !== false);
    return;
  }
  const target = e.target;
  const remove = target.closest(".ctl-remove");
  if (remove) {
    const btn = remove;
    if (btn.disabled) return;
    btn.disabled = true;
    loaderTicketStart();
    try { render((await post("/api/layer_delete", {chain_index: +btn.dataset.chain})).events); }
    catch (err) { add("error", err.message); }
    finally { loaderTicketEnd(); }
    return;
  }
  const move = target.closest(".ctl-move-btn");
  if (move) {
    if (move.disabled) return;
    const from = +move.dataset.chain;
    const to = move.dataset.dir === "up" ? from + 1 : from - 1;
    if (to < 1) return;
    move.disabled = true;
    loaderTicketStart();
    try { render((await post("/api/layer_move", {from_index: from, to_index: to})).events); }
    catch (err) { add("error", err.message); }
    finally { loaderTicketEnd(); }
    return;
  }
  const palTrigger = target.closest("[data-palette-trigger]");
  if (palTrigger) {
    const pop = palTrigger.parentElement.querySelector(".ctl-palette-pop");
    const willOpen = pop.hidden;
    controlsPanel.querySelectorAll(".ctl-palette-pop:not([hidden])").forEach(p => { if (p !== pop) p.hidden = true; });
    pop.hidden = !willOpen;
    palTrigger.setAttribute("aria-expanded", willOpen ? "true" : "false");
    return;
  }
  const sw = target.closest("button[data-palette]");
  if (sw) {
    const row = sw.closest(".ctl-palette");
    const chain = +row.dataset.chain;
    row.querySelectorAll(".swatch").forEach(b => {
      b.classList.toggle("active", b === sw);
      b.setAttribute("aria-pressed", b === sw ? "true" : "false");
    });
    stageControl({chain_index: chain, name: "palette", value: sw.dataset.palette});
    const cur = row.querySelector(".ctl-palette-cur");
    if (cur) cur.innerHTML = sw.innerHTML;
    const pop = row.querySelector(".ctl-palette-pop");
    if (pop) pop.hidden = true;
    const trig = row.querySelector(".ctl-palette-trigger");
    if (trig) trig.setAttribute("aria-expanded", "false");
    return;
  }
  if (target.matches(".ctl-seg")) {
    target.parentElement.querySelectorAll(".ctl-seg").forEach(b => b.classList.toggle("active", b === target));
    stageControl({chain_index: +target.dataset.chain, name: target.dataset.name, value: JSON.parse(target.dataset.value)});
    return;
  }
  const pan = target.closest(".ctl-pan");
  const arrow = target.closest("button[data-dir]");
  if (pan && arrow) {
    const step = +pan.dataset.step || 0.1;
    let x = +pan.dataset.x || 0, y = +pan.dataset.y || 0;
    if (arrow.dataset.dir === "left") x -= step;
    else if (arrow.dataset.dir === "right") x += step;
    else if (arrow.dataset.dir === "up") y -= step;
    else if (arrow.dataset.dir === "down") y += step;
    pan.dataset.x = x; pan.dataset.y = y;
    const cc = pan.parentElement.querySelector(".ctl-pan-val"); if (cc) cc.textContent = `x ${fmtNum(x)} · y ${fmtNum(y)}`;
    const ci = +pan.dataset.chain;
    const xp = pan.dataset.xparam, yp = pan.dataset.yparam;
    if (arrow.dataset.dir === "left" || arrow.dataset.dir === "right") stageControl({chain_index: ci, name: xp, value: x});
    else stageControl({chain_index: ci, name: yp, value: y});
    return;
  }
});
document.addEventListener("click", e => {
  const control = e.target.closest(".ctl-palette-control");
  controlsPanel.querySelectorAll(".ctl-palette-pop:not([hidden])").forEach(pop => {
    if (control && control.contains(pop)) return;
    pop.hidden = true;
    const trig = pop.parentElement.querySelector(".ctl-palette-trigger");
    if (trig) trig.setAttribute("aria-expanded", "false");
  });
});
controlsPanel.addEventListener("input", e => {
  const el = e.target;
  if (el.id === "videoFps" || el.id === "videoSeconds") {
    if (el.id === "videoFps") videoFpsValue = Math.min(30, Math.max(1, Math.round(Number(el.value) || 1)));
    else videoSecondsValue = Math.min(10, Math.max(0.1, Number(el.value) || 0.1));
    updateVideoFrames();
    return;
  }
  const chain = +el.dataset.chain;
  if (Number.isNaN(chain)) return;
  if (el.dataset.kind === "slider") {
    const valEl = el.parentElement.querySelector(".ctl-val");
    if (valEl) valEl.textContent = fmtNum(+el.value);
    el.style.setProperty("--fill", sliderPct(el.min, el.max, el.value) + "%");
    stageControl({chain_index: chain, name: el.dataset.name, value: +el.value});
  }
  if (el.dataset.kind === "text") {
    stageControl({chain_index: chain, name: el.dataset.name, value: el.value});
  }
});
controlsPanel.addEventListener("change", e => {
  const el = e.target;
  const chain = +el.dataset.chain;
  if (Number.isNaN(chain)) return;
  if (el.dataset.kind === "bool") {
    stageControl({chain_index: chain, name: el.dataset.name, value: el.checked});
  }
});

function renderWidget(panel, spec) {
  const v = panel.values || {};
  const id = `c${panel.chain_index}-${spec.name}`;
  if (spec.type === "slider") {
    const cur = stagedValue(panel.chain_index, spec.name, v[spec.name] ?? spec.default);
    const key = controlKey(panel.chain_index, spec.name);
    const active = videoSliders.has(key);
    return `<div class="ctl-row ctl-slider-row${active ? " video-selected" : ""}" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}"><span>${esc(spec.label)}</span><input id="${id}" type="range" min="${spec.min}" max="${spec.max}" step="${spec.step}" value="${cur}" style="--fill:${sliderPct(spec.min, spec.max, cur)}%" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" data-kind="slider"><span class="ctl-val">${fmtNum(cur)}</span><button type="button" class="ctl-video-toggle${active ? " active" : ""}" data-video-toggle data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" aria-pressed="${active ? "true" : "false"}" title="Include this slider in video" aria-label="Include ${esc(spec.label)} in video">&#10003;</button></div>`;
  }
  if (spec.type === "bool") {
    const on = !!stagedValue(panel.chain_index, spec.name, v[spec.name] ?? spec.default);
    return `<label class="ctl-row" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}"><span>${esc(spec.label)}</span><input type="checkbox" ${on?"checked":""} data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" data-kind="bool"></label>`;
  }
  if (spec.type === "enum") {
    const cur = stagedValue(panel.chain_index, spec.name, v[spec.name] ?? spec.default);
    const opts = (spec.options || []).map(o =>
      `<button type="button" class="${JSON.stringify(o.value)===JSON.stringify(cur)?"ctl-seg active":"ctl-seg"}" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" data-kind="enum" data-value='${esc(JSON.stringify(o.value))}'>${esc(o.label)}</button>`
    ).join("");
    return `<div class="ctl-row" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}"><span>${esc(spec.label)}</span><div class="ctl-segs">${opts}</div></div>`;
  }
  if (spec.type === "pan") {
    const xp = spec.x_param, yp = spec.y_param;
    const xv = stagedValue(panel.chain_index, xp, v[xp] ?? spec.x_default ?? 0);
    const yv = stagedValue(panel.chain_index, yp, v[yp] ?? spec.y_default ?? 0);
    return `<div class="ctl-row" data-chain="${panel.chain_index}" data-xparam="${esc(xp)}" data-yparam="${esc(yp)}"><span>${esc(spec.label)}</span><div class="ctl-pan" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" data-xparam="${esc(xp)}" data-yparam="${esc(yp)}" data-step="${spec.step}" data-x="${xv}" data-y="${yv}"><button type="button" class="ctl-pan-up" data-dir="up">↑</button><button type="button" class="ctl-pan-left" data-dir="left">←</button><span class="ctl-pan-c"></span><button type="button" class="ctl-pan-right" data-dir="right">→</button><button type="button" class="ctl-pan-down" data-dir="down">↓</button></div><span class="ctl-val ctl-pan-val">x ${fmtNum(xv)} · y ${fmtNum(yv)}</span></div>`;
  }
  if (spec.type === "text") {
    const cur = stagedValue(panel.chain_index, spec.name, v[spec.name] ?? spec.default ?? "");
    const ph = spec.placeholder ? ` placeholder="${esc(spec.placeholder)}"` : "";
    return `<label class="ctl-row" for="${id}" data-chain="${panel.chain_index}" data-name="${esc(spec.name)}"><span>${esc(spec.label)}</span><input id="${id}" type="text" value="${esc(cur)}" maxlength="${spec.max_length || 120}"${ph} data-chain="${panel.chain_index}" data-name="${esc(spec.name)}" data-kind="text"></label>`;
  }
  if (spec.type === "palette") {
    const cur = stagedValue(panel.chain_index, "palette", v.palette || "");
    const swatches = palettesCache.map(p => paletteSwatchHtml(p, cur)).join("");
    return `<div class="ctl-row ctl-palette" data-chain="${panel.chain_index}" data-name="palette"><span>${esc(spec.label || "Palette")}</span><div class="ctl-palette-control"><button type="button" class="ctl-palette-trigger" data-palette-trigger aria-haspopup="true" aria-expanded="false"><span class="ctl-palette-cur">${paletteCurBars(cur)}</span><span class="ctl-palette-caret">▾</span></button><div class="ctl-palette-pop" hidden>${swatches}</div></div></div>`;
  }
  return "";
}
function fmtNum(v) {
  if (typeof v !== "number") return String(v);
  const abs = Math.abs(v);
  return abs >= 100 ? v.toFixed(0) : abs >= 10 ? v.toFixed(1) : v.toFixed(2);
}
function sliderPct(min, max, val) {
  const lo = Number(min), hi = Number(max), v = Number(val);
  if (!(hi > lo)) return 0;
  return Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
}
function controlKey(chain, name) { return `${chain}.${name}`; }
function stagedValue(chain, name, fallback) {
  return pendingControls.get(controlKey(chain, name))?.value ?? fallback;
}
function currentControlValue(chain, name) {
  const panel = currentControlsPanels.find(p => +p.chain_index === +chain);
  return panel?.values ? panel.values[name] : undefined;
}
function stageControl(body) {
  const key = controlKey(body.chain_index, body.name);
  if (JSON.stringify(currentControlValue(body.chain_index, body.name)) === JSON.stringify(body.value)) pendingControls.delete(key);
  else pendingControls.set(key, body);
  markDirtyControls();
}
function markDirtyControls() {
  controlsPanel.querySelectorAll(".ctl-row[data-chain]").forEach(row => {
    const chain = row.dataset.chain;
    const names = row.dataset.xparam ? [row.dataset.xparam, row.dataset.yparam] : [row.dataset.name];
    row.classList.toggle("row-dirty", names.some(n => n && pendingControls.has(`${chain}.${n}`)));
  });
  controlsPanel.querySelectorAll("#globalRegenerate,#globalRandomize").forEach(b => b.classList.toggle("dirty", pendingControls.size > 0));
  const specs = selectedVideoSpecs();
  const videoBtn = controlsPanel.querySelector("#globalVideo");
  if (videoBtn) videoBtn.disabled = specs.length < 1;
  const summary = controlsPanel.querySelector("#videoSummary");
  if (summary) summary.textContent = videoSummaryText();
}
function clearPendingControls(refresh = true) {
  pendingControls.clear();
  if (refresh) renderControlsPanel(currentControlsPanels);
  else markDirtyControls();
}
async function applyControls(forceNewSeed, btn) {
  if (controlsPanel.classList.contains("loading")) return;
  controlsPanel.classList.add("loading");
  controlsPanel.querySelectorAll(".ctl-global").forEach(b => b.disabled = true);
  loaderTicketStart();
  try {
    const r = await post("/api/regenerate", {controls: [...pendingControls.values()], force_new_seed: !!forceNewSeed});
    if (!(r.events || []).some(ev => ev.type === "error")) clearPendingControls(false);
    render(r.events);
  }
  catch (err) { add("error", err.message); }
  finally {
    controlsPanel.classList.remove("loading");
    controlsPanel.querySelectorAll(".ctl-global").forEach(b => b.disabled = false);
    if (btn) btn.disabled = false;
    markDirtyControls();
    loaderTicketEnd();
  }
}
function esc(x) { return String(x ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

// ----- Video popup -----
function selectedVideoSpecs() {
  const specs = [];
  for (const panel of currentControlsPanels) {
    for (const spec of (panel.schema || [])) {
      if (spec.type !== "slider") continue;
      if (videoSliders.has(controlKey(panel.chain_index, spec.name))) specs.push({chain_index: Number(panel.chain_index), name: spec.name});
    }
  }
  return specs;
}
function pruneVideoSliders() {
  const valid = new Set();
  for (const panel of currentControlsPanels) {
    for (const spec of (panel.schema || [])) if (spec.type === "slider") valid.add(controlKey(panel.chain_index, spec.name));
  }
  for (const key of [...videoSliders]) if (!valid.has(key)) videoSliders.delete(key);
}
function videoSummaryText() {
  const n = selectedVideoSpecs().length;
  return `${n} slider${n === 1 ? "" : "s"} selected`;
}
function updateVideoFrames() {
  const videoFrames = controlsPanel.querySelector("#videoFrames");
  if (!videoFrames) return;
  const fps = Math.min(30, Math.max(0, Number(controlsPanel.querySelector("#videoFps")?.value) || 0));
  const secs = Math.min(10, Math.max(0, Number(controlsPanel.querySelector("#videoSeconds")?.value) || 0));
  const n = Math.round(fps * secs);
  videoFrames.textContent = n >= 2 ? `${n} frames` : "— frames (raise fps or seconds)";
}
function refreshVideoTierLabels() {
  controlsPanel.querySelectorAll("#videoPopup .vp-size-btn").forEach(btn => {
    const [w, h] = downloadDimsForScale(Number(btn.dataset.scale) || 1);
    const dims = btn.querySelector(".vp-size-dims");
    if (dims) dims.textContent = `${w} × ${h}`;
  });
}
function renderVideoPopup() {
  return `<div id="videoPopup" class="video-popup" hidden>
    <div class="vp-grid">
      <label class="vp-field"><span>FPS</span><input id="videoFps" type="number" min="1" max="30" step="1" value="${videoFpsValue}"></label>
      <label class="vp-field"><span>Seconds</span><input id="videoSeconds" type="number" min="0.1" max="10" step="0.1" value="${videoSecondsValue}"></label>
    </div>
    <p class="vp-frames" id="videoFrames">${Math.round(videoFpsValue * videoSecondsValue)} frames</p>
    <p class="vp-summary" id="videoSummary">${videoSummaryText()}</p>
    <div class="vp-tiers">
      <button type="button" class="vp-size-btn" data-scale="0.5"><span class="vp-size-label">Low</span><span class="vp-size-dims">— × —</span></button>
      <button type="button" class="vp-size-btn" data-scale="1"><span class="vp-size-label">Medium</span><span class="vp-size-dims">— × —</span></button>
    </div>
  </div>`;
}
function setVideoPopupOpen(open) {
  const popup = controlsPanel.querySelector("#videoPopup");
  if (!popup) return;
  if (open && selectedVideoSpecs().length < 1) return;
  const opening = open && popup.hidden;
  popup.hidden = !open;
  if (opening) {
    if (!downloadPanel.hidden) setDownloadPanelOpen(false);
    if (sharePanel && !sharePanel.hidden) setSharePanelOpen(false);
    refreshVideoTierLabels();
    updateVideoFrames();
    const summary = popup.querySelector("#videoSummary");
    if (summary) summary.textContent = videoSummaryText();
  }
}
async function runVideoTier(btn) {
  if (videoRendering && btn.classList.contains("loading")) {
    if (videoCanceling) return;
    videoCanceling = true;
    const labelEl = btn.querySelector(".vp-size-label");
    if (labelEl) labelEl.textContent = "Cancelling…";
    try { await post("/api/cancel_video"); } catch {}
    return;
  }
  if (btn.disabled) return;
  const popup = controlsPanel.querySelector("#videoPopup");
  const specs = selectedVideoSpecs();
  if (!specs.length) { add("error", "Check at least one slider first."); return; }
  const fps = Math.min(30, Math.max(1, Math.round(Number(controlsPanel.querySelector("#videoFps")?.value) || videoFpsValue)));
  const seconds = Math.min(10, Math.max(0.1, Number(controlsPanel.querySelector("#videoSeconds")?.value) || videoSecondsValue));
  const scale = Number(btn.dataset.scale) || 1;
  const labelEl = btn.querySelector(".vp-size-label");
  const orig = labelEl ? labelEl.textContent : "";
  videoFpsValue = fps;
  videoSecondsValue = seconds;
  videoRendering = true;
  videoCanceling = false;
  popup?.querySelectorAll(".vp-size-btn").forEach(b => b.disabled = b !== btn);
  btn.classList.add("loading", "cancel");
  if (labelEl) labelEl.textContent = "Cancel";
  loaderTicketStart();
  try {
    const r = await post("/api/render_video", {specs, controls: [...pendingControls.values()], fps, seconds, scale});
    const ev = (r?.events || []).find(e => e.type === "video_ready");
    if (!ev || !ev.url) {
      const err = (r?.events || []).find(e => e.type === "error");
      add("error", (err && err.content) || "Video failed.");
      return;
    }
    const a = document.createElement("a");
    a.href = ev.url;
    a.download = `secondbrain-${ev.width}x${ev.height}-${ev.frames}f.gif`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    add("error", err.message);
  } finally {
    videoRendering = false;
    videoCanceling = false;
    popup?.querySelectorAll(".vp-size-btn").forEach(b => b.disabled = false);
    btn.classList.remove("loading", "cancel");
    if (labelEl) labelEl.textContent = orig;
    loaderTicketEnd();
    renderMeter.hidden = true;
  }
}
document.addEventListener("pointerdown", e => {
  const popup = controlsPanel.querySelector("#videoPopup");
  if (!popup || popup.hidden) return;
  const wrap = e.target.closest(".video-action-wrap");
  if (wrap && wrap.contains(popup)) return;
  setVideoPopupOpen(false);
});
document.addEventListener("keydown", e => {
  const popup = controlsPanel.querySelector("#videoPopup");
  if (e.key === "Escape" && popup && !popup.hidden) setVideoPopupOpen(false);
});

// ----- Canvas loader bookkeeping -----
let userTickets = 0;
const activeRenderTools = new Set();

function loaderForceStop() {
  userTickets = 0; activeRenderTools.clear();
}
function loaderTicketStart() { userTickets++; }
function loaderTicketEnd() { if (userTickets > 0) userTickets--; }
function loaderToolStart(id) { activeRenderTools.add(id); }
function loaderToolEnd(id) { activeRenderTools.delete(id); }

// ----- Chat + actions -----
form.addEventListener("submit", async e => {
  e.preventDefault();
  if (agentBusy) return;
  const text = input.value.trim();
  if (!text) return;
  if (inSearchMode) {
    // Semantic fallback — call /api/search_techniques and render its results
    // alongside (in place of) the prefix-rank hits.
    sendBtn.disabled = true;
    try {
      const r = await post("/api/search_techniques", { query: text, limit: 10 });
      renderSearchResults(r.techniques || [], { semantic: true });
      showSearchResults(true);
    } catch (err) {
      add("error", err.message);
    } finally {
      sendBtn.disabled = !input.value.trim();
    }
    return;
  }
  input.value = "";
  add("user", text);
  bottom(true);
  loaderTicketStart();
  setBusy(true);
  try { render((await post("/api/chat", {message:text})).events); }
  catch (err) { add("error", err.message); }
  finally { loaderTicketEnd(); setTyping(false); setBusy(false); }
});
document.querySelector("#newChat").addEventListener("click", async () => {
  messages.innerHTML = `<div class="ephemeral-note" id="tipNote"><strong>Tip</strong><span id="tipText"></span></div>`;
  pickTip();
  // Rebuild the empty-state tutorial so its first card re-rolls a fresh set
  // of prompt suggestions each time the visitor starts over.
  if (window.SBTutorial && emptyState) {
    window.SBTutorial.build(emptyState, { onTryIt: tutorialTryIt, onSearchDemo: tutorialSearchDemo });
  }
  render((await post("/api/new")).events);
});

// Tutorial carousel: live hero (replaces the old empty-state copy) + Help modal.
// Set when a tutorial chip kicks off a prompt — the next hero-image load
// is the visitor's first ever render. At that moment we pulse "+ New
// canvas" so they learn the "start over" affordance exists before they're
// staring at their result going "now what?"
let tutorialChipPending = false;
function tutorialTryIt(prompt) {
  // Prompts are agent-bound — close the controls drawer so the left column
  // is back in chat mode before we drop the suggestion in.
  if (controlsDrawer.classList.contains("open")) setControlsOpen(false);
  if (prompt) input.value = prompt;
  input.focus();
  const modal = document.querySelector("#helpModal");
  if (modal && !modal.hidden) modal.hidden = true;
  tutorialChipPending = true;
}
function tutorialSearchDemo(query) {
  // Step 4 demo: open the controls drawer (which flips the composer into
  // search mode) and seed the input, then fire `input` so the search wires
  // pick it up just as if the user had typed it themselves.
  if (!controlsDrawer.classList.contains("open")) setControlsOpen(true);
  input.value = query;
  input.focus();
  input.dispatchEvent(new Event("input", { bubbles: true }));
  const modal = document.querySelector("#helpModal");
  if (modal && !modal.hidden) modal.hidden = true;
}
if (window.SBTutorial) {
  window.SBTutorial.build(emptyState, { onTryIt: tutorialTryIt, onSearchDemo: tutorialSearchDemo });
}
heroImage?.addEventListener("load", () => {
  if (!tutorialChipPending) return;
  tutorialChipPending = false;
});
const helpModal = document.querySelector("#helpModal");
const helpModalBody = document.querySelector("#helpModalBody");
const helpBtn = document.querySelector("#helpBtn");
if (helpBtn && helpModal && helpModalBody && window.SBTutorial) {
  helpBtn.addEventListener("click", () => {
    window.SBTutorial.build(helpModalBody, { onTryIt: tutorialTryIt, onSearchDemo: tutorialSearchDemo });
    helpModal.hidden = false;
  });
  helpModal.addEventListener("click", e => { if (e.target === helpModal) helpModal.hidden = true; });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && !helpModal.hidden) helpModal.hidden = true;
  });
}

const DOWNLOAD_LONG_CAP = 8192;
// Scale (w, h) by `scale`, clamping the long edge to DOWNLOAD_LONG_CAP and the
// short edge to a 64px floor — mirrors render_for_download on the backend.
function downloadDimsForScale(scale) {
  const w0 = currentCanvasWidth > 0 ? currentCanvasWidth : (currentCanvasSize || 1024);
  const h0 = currentCanvasHeight > 0 ? currentCanvasHeight : (currentCanvasSize || 1024);
  let w = Math.round(w0 * scale), h = Math.round(h0 * scale);
  const long = Math.max(w, h);
  if (long > DOWNLOAD_LONG_CAP) { const f = DOWNLOAD_LONG_CAP / long; w = Math.round(w * f); h = Math.round(h * f); }
  return [Math.max(64, w), Math.max(64, h)];
}
function refreshDownloadTierLabels() {
  downloadPanel.querySelectorAll(".dp-size-btn").forEach(btn => {
    const scale = Number(btn.dataset.scale) || 1;
    const [w, h] = downloadDimsForScale(scale);
    const dims = btn.querySelector(".dp-size-dims");
    if (dims) dims.textContent = `${w} × ${h}`;
  });
}
function setDownloadPanelOpen(open) {
  const opening = open && downloadPanel.hidden;
  downloadPanel.hidden = !open;
  if (opening) {
    if (!sharePanel.hidden) setSharePanelOpen(false);
    refreshDownloadTierLabels();
  }
}
async function runDownloadTier(btn) {
  if (btn.disabled) return;
  const scale = Number(btn.dataset.scale) || 1;
  const labelEl = btn.querySelector(".dp-size-label");
  const dimsEl = btn.querySelector(".dp-size-dims");
  const origLabel = labelEl ? labelEl.textContent : "";
  const origDims = dimsEl ? dimsEl.textContent : "";
  btn.disabled = true;
  btn.classList.add("loading");
  if (labelEl) labelEl.textContent = "Rendering…";
  if (dimsEl) dimsEl.textContent = "";
  try {
    const r = await post("/api/render_for_download", {scale});
    const ev = (r?.events || []).find(e => e.type === "download_ready");
    if (!ev || !ev.url) {
      const err = (r?.events || []).find(e => e.type === "error");
      add("error", (err && err.content) || "Download failed.");
      return;
    }
    // Trigger the actual file download via a hidden anchor.
    const a = document.createElement("a");
    a.href = ev.url;
    const shortHash = (ev.pool_hash || "").slice(0, 8);
    a.download = `secondbrain-${ev.width}x${ev.height}${shortHash ? "-" + shortHash : ""}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    post("/api/download").catch(() => {});
    setDownloadPanelOpen(false);
  } catch (err) {
    add("error", err.message);
  } finally {
    btn.disabled = false;
    btn.classList.remove("loading");
    if (labelEl) labelEl.textContent = origLabel;
    if (dimsEl) dimsEl.textContent = origDims;
  }
}
downloadImage.addEventListener("click", () => {
  if (!currentCanvasHasImage) return;
  setDownloadPanelOpen(downloadPanel.hidden);
});
downloadPanel.addEventListener("click", e => {
  const btn = e.target.closest(".dp-size-btn");
  if (btn) runDownloadTier(btn);
});
document.addEventListener("pointerdown", e => {
  if (downloadPanel.hidden) return;
  if (downloadPanel.contains(e.target) || downloadImage.contains(e.target)) return;
  setDownloadPanelOpen(false);
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && !downloadPanel.hidden) setDownloadPanelOpen(false);
});
function setShareLink(url, qrUrl) {
  if (shareLinkInput) shareLinkInput.value = url || "";
  if (qrUrl) {
    if (shareQrImg) shareQrImg.src = qrUrl;
    if (shareQrDownload) shareQrDownload.href = qrUrl;
  }
}
async function fetchCurrentShareLink() {
  setShareLink("", "");
  try {
    const r = await post("/api/get_link", {kind: "current"});
    if (r && r.ok && r.url) setShareLink(r.url, r.qr_url);
    else shareLinkInput.value = (r && r.error) || "Nothing to share yet — make something first.";
  } catch (err) { shareLinkInput.value = "Could not generate link."; }
}
async function copyToClipboard(text, btn) {
  if (!text || /^Nothing to share|^Could not/.test(text)) return;
  try { await navigator.clipboard.writeText(text); }
  catch { try { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); } catch {} }
  if (btn) {
    btn.classList.add("copied");
    setTimeout(() => btn.classList.remove("copied"), 1200);
  }
}
function setSharePanelOpen(open) {
  const opening = open && sharePanel.hidden;
  sharePanel.hidden = !open;
  if (opening) {
    if (!downloadPanel.hidden) setDownloadPanelOpen(false);
    fetchCurrentShareLink();
  }
}
shareBtn.addEventListener("click", () => setSharePanelOpen(sharePanel.hidden));
document.addEventListener("pointerdown", e => {
  if (sharePanel.hidden) return;
  if (sharePanel.contains(e.target) || shareBtn.contains(e.target)) return;
  setSharePanelOpen(false);
});
copyShareLinkBtn?.addEventListener("click", () => copyToClipboard(shareLinkInput.value, copyShareLinkBtn));
toggleShareQrBtn?.addEventListener("click", () => {
  const showing = shareQrWrap.hidden;
  shareQrWrap.hidden = !showing;
  toggleShareQrBtn.setAttribute("aria-pressed", String(showing));
});

function openLinkModal(url, qrUrl, shareId) {
  linkModalUrl.value = url || "";
  if (qrUrl) { linkModalQr.src = qrUrl; linkModalDownload.href = qrUrl; }
  linkModalDownload.download = `second-brain-${shareId || "share"}.png`;
  linkModal.hidden = false;
}
linkModalCopy?.addEventListener("click", () => copyToClipboard(linkModalUrl.value, linkModalCopy));
document.querySelectorAll('[data-close="linkModal"]').forEach(b => b.addEventListener("click", () => linkModal.hidden = true));

async function handleShareDeepLink() {
  const params = new URLSearchParams(location.search);
  const shareId = params.get("share");
  if (!shareId) return;
  // Strip the param so reloads don't re-trigger remix.
  params.delete("share");
  const qs = params.toString();
  history.replaceState({}, "", location.pathname + (qs ? "?" + qs : ""));
  scrollTo({top:0, behavior:"smooth"});
  loaderTicketStart();
  try { render((await post("/api/remix", {share_id: shareId})).events); }
  catch (err) { add("error", err.message); }
  finally { loaderTicketEnd(); }
}
(function rehydrateAccents() {
  try {
    const a = JSON.parse(localStorage.sbAccents || "null");
    if (!a) return;
    const root = document.documentElement.style;
    if (a.accent) root.setProperty("--accent", a.accent);
    if (a.accent2) root.setProperty("--accent-2", a.accent2);
    if (a.glow) root.setProperty("--accent-glow", a.glow);
    if (a.glow2) root.setProperty("--accent-2-glow", a.glow2);
  } catch {}
})();
async function loadHistory() {
  try {
    const r = await get("/api/history");
    const msgs = Array.isArray(r.history) ? r.history : [];
    if (!msgs.length) return;
    // Replace boilerplate greeting only when real history exists.
    messages.innerHTML = "";
    for (const m of msgs) add(m.role === "user" ? "user" : "assistant", m.content, m.role === "assistant");
  } catch {}
}
document.addEventListener("keydown", async (e) => {
  const mod = e.ctrlKey || e.metaKey;
  if (!mod || (e.key !== "z" && e.key !== "Z")) return;
  // Don't hijack native text undo inside editable fields.
  const t = e.target;
  if (t && t.matches && t.matches("input, textarea, [contenteditable=''], [contenteditable='true']")) return;
  e.preventDefault();
  const url = e.shiftKey ? "/api/redo" : "/api/undo";
  try { render((await post(url, {})).events); } catch {}
});
connectEvents();
const bootingShare = new URLSearchParams(location.search).has("share");
loadHistory(); loadPalettes(); if (bootingShare) handleShareDeepLink(); else loadCanvas(); refreshSettings();
