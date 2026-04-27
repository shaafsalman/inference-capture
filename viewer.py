"""
viewer.py
---------
Lightweight Flask web application for browsing captured inference datasets.

Serves a single-page UI that reads JSONL files from the data/ directory and
displays each record (input, chain-of-thought, answer, params, token usage)
in a searchable, filterable table with expand-in-place detail panels.

Usage:
    python viewer.py
    # Then open http://localhost:8003 in your browser
"""

import os
import json
import glob
from flask import Flask, jsonify, Response

DATA_DIR = "data"
VIEWER_PORT = 8003

app = Flask(__name__, static_folder=None)


@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.route("/api/files")
def list_files():
    """Return a sorted list of JSONL filenames found in DATA_DIR."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.jsonl")))
    return jsonify([os.path.basename(f) for f in files])


@app.route("/api/records/<filename>")
def get_records(filename):
    """
    Parse and return all valid JSON records from a JSONL file.
    Each record gets a 1-based 'row' field injected for UI tracking.
    Invalid lines are silently skipped.
    """
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return jsonify([])
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                r["row"] = i
                records.append(r)
            except json.JSONDecodeError:
                pass
    return jsonify(records)


# ---------------------------------------------------------------------------
# Embedded single-page UI
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dataset Viewer</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #f2f2f5; --surface: #eaeaee; --surface2: #e0e0e6; --surface3: #d4d4dc;
  --border: #c8c8d0; --border2: #b4b4c0;
  --accent: #5b4fd4; --accent-l: #ede9ff; --accent-d: #4438b0;
  --green: #1a7a4a; --green-l: #e0f5eb;
  --yellow: #7a5400; --yellow-l: #fef3d0;
  --blue: #1a5fa8; --blue-l: #deeeff;
  --red: #b83232; --red-l: #ffecec;
  --text: #161618; --text2: #38383c; --text3: #60606a; --text4: #9898a8;
  --mono: 'JetBrains Mono', monospace; --sans: 'Inter', sans-serif;
  --fs: 13px; --radius: 8px;
}
body { background: var(--bg); color: var(--text); font-family: var(--sans); font-size: var(--fs); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.topbar { height: 54px; flex-shrink: 0; display: flex; align-items: center; gap: 12px; padding: 0 20px; background: var(--surface); border-bottom: 1px solid var(--border2); box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.logo { font-family: var(--mono); font-size: 15px; font-weight: 700; letter-spacing: -0.04em; }
.logo span { color: var(--accent); }
.sep { width: 1px; height: 22px; background: var(--border2); margin: 0 2px; }
.topbar-right { margin-left: auto; display: flex; align-items: center; gap: 8px; }

select, input[type=text] { background: white; border: 1px solid var(--border2); color: var(--text); font-family: var(--mono); font-size: 12px; padding: 6px 10px; border-radius: var(--radius); outline: none; transition: border-color .15s, box-shadow .15s; }
select:focus, input[type=text]:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,79,212,.12); }
#fileSelect { min-width: 230px; }

.btn { background: white; border: 1px solid var(--border2); color: var(--text2); font-family: var(--mono); font-size: 11px; font-weight: 600; padding: 6px 14px; border-radius: var(--radius); cursor: pointer; transition: all .15s; display: flex; align-items: center; gap: 5px; white-space: nowrap; }
.btn:hover { color: var(--accent); border-color: var(--accent); background: var(--accent-l); }

.fs-controls { display: flex; align-items: center; gap: 4px; }
.fs-btn { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; background: white; border: 1px solid var(--border2); color: var(--text2); cursor: pointer; font-size: 15px; font-weight: 600; transition: all .15s; }
.fs-btn:hover { color: var(--accent); border-color: var(--accent); background: var(--accent-l); }
.fs-label { font-size: 11px; color: var(--text3); font-family: var(--mono); min-width: 30px; text-align: center; }

.stats-bar { height: 42px; flex-shrink: 0; display: flex; align-items: center; gap: 12px; padding: 0 20px; background: var(--surface2); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text3); }
.stat-pill { display: flex; align-items: center; gap: 5px; background: white; border: 1px solid var(--border); border-radius: 20px; padding: 3px 10px; font-size: 11px; font-family: var(--mono); }
.stat-pill b { color: var(--accent); }
.filter-wrap { margin-left: auto; display: flex; align-items: center; gap: 6px; }
#searchInput { width: 250px; }
.chip { display: flex; align-items: center; gap: 4px; background: white; border: 1px solid var(--border2); border-radius: 20px; padding: 4px 11px; font-size: 11px; font-family: var(--mono); color: var(--text3); cursor: pointer; transition: all .15s; white-space: nowrap; }
.chip:hover, .chip.active { background: var(--accent-l); border-color: var(--accent); color: var(--accent); font-weight: 600; }

.table-wrap { flex: 1; overflow: auto; scrollbar-width: thin; scrollbar-color: var(--border2) transparent; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
col.c-sel { width: 36px; } col.c-row { width: 50px; } col.c-ts { width: 148px; }
col.c-input { width: 25%; } col.c-cot { width: 28%; } col.c-answer { width: 22%; }
col.c-act { width: 76px; }

thead { position: sticky; top: 0; z-index: 20; }
thead tr { background: var(--surface); }
th { padding: 0 12px; height: 40px; text-align: left; font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; color: var(--text3); border-bottom: 2px solid var(--border2); border-right: 1px solid var(--border); white-space: nowrap; user-select: none; }
th:last-child { border-right: none; }
th.tc { text-align: center; }

tbody tr.data-row { border-bottom: 1px solid var(--border); transition: background .08s; cursor: pointer; }
tbody tr.data-row:hover { background: rgba(91,79,212,.05); }
tbody tr.data-row:nth-child(4n+1) { background: white; }
tbody tr.data-row:nth-child(4n+1):hover { background: rgba(91,79,212,.05); }
tbody tr.data-row.expanded { background: var(--accent-l) !important; }
tbody tr.data-row.selected { background: rgba(91,79,212,.09) !important; box-shadow: inset 2px 0 0 var(--accent); }

td { padding: 0 12px; height: 46px; vertical-align: middle; font-family: var(--mono); color: var(--text2); border-right: 1px solid var(--border); overflow: hidden; }
td:last-child { border-right: none; }
td.tc { text-align: center; }
td.td-ts { color: var(--text4); font-size: 11px; }

.cell-preview { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block; }
.cp-input { color: var(--yellow); font-weight: 500; }
.cp-answer { color: var(--green); font-weight: 500; }
.cp-cot { color: var(--text3); font-style: italic; }
.cp-none { color: var(--text4); font-style: italic; }

.badge-row { display: inline-flex; align-items: center; justify-content: center; font-family: var(--mono); font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 5px; min-width: 28px; background: var(--surface3); color: var(--text3); border: 1px solid var(--border2); }
.row-check { width: 15px; height: 15px; cursor: pointer; accent-color: var(--accent); }
.row-actions { display: flex; align-items: center; justify-content: center; gap: 4px; }
.icon-btn { width: 26px; height: 26px; border-radius: 5px; display: flex; align-items: center; justify-content: center; background: white; border: 1px solid var(--border2); color: var(--text3); cursor: pointer; font-size: 13px; transition: all .12s; flex-shrink: 0; }
.icon-btn:hover { color: var(--accent); border-color: var(--accent); background: var(--accent-l); }
.icon-btn.on { color: var(--accent); border-color: var(--accent); background: var(--accent-l); }

tr.detail-row td { height: auto; padding: 0; border-right: none; background: white; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1px; background: var(--border2); border-top: 3px solid var(--accent); }
.detail-col { background: white; padding: 14px 18px; min-height: 80px; }
.detail-col-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.col-label { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; display: flex; align-items: center; gap: 8px; flex: 1; }
.col-label::after { content: ''; flex: 1; height: 1px; background: var(--border); }
.lbl-i { color: var(--yellow); } .lbl-c { color: var(--text3); } .lbl-a { color: var(--green); }
.copy-btn { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .04em; padding: 3px 8px; border-radius: 4px; border: 1px solid var(--border2); background: var(--surface2); color: var(--text3); cursor: pointer; transition: all .12s; text-transform: uppercase; white-space: nowrap; }
.copy-btn:hover { background: var(--accent-l); border-color: var(--accent); color: var(--accent); }
.copy-btn.ok { background: var(--green-l); border-color: var(--green); color: var(--green); }
.detail-content { font-family: var(--mono); line-height: 1.8; font-size: var(--fs); white-space: pre-wrap; word-break: break-word; max-height: 360px; overflow-y: auto; scrollbar-width: thin; }
.dc-i { color: var(--text); } .dc-c { color: var(--text3); font-style: italic; } .dc-a { color: var(--green); font-weight: 500; }
.msg-block { margin-bottom: 12px; }
.msg-role { font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 4px; padding: 2px 7px; border-radius: 4px; display: inline-block; }
.r-user { background: var(--yellow-l); color: var(--yellow); }
.r-assistant { background: var(--accent-l); color: var(--accent); }
.r-system { background: var(--blue-l); color: var(--blue); }
.msg-body { color: var(--text); line-height: 1.75; font-family: var(--mono); font-size: var(--fs); }
.no-cot { color: var(--text4); font-style: italic; font-size: 11px; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--border); border-top: 1px solid var(--border2); }
.meta-sec { background: var(--surface); padding: 10px 18px; }
.meta-title { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text3); margin-bottom: 6px; }
.meta-row { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; border-bottom: 1px solid var(--border); }
.meta-row:last-child { border-bottom: none; }
.meta-k { font-family: var(--mono); font-size: 11px; color: var(--text3); min-width: 150px; flex-shrink: 0; }
.meta-v { font-family: var(--mono); font-size: 11px; color: var(--text); font-weight: 600; }

.bulk-bar { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #1a1a20; color: white; border-radius: 12px; padding: 10px 20px; display: flex; align-items: center; gap: 10px; box-shadow: 0 8px 32px rgba(0,0,0,.28); z-index: 100; font-size: 12px; font-family: var(--mono); animation: slideUp .15s ease-out; }
@keyframes slideUp { from { transform: translateX(-50%) translateY(10px); opacity:0; } to { transform: translateX(-50%) translateY(0); opacity:1; } }
.bb { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); color: white; font-family: var(--mono); font-size: 11px; font-weight: 600; padding: 5px 12px; border-radius: 6px; cursor: pointer; transition: background .12s; white-space: nowrap; }
.bb:hover { background: rgba(255,255,255,.2); }
.bb.g { background: rgba(26,122,74,.5); border-color: rgba(26,122,74,.7); }
.bb.r { background: rgba(184,50,50,.4); border-color: rgba(184,50,50,.6); }

.toast { position: fixed; bottom: 80px; right: 24px; background: #1a1a20; color: white; border-radius: 8px; padding: 10px 16px; font-size: 12px; font-family: var(--mono); box-shadow: 0 4px 16px rgba(0,0,0,.2); z-index: 200; animation: toastIn .15s ease-out; pointer-events: none; }
.toast.g { background: var(--green); }
@keyframes toastIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

.empty { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; gap: 10px; color: var(--text3); font-size: 13px; padding: 80px; }
.empty-icon { font-size: 42px; }
@keyframes fadeIn { from { opacity:0; transform: translateY(-3px); } to { opacity:1; transform: translateY(0); } }
tr.detail-row { animation: fadeIn .1s ease-out; }
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">inference<span>capture</span></div>
  <div class="sep"></div>
  <select id="fileSelect" onchange="loadFile()"><option value="">— select file —</option></select>
  <div class="topbar-right">
    <div class="fs-controls">
      <button class="fs-btn" onclick="changeFontSize(-1)">−</button>
      <span class="fs-label" id="fsLabel">13px</span>
      <button class="fs-btn" onclick="changeFontSize(1)">+</button>
    </div>
    <div class="sep"></div>
    <button class="btn" onclick="exportRows()">⬇ export</button>
    <button class="btn" onclick="init()">↻ refresh</button>
  </div>
</div>

<div class="stats-bar" id="statsBar" style="display:none">
  <div class="stat-pill">rows <b id="statRows">0</b></div>
  <div class="stat-pill">showing <b id="statShowing">0</b></div>
  <div class="stat-pill">selected <b id="statSel">0</b></div>
  <div class="filter-wrap">
    <div class="chip active" id="chipAll" onclick="setFilter('all')">all</div>
    <div class="chip" id="chipCot" onclick="setFilter('cot')">has cot</div>
    <div class="chip" id="chipNoCot" onclick="setFilter('nocot')">no cot</div>
    <input type="text" id="searchInput" placeholder="search input / cot / answer…" oninput="renderFiltered()">
  </div>
</div>

<div id="tableContainer" style="flex:1;display:flex;flex-direction:column;overflow:hidden;">
  <div class="empty"><div class="empty-icon">📂</div>select a file to begin</div>
</div>

<div class="bulk-bar" id="bulkBar" style="display:none">
  <span id="bulkCount">0 selected</span>
  <button class="bb g" onclick="copySelectedJSON()">📋 copy JSONL</button>
  <button class="bb g" onclick="exportRows()">⬇ export</button>
  <button class="bb" onclick="selectAllVisible()">select all</button>
  <button class="bb r" onclick="clearSel()">✕ clear</button>
</div>

<script>
let allRecords = [], fontSize = 13, selectedRows = new Set(), activeFilter = 'all';

function changeFontSize(d) {
  fontSize = Math.min(20, Math.max(10, fontSize + d));
  document.documentElement.style.setProperty('--fs', fontSize + 'px');
  document.getElementById('fsLabel').textContent = fontSize + 'px';
}

function setFilter(f) {
  activeFilter = f;
  document.getElementById('chipAll').classList.toggle('active', f==='all');
  document.getElementById('chipCot').classList.toggle('active', f==='cot');
  document.getElementById('chipNoCot').classList.toggle('active', f==='nocot');
  renderFiltered();
}

async function init() {
  const sel = document.getElementById('fileSelect'), cur = sel.value;
  const files = await fetch('/api/files').then(r=>r.json());
  sel.innerHTML = '<option value="">— select file —</option>';
  files.forEach(f => {
    const o = document.createElement('option');
    o.value = f; o.textContent = f;
    if (f === cur) o.selected = true;
    sel.appendChild(o);
  });
  if (cur && files.includes(cur)) loadFile();
}

async function loadFile() {
  const fn = document.getElementById('fileSelect').value;
  selectedRows.clear(); updateBulkBar();
  if (!fn) {
    allRecords = [];
    document.getElementById('statsBar').style.display = 'none';
    document.getElementById('tableContainer').innerHTML = '<div class="empty"><div class="empty-icon">📂</div>select a file to begin</div>';
    return;
  }
  document.getElementById('tableContainer').innerHTML = '<div class="empty"><div class="empty-icon">⏳</div>loading…</div>';
  allRecords = await fetch(`/api/records/${encodeURIComponent(fn)}`).then(r=>r.json());
  document.getElementById('statsBar').style.display = 'flex';
  document.getElementById('statRows').textContent = allRecords.length;
  renderFiltered();
}

function getFiltered() {
  const q = document.getElementById('searchInput').value.toLowerCase().trim();
  return allRecords.filter(r => {
    if (activeFilter==='cot' && !r.cot) return false;
    if (activeFilter==='nocot' && r.cot) return false;
    if (!q) return true;
    return (r.input||'').toLowerCase().includes(q) || (r.answer||'').toLowerCase().includes(q) || (r.cot||'').toLowerCase().includes(q);
  });
}

function renderFiltered() {
  const f = getFiltered();
  document.getElementById('statShowing').textContent = f.length;
  renderTable(f);
}

function renderTable(records) {
  const c = document.getElementById('tableContainer');
  if (!records.length) { c.innerHTML = '<div class="empty"><div class="empty-icon">🔍</div>no matching records</div>'; return; }

  let html = `<div class="table-wrap"><table>
    <colgroup><col class="c-sel"><col class="c-row"><col class="c-ts"><col class="c-input"><col class="c-cot"><col class="c-answer"><col class="c-act"></colgroup>
    <thead><tr>
      <th class="tc"><input type="checkbox" class="row-check" id="chkAll" onchange="toggleSelectAll(this)"></th>
      <th class="tc">#</th><th>Timestamp</th><th>Input</th><th>Chain of Thought</th><th>Answer</th>
      <th class="tc">Actions</th>
    </tr></thead><tbody>`;

  records.forEach(r => {
    const ip = previewInput(r.input);
    const cp = r.cot ? r.cot.slice(0,85).replace(/\n/g,' ')+(r.cot.length>85?'…':'') : '';
    const ap = (r.answer||'').slice(0,85).replace(/\n/g,' ')+((r.answer||'').length>85?'…':'');
    const ts = (r.timestamp||'').replace('T',' ').slice(0,19);
    const sel = selectedRows.has(r.row);
    html += `
    <tr class="data-row${sel?' selected':''}" id="row-${r.row}" onclick="toggleRow(${r.row})">
      <td class="tc" onclick="event.stopPropagation()"><input type="checkbox" class="row-check" ${sel?'checked':''} onchange="toggleSel(${r.row},this)"></td>
      <td class="tc"><span class="badge-row">${r.row}</span></td>
      <td class="td-ts">${esc(ts)}</td>
      <td><span class="cell-preview cp-input">${esc(ip)}</span></td>
      <td><span class="cell-preview ${cp?'cp-cot':'cp-none'}">${cp?esc(cp):'—'}</span></td>
      <td><span class="cell-preview cp-answer">${esc(ap)}</span></td>
      <td class="tc" onclick="event.stopPropagation()">
        <div class="row-actions">
          <button class="icon-btn" id="btn-${r.row}" onclick="toggleRow(${r.row})" title="Expand/collapse">+</button>
          <button class="icon-btn" onclick="copyCell('row',${r.row})" title="Copy row as JSON">📋</button>
        </div>
      </td>
    </tr>
    <tr class="detail-row" id="detail-${r.row}" style="display:none"><td colspan="7">${detailHTML(r)}</td></tr>`;
  });

  html += `</tbody></table></div>`;
  c.innerHTML = html;
}

function detailHTML(r) {
  const params = r.params||{}, usage = r.usage||{}, rid = r.row;
  const pf = [
    ['model', r.model||params.model],
    ['temperature', r.temperature??params.temperature],
    ['max_tokens', r.max_tokens??params.max_tokens],
    ['top_p', r.top_p??params.top_p],
    ['presence_penalty', r.presence_penalty??params.presence_penalty],
    ['frequency_penalty', r.frequency_penalty??params.frequency_penalty],
    ['seed', r.seed??params.seed],
    ['stream', r.stream??params.stream],
  ].filter(([,v]) => v!==undefined && v!==null && v!=='');
  const uf = [
    ['prompt_tokens', r.prompt_tokens??usage.prompt_tokens],
    ['completion_tokens', r.completion_tokens??usage.completion_tokens],
    ['total_tokens', r.total_tokens??usage.total_tokens],
  ].filter(([,v]) => v!==undefined && v!==null && v!=='');

  return `<div>
    <div class="detail-grid">
      <div class="detail-col">
        <div class="detail-col-hdr">
          <div class="col-label lbl-i">Input</div>
          <button class="copy-btn" id="cb-input-${rid}" onclick="copyCell('input',${rid})">copy</button>
        </div>
        ${renderInputDetail(r.input)}
      </div>
      <div class="detail-col">
        <div class="detail-col-hdr">
          <div class="col-label lbl-c">Chain of Thought</div>
          ${r.cot?`<button class="copy-btn" id="cb-cot-${rid}" onclick="copyCell('cot',${rid})">copy</button>`:''}
        </div>
        ${r.cot?`<div class="detail-content dc-c">${esc(r.cot)}</div>`:'<div class="no-cot">No chain of thought recorded</div>'}
      </div>
      <div class="detail-col">
        <div class="detail-col-hdr">
          <div class="col-label lbl-a">Answer</div>
          <button class="copy-btn" id="cb-answer-${rid}" onclick="copyCell('answer',${rid})">copy</button>
        </div>
        <div class="detail-content dc-a">${esc(r.answer||'')}</div>
      </div>
    </div>
    <div class="meta-grid">
      <div class="meta-sec">
        <div class="meta-title">Request Params</div>
        ${pf.map(([k,v])=>`<div class="meta-row"><span class="meta-k">${k}</span><span class="meta-v">${esc(String(v))}</span></div>`).join('')||'<div class="no-cot">—</div>'}
      </div>
      <div class="meta-sec">
        <div class="meta-title">Token Usage</div>
        ${uf.map(([k,v])=>`<div class="meta-row"><span class="meta-k">${k}</span><span class="meta-v">${esc(String(v))}</span></div>`).join('')||'<div class="no-cot">—</div>'}
      </div>
    </div>
  </div>`;
}

function copyCell(field, rowId) {
  const r = allRecords.find(x => x.row === rowId);
  if (!r) return;
  let val = field==='row' ? JSON.stringify(r, null, 2) : (r[field]||'');
  if (field==='input') {
    try { const m = JSON.parse(val); if (Array.isArray(m)) val = m.map(x=>`[${x.role}]\n${x.content}`).join('\n\n'); } catch {}
  }
  navigator.clipboard.writeText(val).then(() => {
    if (field !== 'row') {
      const btn = document.getElementById(`cb-${field}-${rowId}`);
      if (btn) { btn.textContent='✓'; btn.classList.add('ok'); setTimeout(()=>{btn.textContent='copy';btn.classList.remove('ok');},1800); }
    }
    toast(field==='row'?'Row copied as JSON':`${field} copied`, field==='row'?'':'g');
  });
}

function copySelectedJSON() {
  const rows = allRecords.filter(r => selectedRows.has(r.row));
  if (!rows.length) { toast('Nothing selected'); return; }
  navigator.clipboard.writeText(rows.map(r=>JSON.stringify(r)).join('\n')).then(()=>toast(`${rows.length} row(s) copied as JSONL`,'g'));
}

function exportRows() {
  const rows = selectedRows.size>0 ? allRecords.filter(r=>selectedRows.has(r.row)) : getFiltered();
  if (!rows.length) { toast('Nothing to export'); return; }
  const blob = new Blob([rows.map(r=>JSON.stringify(r)).join('\n')], {type:'application/jsonl'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download='export.jsonl'; a.click();
  toast(`Exported ${rows.length} row(s)`,'g');
}

function toggleSel(rowId, cb) {
  if (cb.checked) selectedRows.add(rowId); else selectedRows.delete(rowId);
  document.getElementById(`row-${rowId}`)?.classList.toggle('selected', cb.checked);
  updateBulkBar();
}

function toggleSelectAll(master) {
  getFiltered().forEach(r => {
    if (master.checked) selectedRows.add(r.row); else selectedRows.delete(r.row);
    const el = document.getElementById(`row-${r.row}`);
    const cb = el?.querySelector('.row-check');
    el?.classList.toggle('selected', master.checked);
    if (cb) cb.checked = master.checked;
  });
  updateBulkBar();
}

function selectAllVisible() {
  getFiltered().forEach(r => {
    selectedRows.add(r.row);
    const el = document.getElementById(`row-${r.row}`);
    const cb = el?.querySelector('.row-check');
    el?.classList.add('selected');
    if (cb) cb.checked = true;
  });
  updateBulkBar();
}

function clearSel() {
  selectedRows.clear();
  document.querySelectorAll('.row-check').forEach(c=>c.checked=false);
  document.querySelectorAll('.data-row').forEach(e=>e.classList.remove('selected'));
  updateBulkBar();
}

function updateBulkBar() {
  const n = selectedRows.size;
  document.getElementById('statSel').textContent = n;
  const bar = document.getElementById('bulkBar');
  bar.style.display = n>0 ? 'flex' : 'none';
  if (n>0) document.getElementById('bulkCount').textContent = `${n} selected`;
}

function toggleRow(row) {
  const det = document.getElementById(`detail-${row}`);
  const rowEl = document.getElementById(`row-${row}`);
  const btn = document.getElementById(`btn-${row}`);
  if (!det) return;
  const open = det.style.display !== 'none';
  det.style.display = open ? 'none' : 'table-row';
  rowEl.classList.toggle('expanded', !open);
  if (btn) { btn.textContent = open?'+':'−'; btn.classList.toggle('on', !open); }
}

function renderInputDetail(raw) {
  try {
    const msgs = JSON.parse(raw);
    if (Array.isArray(msgs)) return msgs.map(m=>`<div class="msg-block"><div class="msg-role r-${m.role}">${m.role}</div><div class="msg-body detail-content dc-i">${esc(m.content||'')}</div></div>`).join('');
  } catch {}
  return `<div class="detail-content dc-i">${esc(raw||'')}</div>`;
}

function previewInput(raw) {
  try {
    const msgs = JSON.parse(raw);
    if (Array.isArray(msgs)) { const u = msgs.find(m=>m.role==='user'); const c = u?u.content:(msgs[0]?.content||''); return c.slice(0,88)+(c.length>88?'…':''); }
  } catch {}
  return (raw||'').slice(0,88)+((raw||'').length>88?'…':'');
}

function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function toast(msg, color) {
  const t = document.createElement('div');
  t.className = 'toast'+(color==='g'?' g':'');
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(), 2200);
}

document.addEventListener('keydown', e => {
  if (e.key==='Escape') clearSel();
  if ((e.ctrlKey||e.metaKey) && e.key==='a' && document.activeElement.tagName!=='INPUT') { e.preventDefault(); selectAllVisible(); }
  if ((e.ctrlKey||e.metaKey) && e.key==='c' && selectedRows.size>0 && document.activeElement.tagName!=='INPUT') { e.preventDefault(); copySelectedJSON(); }
});

init();
// Auto-refresh the current file every 10 seconds to pick up new records.
setInterval(()=>{ const f=document.getElementById('fileSelect').value; if(f) loadFile(); }, 10000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=VIEWER_PORT, debug=False)
