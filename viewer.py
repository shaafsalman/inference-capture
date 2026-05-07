"""
viewer.py  —  inference-capture dataset viewer
"""

import os, json, glob
from flask import Flask, jsonify, Response, request

DATA_DIR   = "data"
VIEWER_PORT = 8081

app = Flask(__name__, static_folder=None)

@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")

@app.route("/api/files")
def list_files():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.jsonl")))
    return jsonify([os.path.basename(f) for f in files])

@app.route("/api/records/<filename>")
def get_records(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return jsonify([])
    since = int(request.args.get("since", 0))
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if i <= since:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                r["_row"] = i
                records.append(r)
            except json.JSONDecodeError:
                pass
    return jsonify(records)

@app.route("/api/delete_rows", methods=["POST"])
def delete_rows():
    data     = request.json
    filename = data.get("filename", "")
    row_nums = set(data.get("rows", []))
    if not filename or not row_nums:
        return jsonify({"status": "error", "message": "missing filename or rows"}), 400
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"status": "error", "message": "file not found"}), 404
    kept = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if i in row_nums:
                continue
            line = line.strip()
            if line:
                kept.append(line)
    with open(path, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
    return jsonify({"status": "ok", "deleted": len(row_nums), "remaining": len(kept)})

@app.route("/api/save_processed", methods=["POST"])
def save_processed():
    data     = request.json
    filename = data.get("filename", "processed_dataset.jsonl")
    records  = data.get("records", [])
    if not filename.endswith(".jsonl"):
        filename += ".jsonl"
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return jsonify({"status": "ok", "path": path, "count": len(records)})


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>inference-capture viewer</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f0f0f4;--surf:#e8e8ec;--surf2:#dcdce2;--surf3:#d0d0d8;
  --bdr:#c4c4cc;--bdr2:#adadb8;
  --acc:#5b4fd4;--acc-l:#eceaff;--acc-d:#4438b0;
  --grn:#1a7a4a;--grn-l:#dff5eb;
  --yel:#7a5400;--yel-l:#fef3d0;
  --blu:#1a5fa8;--blu-l:#deeeff;
  --red:#b83232;--red-l:#ffecec;
  --txt:#18181c;--txt2:#36363c;--txt3:#5e5e68;--txt4:#96969e;
  --mono:'JetBrains Mono',monospace;--sans:'Inter',sans-serif;
  --fs:13px;--r:8px;
}
body{background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:var(--fs);height:100vh;display:flex;flex-direction:column;overflow:hidden}

.topbar{height:52px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 18px;background:var(--surf);border-bottom:1.5px solid var(--bdr2);box-shadow:0 1px 6px rgba(0,0,0,.07)}
.logo{font-family:var(--mono);font-size:14px;font-weight:700;letter-spacing:-.04em;white-space:nowrap}
.logo span{color:var(--acc)}
.vr{width:1px;height:20px;background:var(--bdr2);flex-shrink:0}
.topbar-r{margin-left:auto;display:flex;align-items:center;gap:6px}

select,input[type=text]{background:#fff;border:1px solid var(--bdr2);color:var(--txt);font-family:var(--mono);font-size:12px;padding:5px 9px;border-radius:var(--r);outline:none;transition:border-color .15s,box-shadow .15s}
select:focus,input[type=text]:focus{border-color:var(--acc);box-shadow:0 0 0 3px rgba(91,79,212,.13)}
#fileSelect{min-width:220px}

.btn{background:#fff;border:1px solid var(--bdr2);color:var(--txt2);font-family:var(--mono);font-size:11px;font-weight:600;padding:5px 13px;border-radius:var(--r);cursor:pointer;transition:all .15s;display:flex;align-items:center;gap:4px;white-space:nowrap}
.btn:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}
.btn.g{color:var(--grn);border-color:var(--grn);background:var(--grn-l)}
.btn.g:hover{opacity:.85}
.btn.danger{color:var(--red);border-color:var(--red);background:var(--red-l)}
.btn.danger:hover{opacity:.85}
.fsc{display:flex;align-items:center;gap:3px}
.fsb{width:26px;height:26px;border-radius:6px;display:flex;align-items:center;justify-content:center;background:#fff;border:1px solid var(--bdr2);color:var(--txt2);cursor:pointer;font-size:14px;font-weight:700;transition:all .15s}
.fsb:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}
.fsl{font-size:11px;color:var(--txt3);font-family:var(--mono);min-width:30px;text-align:center}

.sbar{height:40px;flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 18px;background:var(--surf2);border-bottom:1px solid var(--bdr);font-size:12px;overflow-x:auto}
.pill{display:flex;align-items:center;gap:4px;background:#fff;border:1px solid var(--bdr);border-radius:20px;padding:2px 9px;font-size:11px;font-family:var(--mono);white-space:nowrap;flex-shrink:0}
.pill b{color:var(--acc)}
.pill.live b{color:var(--grn);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.fw{margin-left:auto;display:flex;align-items:center;gap:5px;flex-shrink:0}
#srch{width:230px}
.chip{background:#fff;border:1px solid var(--bdr2);border-radius:20px;padding:3px 10px;font-size:11px;font-family:var(--mono);color:var(--txt3);cursor:pointer;transition:all .15s;white-space:nowrap}
.chip:hover,.chip.on{background:var(--acc-l);border-color:var(--acc);color:var(--acc);font-weight:600}

.tw{flex:1;overflow:auto;scrollbar-width:thin;scrollbar-color:var(--bdr2) transparent}
table{width:100%;border-collapse:collapse;table-layout:fixed}
colgroup col.cs{width:34px}
colgroup col.cn{width:48px}
colgroup col.ct{width:136px}
colgroup col.ci{width:23%}
colgroup col.cc{width:26%}
colgroup col.ca{width:20%}
colgroup col.cb{width:72px}

thead{position:sticky;top:0;z-index:20}
thead tr{background:var(--surf)}
th{padding:0 10px;height:38px;text-align:left;font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--txt3);border-bottom:2px solid var(--bdr2);border-right:1px solid var(--bdr);white-space:nowrap;user-select:none}
th:last-child{border-right:none}
th.tc{text-align:center}

.gh-row{}
.gh-cell{padding:0;border-right:none!important}
.gh-main{display:flex;align-items:center;border-left:4px solid;height:44px}
.gh-collapse-zone{display:flex;align-items:center;gap:9px;padding:0 14px;flex:1;min-width:0;cursor:pointer;user-select:none;height:100%;transition:filter .1s}
.gh-collapse-zone:hover{filter:brightness(.96)}
.gh-actions{display:flex;align-items:center;gap:6px;padding-right:14px;flex-shrink:0}

.gh-chev{font-size:10px;transition:transform .15s;flex-shrink:0;color:var(--txt3)}
.gh-chev.open{transform:rotate(90deg)}
.gh-badge{font-size:10px;font-weight:700;padding:2px 9px;border-radius:20px;border:1px solid;white-space:nowrap;flex-shrink:0;background:#fff}
.gh-name{font-family:var(--mono);font-size:12px;font-weight:600;max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gh-name.unnamed{opacity:.45;font-style:italic;font-weight:400}
.gh-edit-btn{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 8px;border-radius:5px;border:1px dashed;background:rgba(255,255,255,.5);cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .12s;text-transform:uppercase;letter-spacing:.04em}
.gh-edit-btn:hover{background:#fff}
.gh-del-btn{font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 8px;border-radius:5px;border:1px solid rgba(184,50,50,.4);background:rgba(255,236,236,.5);color:var(--red);cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .12s;text-transform:uppercase;letter-spacing:.04em}
.gh-del-btn:hover{background:var(--red-l);border-color:var(--red)}
.gh-prompt-btn{font-family:var(--mono);font-size:10px;background:rgba(255,255,255,.45);border:1px solid rgba(0,0,0,.1);border-radius:4px;padding:2px 8px;cursor:pointer;white-space:nowrap;flex-shrink:0;margin-left:auto;transition:all .12s}
.gh-prompt-btn:hover{background:#fff}
.gh-panel{padding:12px 18px 14px 52px;border-top:1px solid rgba(0,0,0,.07);font-family:var(--mono);font-size:11px;color:var(--txt3);white-space:pre-wrap;line-height:1.75;max-height:220px;overflow-y:auto;border-left:4px solid}

.dr{border-bottom:1px solid var(--bdr);cursor:pointer;transition:background .07s}
.dr:hover{background:rgba(91,79,212,.04)}
.dr.exp{background:var(--acc-l)!important}
.dr.sel{background:rgba(91,79,212,.08)!important;box-shadow:inset 2px 0 0 var(--acc)}
.dr.hid,.det-row.hid{display:none}
td{padding:0 10px;height:44px;vertical-align:middle;font-family:var(--mono);color:var(--txt2);border-right:1px solid var(--bdr);overflow:hidden}
td:last-child{border-right:none}
td.tc{text-align:center}
td.ts{color:var(--txt4);font-size:11px}
.prev{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;display:block}
.pi{color:var(--yel);font-weight:500}
.pa{color:var(--grn);font-weight:500}
.pc{color:var(--txt3);font-style:italic}
.pn{color:var(--txt4);font-style:italic}
.badge{display:inline-flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:10px;font-weight:700;padding:2px 6px;border-radius:5px;min-width:26px;background:var(--surf3);color:var(--txt3);border:1px solid var(--bdr2)}
.chk{width:14px;height:14px;cursor:pointer;accent-color:var(--acc)}
.acts{display:flex;align-items:center;justify-content:center;gap:3px}
.ib{width:25px;height:25px;border-radius:5px;display:flex;align-items:center;justify-content:center;background:#fff;border:1px solid var(--bdr2);color:var(--txt3);cursor:pointer;font-size:12px;transition:all .12s}
.ib:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}
.ib.on{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}

.det-row td{height:auto;padding:0;border-right:none;background:#fff}
.det-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:var(--bdr2);border-top:3px solid var(--acc)}
.det-col{background:#fff;padding:12px 16px}
.det-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}
.lbl{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;display:flex;align-items:center;gap:7px;flex:1}
.lbl::after{content:'';flex:1;height:1px;background:var(--bdr)}
.li{color:var(--yel)}.lc{color:var(--txt3)}.la{color:var(--grn)}
.cpb{font-family:var(--mono);font-size:9px;font-weight:700;padding:2px 7px;border-radius:4px;border:1px solid var(--bdr2);background:var(--surf2);color:var(--txt3);cursor:pointer;transition:all .12s;text-transform:uppercase}
.cpb:hover{background:var(--acc-l);border-color:var(--acc);color:var(--acc)}
.cpb.ok{background:var(--grn-l);border-color:var(--grn);color:var(--grn)}
.dc{font-family:var(--mono);line-height:1.8;font-size:var(--fs);white-space:pre-wrap;word-break:break-word;max-height:340px;overflow-y:auto;scrollbar-width:thin}
.di{color:var(--txt)}.dcc{color:var(--txt3);font-style:italic}.da{color:var(--grn);font-weight:500}
.mb{margin-bottom:10px}
.mr{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:3px;padding:2px 6px;border-radius:4px;display:inline-block}
.r-s{background:var(--blu-l);color:var(--blu)}.r-u{background:var(--yel-l);color:var(--yel)}.r-a{background:var(--acc-l);color:var(--acc)}
.mb-body{color:var(--txt);line-height:1.75;font-family:var(--mono);font-size:var(--fs)}
.no-c{color:var(--txt4);font-style:italic;font-size:11px}
.meta-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--bdr);border-top:1px solid var(--bdr2)}
.ms{background:var(--surf);padding:8px 16px}
.mt{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--txt3);margin-bottom:5px}
.mk{font-family:var(--mono);font-size:11px;color:var(--txt3);min-width:150px;flex-shrink:0}
.mv{font-family:var(--mono);font-size:11px;color:var(--txt);font-weight:600}
.mr2{display:flex;align-items:baseline;gap:8px;padding:2px 0;border-bottom:1px solid var(--bdr)}
.mr2:last-child{border-bottom:none}

.overlay{position:fixed;inset:0;background:rgba(0,0,0,.48);z-index:300;display:flex;align-items:center;justify-content:center;animation:fi .15s ease}
@keyframes fi{from{opacity:0}to{opacity:1}}
.modal{background:#fff;border-radius:12px;padding:26px 28px;width:460px;box-shadow:0 20px 60px rgba(0,0,0,.22);animation:ms .15s ease}
@keyframes ms{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.modal h3{font-size:15px;font-weight:700;margin-bottom:5px}
.modal p{font-size:12px;color:var(--txt3);margin-bottom:16px;font-family:var(--mono);line-height:1.7}
.modal input{width:100%;margin-bottom:14px;font-size:13px}
.modal-btns{display:flex;gap:7px;justify-content:flex-end}
.name-preview{font-family:var(--mono);font-size:11px;color:var(--txt3);margin-bottom:14px;padding:8px 10px;background:var(--surf2);border-radius:6px;line-height:1.6;max-height:80px;overflow:hidden;text-overflow:ellipsis}

.del-warn{background:var(--red-l);border:1px solid var(--red);border-radius:6px;padding:10px 12px;font-family:var(--mono);font-size:11px;color:var(--red);margin-bottom:14px;line-height:1.6}

.bulk{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#18181e;color:#fff;border-radius:12px;padding:9px 18px;display:flex;align-items:center;gap:9px;box-shadow:0 8px 32px rgba(0,0,0,.28);z-index:100;font-size:12px;font-family:var(--mono);animation:su .15s ease}
@keyframes su{from{transform:translateX(-50%) translateY(10px);opacity:0}to{transform:translateX(-50%) translateY(0);opacity:1}}
.bb{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:#fff;font-family:var(--mono);font-size:11px;font-weight:600;padding:4px 11px;border-radius:6px;cursor:pointer;transition:background .12s;white-space:nowrap}
.bb:hover{background:rgba(255,255,255,.2)}
.bb.g{background:rgba(26,122,74,.5);border-color:rgba(26,122,74,.7)}
.bb.r{background:rgba(184,50,50,.4);border-color:rgba(184,50,50,.6)}

.toast{position:fixed;bottom:72px;right:20px;background:#18181e;color:#fff;border-radius:8px;padding:9px 14px;font-size:12px;font-family:var(--mono);box-shadow:0 4px 16px rgba(0,0,0,.2);z-index:500;animation:ti .15s ease;pointer-events:none}
.toast.g{background:var(--grn)}
.toast.r{background:var(--red)}
@keyframes ti{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;gap:10px;color:var(--txt3);padding:80px}
.empty-ico{font-size:40px}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">inference<span>capture</span></div>
  <div class="vr"></div>
  <select id="fileSelect" onchange="onFileChange()"><option value="">— select file —</option></select>
  <div class="topbar-r">
    <div class="fsc">
      <button class="fsb" onclick="chFS(-1)">−</button>
      <span class="fsl" id="fsl">13px</span>
      <button class="fsb" onclick="chFS(1)">+</button>
    </div>
    <div class="vr"></div>
    <button class="btn" onclick="collapseAll()">⊟ collapse</button>
    <button class="btn" onclick="expandAll()">⊞ expand</button>
    <button class="btn g" onclick="openSaveModal()">💾 save processed</button>
    <button class="btn" onclick="exportVisible()">⬇ export</button>
  </div>
</div>

<div class="sbar" id="sbar" style="display:none">
  <div class="pill">rows <b id="st-rows">0</b></div>
  <div class="pill">groups <b id="st-groups">0</b></div>
  <div class="pill">named <b id="st-named">0</b></div>
  <div class="pill">selected <b id="st-sel">0</b></div>
  <div class="pill live">live <b id="st-live">●</b></div>
  <div class="fw">
    <span class="chip on" id="c-all" onclick="setF('all')">all</span>
    <span class="chip" id="c-cot" onclick="setF('cot')">has cot</span>
    <span class="chip" id="c-no" onclick="setF('no')">no cot</span>
    <input type="text" id="srch" placeholder="search…" oninput="applyFilter()">
  </div>
</div>

<div id="main" style="flex:1;display:flex;flex-direction:column;overflow:hidden">
  <div class="empty"><div class="empty-ico">📂</div>select a file to begin</div>
</div>

<div class="bulk" id="bulk" style="display:none">
  <span id="bulk-n">0 selected</span>
  <button class="bb g" onclick="copySelJSON()">📋 copy JSONL</button>
  <button class="bb g" onclick="exportSel()">⬇ export</button>
  <button class="bb" onclick="selAll()">select all</button>
  <button class="bb r" onclick="clearSel()">✕ clear</button>
</div>

<!-- NAME MODAL -->
<div class="overlay" id="nameOverlay" style="display:none" onclick="closeNameModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3>✏️ Name this group</h3>
    <div class="name-preview" id="namePreview"></div>
    <input type="text" id="nameInput" placeholder="e.g. MedBullets, MedEC, HeadQA…">
    <div class="modal-btns">
      <button class="btn" onclick="clearGroupName()">Clear name</button>
      <button class="btn" onclick="closeNameModal()">Cancel</button>
      <button class="btn g" onclick="saveGroupName()">Save</button>
    </div>
  </div>
</div>

<!-- DELETE GROUP MODAL -->
<div class="overlay" id="deleteOverlay" style="display:none" onclick="closeDeleteModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3>🗑️ Delete group</h3>
    <div class="name-preview" id="deletePreview"></div>
    <div class="del-warn" id="deleteWarn"></div>
    <p>This permanently removes these rows from <b id="deleteFilename"></b> on disk. This cannot be undone.</p>
    <div class="modal-btns">
      <button class="btn" onclick="closeDeleteModal()">Cancel</button>
      <button class="btn danger" onclick="confirmDeleteGroup()">🗑️ Delete permanently</button>
    </div>
  </div>
</div>

<!-- SAVE MODAL -->
<div class="overlay" id="saveOverlay" style="display:none" onclick="closeSaveModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3>💾 Save processed dataset</h3>
    <p>All records saved with a <b>category</b> field from your group names.<br>
    Unnamed groups use their user-message prefix as the category.<br>
    Written to <b>data/</b> on the server.</p>
    <input type="text" id="saveFile" value="processed_dataset.jsonl">
    <div class="modal-btns">
      <button class="btn" onclick="closeSaveModal()">Cancel</button>
      <button class="btn g" onclick="doSave()">Save to server</button>
    </div>
  </div>
</div>

<script>
const COLORS = [
  {bg:'#eceaff',bdr:'#5b4fd4',txt:'#4438b0'},
  {bg:'#dff5eb',bdr:'#1a7a4a',txt:'#1a7a4a'},
  {bg:'#fff0e0',bdr:'#8a4500',txt:'#8a4500'},
  {bg:'#deeeff',bdr:'#1a5fa8',txt:'#1a5fa8'},
  {bg:'#f5e0ff',bdr:'#6a1a9a',txt:'#6a1a9a'},
  {bg:'#e0f5f5',bdr:'#1a6a6a',txt:'#1a6a6a'},
  {bg:'#ffecec',bdr:'#b83232',txt:'#b83232'},
  {bg:'#fef3d0',bdr:'#7a5400',txt:'#7a5400'},
];

let currentFile = '';
let allRecords  = [];
let lastRow     = 0;
let groupKeys   = new Map();
let gidSeq      = 0;

let collapsed   = new Set();
let sysOpen     = new Set();
let selected    = new Set();
let catNames    = {};

let filterMode  = 'all';
let searchQ     = '';
let fontSize    = 13;
let pollTimer   = null;

let editingKey  = '';
let deletingKey = '';

function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }
function toast(msg,cls){
  const t=document.createElement('div');
  t.className='toast'+(cls?' '+cls:'');t.textContent=msg;
  document.body.appendChild(t);setTimeout(()=>t.remove(),2400);
}

function getGroupKey(r){
  try{
    const msgs=JSON.parse(r.input);
    if(Array.isArray(msgs)){
      const u=msgs.find(m=>m.role==='user');
      if(u?.content){ return u.content.split('\n')[0].trim().slice(0,120); }
    }
  }catch{}
  return '__ungrouped__';
}

function catKey(){ return 'ic_cat_'+currentFile; }
function loadCats(){ try{ catNames=JSON.parse(localStorage.getItem(catKey())||'{}'); }catch{ catNames={}; } }
function persistCats(){ localStorage.setItem(catKey(),JSON.stringify(catNames)); refreshStats(); }

function refreshStats(){
  document.getElementById('st-rows').textContent   = allRecords.length;
  document.getElementById('st-groups').textContent = groupKeys.size;
  document.getElementById('st-named').textContent  = Object.keys(catNames).length;
  document.getElementById('st-sel').textContent    = selected.size;
}

function chFS(d){
  fontSize=Math.min(20,Math.max(10,fontSize+d));
  document.documentElement.style.setProperty('--fs',fontSize+'px');
  document.getElementById('fsl').textContent=fontSize+'px';
}
function setF(f){
  filterMode=f;
  ['all','cot','no'].forEach(x=>{
    document.getElementById('c-'+x).classList.toggle('on',x===f);
  });
  applyFilter();
}
function applyFilter(){
  searchQ=document.getElementById('srch').value.toLowerCase().trim();
  allRecords.forEach(r=>{
    const rowEl =document.getElementById('r-'+r._row);
    const detEl =document.getElementById('d-'+r._row);
    if(!rowEl) return;
    let show=true;
    if(filterMode==='cot'  && !r.cot) show=false;
    if(filterMode==='no'   &&  r.cot) show=false;
    if(searchQ && show){
      const hay=(r.input||'')+(r.cot||'')+(r.answer||'');
      if(!hay.toLowerCase().includes(searchQ)) show=false;
    }
    const gid=rowEl.getAttribute('data-gid');
    const inColl=collapsed.has(gid);
    rowEl.classList.toggle('hid',!show||inColl);
    if(detEl) detEl.classList.toggle('hid',!show||inColl||detEl.style.display==='none');
  });
}

function onFileChange(){
  const f=document.getElementById('fileSelect').value;
  if(f===currentFile) return;
  currentFile=f; lastRow=0; allRecords=[]; groupKeys.clear(); gidSeq=0;
  collapsed.clear(); sysOpen.clear(); selected.clear(); catNames={};
  clearInterval(pollTimer);
  if(!f){
    document.getElementById('sbar').style.display='none';
    document.getElementById('main').innerHTML='<div class="empty"><div class="empty-ico">📂</div>select a file to begin</div>';
    return;
  }
  document.getElementById('sbar').style.display='flex';
  loadCats();
  document.getElementById('main').innerHTML='<div class="tw"><table><colgroup><col class="cs"><col class="cn"><col class="ct"><col class="ci"><col class="cc"><col class="ca"><col class="cb"></colgroup><thead><tr><th class="tc"><input type="checkbox" class="chk" id="chkAll" onchange="toggleAll(this)"></th><th class="tc">#</th><th>Timestamp</th><th>Input</th><th>Chain of Thought</th><th>Answer</th><th class="tc">Actions</th></tr></thead><tbody id="tbody"></tbody></table></div>';
  fetchNew();
  pollTimer=setInterval(fetchNew, 8000);
}

async function fetchNew(){
  if(!currentFile) return;
  const url=`/api/records/${encodeURIComponent(currentFile)}?since=${lastRow}`;
  let data;
  try{ data=await fetch(url).then(r=>r.json()); }catch{ return; }
  if(!data.length) return;
  data.forEach(r=>{ allRecords.push(r); if(r._row>lastRow) lastRow=r._row; appendRow(r); });
  refreshStats();
}

async function initFiles(){
  const sel=document.getElementById('fileSelect'), cur=sel.value;
  const files=await fetch('/api/files').then(r=>r.json());
  sel.innerHTML='<option value="">— select file —</option>';
  files.forEach(f=>{
    const o=document.createElement('option');
    o.value=f;o.textContent=f;if(f===cur)o.selected=true;sel.appendChild(o);
  });
}

function appendRow(r){
  const tbody=document.getElementById('tbody');
  if(!tbody) return;
  const key=getGroupKey(r);

  if(!groupKeys.has(key)){
    const gid='g'+(gidSeq++);
    const col=COLORS[(gidSeq-1)%COLORS.length];
    groupKeys.set(key,{gid,col,count:0});
    insertGroupHeader(tbody,key,gid,col);
  }
  const grp=groupKeys.get(key);
  grp.count++;
  updateGroupCount(grp.gid,grp.count);

  const hidden=collapsed.has(grp.gid);

  const tr=document.createElement('tr');
  tr.className='dr'+(hidden?' hid':'');
  tr.id='r-'+r._row;
  tr.setAttribute('data-gid',grp.gid);
  tr.style.borderLeft='3px solid '+grp.col.bdr;
  tr.onclick=()=>toggleDet(r._row);

  const ip=previewInput(r.input);
  const cp=r.cot?r.cot.slice(0,80).replace(/\n/g,' ')+(r.cot.length>80?'…':''):'';
  const ap=(r.answer||'').slice(0,80).replace(/\n/g,' ')+((r.answer||'').length>80?'…':'');
  const ts=(r.timestamp||'').replace('T',' ').slice(0,19);
  const sel=selected.has(r._row);

  tr.innerHTML=`
    <td class="tc" onclick="event.stopPropagation()"><input type="checkbox" class="chk" ${sel?'checked':''} onchange="toggleSel(${r._row},this)"></td>
    <td class="tc"><span class="badge">${r._row}</span></td>
    <td class="ts">${esc(ts)}</td>
    <td><span class="prev pi">${esc(ip)}</span></td>
    <td><span class="prev ${cp?'pc':'pn'}">${cp?esc(cp):'—'}</span></td>
    <td><span class="prev pa">${esc(ap)}</span></td>
    <td class="tc" onclick="event.stopPropagation()">
      <div class="acts">
        <button class="ib" id="eb-${r._row}" onclick="toggleDet(${r._row})">+</button>
        <button class="ib" onclick="copyRow(${r._row})">📋</button>
      </div>
    </td>`;

  const nextGH=findNextGroupHeader(tbody,grp.gid);
  if(nextGH) tbody.insertBefore(tr,nextGH);
  else tbody.appendChild(tr);

  const det=document.createElement('tr');
  det.className='det-row'+(hidden?' hid':'');
  det.id='d-'+r._row;
  det.style.display='none';
  const dtd=document.createElement('td');
  dtd.colSpan=7;
  dtd.innerHTML=detHTML(r,key);
  det.appendChild(dtd);
  if(nextGH) tbody.insertBefore(det,nextGH);
  else tbody.appendChild(det);

  applyFilter();
}

function findNextGroupHeader(tbody,gid){
  const headers=[...tbody.querySelectorAll('tr[data-is-gh]')];
  let found=false;
  for(const h of headers){
    if(found) return h;
    if(h.getAttribute('data-gh-gid')===gid) found=true;
  }
  return null;
}

function insertGroupHeader(tbody,key,gid,col){
  const tr=document.createElement('tr');
  tr.setAttribute('data-is-gh','1');
  tr.setAttribute('data-gh-gid',gid);
  tr.className='gh-row';

  const td=document.createElement('td');
  td.colSpan=7;
  td.className='gh-cell';
  td.innerHTML=buildGHHTML(key,gid,col,0);
  tr.appendChild(td);
  tbody.appendChild(tr);
}

function buildGHHTML(key,gid,col,count){
  const catName=catNames[key]||'';
  const isOpen=sysOpen.has(gid);
  const isColl=collapsed.has(gid);
  const panelText=buildPanelText(key);
  const safeKey=encodeURIComponent(key);
  return `
    <div class="gh-main" style="background:${col.bg};border-left-color:${col.bdr}">
      <div class="gh-collapse-zone" onclick="toggleGroup('${gid}')">
        <span class="gh-chev${isColl?'':' open'}" id="chev-${gid}">▶</span>
        <span class="gh-badge" style="border-color:${col.bdr};color:${col.txt}" id="cnt-${gid}">${count} rows</span>
        <span class="gh-name${catName?'':' unnamed'}" style="color:${col.txt}" id="gname-${gid}">${catName?esc(catName):'click ✏️ to name this group'}</span>
      </div>
      <div class="gh-actions">
        <button class="gh-edit-btn" style="color:${col.txt};border-color:${col.bdr}"
          data-gid="${gid}" data-key="${safeKey}"
          onclick="handleNameBtn(this)">✏️ name</button>
        <button class="gh-del-btn"
          data-gid="${gid}" data-key="${safeKey}"
          onclick="handleDeleteBtn(this)">🗑️ delete</button>
        <button class="gh-prompt-btn" style="color:${col.txt}" id="pbtn-${gid}"
          onclick="toggleSys('${gid}','${col.bdr}')">${isOpen?'▲ hide prompt':'▼ show prompt'}</button>
      </div>
    </div>
    <div class="gh-panel" id="panel-${gid}" style="display:${isOpen?'block':'none'};background:${col.bg};border-left-color:${col.bdr}">${esc(panelText)}</div>`;
}

function buildPanelText(key){
  return 'User message starts with:\n' + key + (key.length>=120?'\n[truncated — click a row to see full input]':'');
}

function updateGroupCount(gid,count){
  const el=document.getElementById('cnt-'+gid);
  if(el) el.textContent=count+' rows';
}

function refreshGroupHeader(key){
  const grp=groupKeys.get(key);
  if(!grp) return;
  const tbody=document.getElementById('tbody');
  if(!tbody) return;
  const ghRow=tbody.querySelector(`tr[data-gh-gid="${grp.gid}"]`);
  if(!ghRow) return;
  ghRow.querySelector('td').innerHTML=buildGHHTML(key,grp.gid,grp.col,grp.count);
}

function toggleGroup(gid){
  const tbody=document.getElementById('tbody');
  const rows=[...tbody.querySelectorAll(`[data-gid="${gid}"]`)];
  const chev=document.getElementById('chev-'+gid);
  if(collapsed.has(gid)){
    collapsed.delete(gid);
    rows.forEach(r=>r.classList.remove('hid'));
    if(chev) chev.classList.add('open');
  } else {
    collapsed.add(gid);
    rows.forEach(r=>{
      r.classList.add('hid');
      const rid=r.id?.replace('r-','');
      if(rid&&!isNaN(rid)){ const d=document.getElementById('d-'+rid); if(d) d.style.display='none'; }
    });
    if(chev) chev.classList.remove('open');
  }
}

function toggleSys(gid,bdrColor){
  const panel=document.getElementById('panel-'+gid);
  const btn=document.getElementById('pbtn-'+gid);
  if(!panel) return;
  if(sysOpen.has(gid)){
    sysOpen.delete(gid); panel.style.display='none';
    if(btn) btn.textContent='▼ prompt';
  } else {
    sysOpen.add(gid); panel.style.display='block';
    if(btn) btn.textContent='▲ hide';
  }
}

function collapseAll(){
  groupKeys.forEach((_,key)=>{ const g=groupKeys.get(key); if(g&&!collapsed.has(g.gid)) toggleGroup(g.gid); });
}
function expandAll(){
  groupKeys.forEach((_,key)=>{ const g=groupKeys.get(key); if(g&&collapsed.has(g.gid)) toggleGroup(g.gid); });
}

// ── DELETE GROUP ──────────────────────────────────────────────────────────
function handleDeleteBtn(btn){
  const gid=btn.getAttribute('data-gid');
  const key=decodeURIComponent(btn.getAttribute('data-key'));
  openDeleteModal(gid,key);
}

function openDeleteModal(gid,key){
  deletingKey=key;
  const grp=groupKeys.get(key);
  const count=grp?grp.count:0;
  const catName=catNames[key]||'';
  document.getElementById('deletePreview').textContent=(catName||key).slice(0,160);
  document.getElementById('deleteWarn').textContent=`⚠ This will permanently delete ${count} row${count===1?'':'s'} from the file.`;
  document.getElementById('deleteFilename').textContent=currentFile;
  document.getElementById('deleteOverlay').style.display='flex';
}

function closeDeleteModal(){
  document.getElementById('deleteOverlay').style.display='none';
  deletingKey='';
}

async function confirmDeleteGroup(){
  if(!deletingKey||!currentFile){ closeDeleteModal(); return; }
  const grp=groupKeys.get(deletingKey);
  if(!grp){ closeDeleteModal(); return; }

  const rowNums=allRecords.filter(r=>getGroupKey(r)===deletingKey).map(r=>r._row);

  const res=await fetch('/api/delete_rows',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({filename:currentFile, rows:rowNums})
  });
  const j=await res.json();
  if(j.status!=='ok'){
    toast('Delete failed: '+(j.message||'unknown error'),'r');
    closeDeleteModal();
    return;
  }

  const tbody=document.getElementById('tbody');
  rowNums.forEach(rowNum=>{
    selected.delete(rowNum);
    document.getElementById('r-'+rowNum)?.remove();
    document.getElementById('d-'+rowNum)?.remove();
  });

  const ghRow=tbody.querySelector(`tr[data-gh-gid="${grp.gid}"]`);
  if(ghRow) ghRow.remove();

  allRecords=allRecords.filter(r=>getGroupKey(r)!==deletingKey);
  groupKeys.delete(deletingKey);
  if(catNames[deletingKey]){ delete catNames[deletingKey]; persistCats(); }
  collapsed.delete(grp.gid);
  sysOpen.delete(grp.gid);

  refreshStats();
  updateBulk();
  toast(`🗑️ Deleted ${rowNums.length} rows from ${currentFile}`,'r');
  closeDeleteModal();
}

// ── NAME MODAL ────────────────────────────────────────────────────────────
function handleNameBtn(btn){
  const gid=btn.getAttribute('data-gid');
  const key=decodeURIComponent(btn.getAttribute('data-key'));
  openNameModal(gid,key);
}
function openNameModal(gid,key){
  editingKey=key;
  document.getElementById('nameInput').value=catNames[key]||'';
  document.getElementById('namePreview').textContent=key.slice(0,160)+(key.length>160?'…':'');
  document.getElementById('nameOverlay').style.display='flex';
  setTimeout(()=>document.getElementById('nameInput').focus(),50);
}
function closeNameModal(){ document.getElementById('nameOverlay').style.display='none'; editingKey=''; }
function saveGroupName(){
  const val=document.getElementById('nameInput').value.trim();
  if(val) catNames[editingKey]=val; else delete catNames[editingKey];
  persistCats();
  refreshGroupHeader(editingKey);
  closeNameModal();
  toast(val?`Named: "${val}"`:'Name cleared');
}
function clearGroupName(){ document.getElementById('nameInput').value=''; }

// ── SAVE MODAL ────────────────────────────────────────────────────────────
function openSaveModal(){ document.getElementById('saveOverlay').style.display='flex'; setTimeout(()=>document.getElementById('saveFile').focus(),50); }
function closeSaveModal(){ document.getElementById('saveOverlay').style.display='none'; }
async function doSave(){
  const fn=document.getElementById('saveFile').value.trim()||'processed_dataset.jsonl';
  const records=allRecords.map(r=>{ const key=getGroupKey(r); return {...r,category:catNames[key]||key}; });
  const res=await fetch('/api/save_processed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:fn,records})});
  const j=await res.json();
  closeSaveModal();
  toast(`✓ Saved ${j.count} records → ${j.path}`,'g');
  setTimeout(initFiles,600);
}

// ── ROW DETAIL ────────────────────────────────────────────────────────────
function toggleDet(row){
  const det=document.getElementById('d-'+row);
  const rowEl=document.getElementById('r-'+row);
  const btn=document.getElementById('eb-'+row);
  if(!det) return;
  const open=det.style.display!=='none';
  det.style.display=open?'none':'table-row';
  rowEl?.classList.toggle('exp',!open);
  if(btn){ btn.textContent=open?'+':'−'; btn.classList.toggle('on',!open); }
}

function detHTML(r,key){
  const p=r.params||{},u=r.usage||{},id=r._row;
  const cat=catNames[key]||'(unnamed)';
  const pf=[
    ['category',cat],['model',r.model||p.model],
    ['temperature',r.temperature??p.temperature],['max_tokens',r.max_tokens??p.max_tokens],
    ['top_p',r.top_p??p.top_p],['rep_penalty',p.repetition_penalty],
    ['seed',r.seed??p.seed],['stream',r.stream??p.stream],
  ].filter(([,v])=>v!==undefined&&v!==null&&v!=='');
  const uf=[
    ['prompt_tokens',r.prompt_tokens??u.prompt_tokens],
    ['completion_tokens',r.completion_tokens??u.completion_tokens],
    ['total_tokens',r.total_tokens??u.total_tokens],
  ].filter(([,v])=>v!==undefined&&v!==null&&v!=='');
  return `<div>
    <div class="det-grid">
      <div class="det-col">
        <div class="det-hdr"><div class="lbl li">Input</div><button class="cpb" id="cb-i-${id}" onclick="cpCell('input',${id})">copy</button></div>
        ${renderInput(r.input)}
      </div>
      <div class="det-col">
        <div class="det-hdr"><div class="lbl lc">Chain of Thought</div>${r.cot?`<button class="cpb" id="cb-c-${id}" onclick="cpCell('cot',${id})">copy</button>`:''}</div>
        ${r.cot?`<div class="dc dcc">${esc(r.cot)}</div>`:'<div class="no-c">No chain of thought</div>'}
      </div>
      <div class="det-col">
        <div class="det-hdr"><div class="lbl la">Answer</div><button class="cpb" id="cb-a-${id}" onclick="cpCell('answer',${id})">copy</button></div>
        <div class="dc da">${esc(r.answer||'')}</div>
      </div>
    </div>
    <div class="meta-grid">
      <div class="ms"><div class="mt">Params</div>${pf.map(([k,v])=>`<div class="mr2"><span class="mk">${k}</span><span class="mv">${esc(String(v))}</span></div>`).join('')}</div>
      <div class="ms"><div class="mt">Token Usage</div>${uf.map(([k,v])=>`<div class="mr2"><span class="mk">${k}</span><span class="mv">${esc(String(v))}</span></div>`).join('')}</div>
    </div>
  </div>`;
}

function renderInput(raw){
  try{
    const msgs=JSON.parse(raw);
    if(Array.isArray(msgs)) return msgs.map(m=>`<div class="mb"><div class="mr r-${m.role}">${m.role}</div><div class="mb-body dc di">${esc(m.content||'')}</div></div>`).join('');
  }catch{}
  return `<div class="dc di">${esc(raw||'')}`;
}

function previewInput(raw){
  try{
    const msgs=JSON.parse(raw);
    if(Array.isArray(msgs)){
      const u=msgs.find(m=>m.role==='user');
      const c=u?u.content:(msgs[0]?.content||'');
      return c.slice(0,85)+(c.length>85?'…':'');
    }
  }catch{}
  return (raw||'').slice(0,85)+((raw||'').length>85?'…':'');
}

function toggleSel(row,cb){
  if(cb.checked) selected.add(row); else selected.delete(row);
  document.getElementById('r-'+row)?.classList.toggle('sel',cb.checked);
  refreshStats(); updateBulk();
}
function toggleAll(master){
  allRecords.forEach(r=>{
    if(master.checked) selected.add(r._row); else selected.delete(r._row);
    const el=document.getElementById('r-'+r._row);
    const cb=el?.querySelector('.chk');
    el?.classList.toggle('sel',master.checked);
    if(cb) cb.checked=master.checked;
  });
  refreshStats(); updateBulk();
}
function selAll(){ const master=document.getElementById('chkAll'); if(master){master.checked=true;toggleAll(master);} }
function clearSel(){ const master=document.getElementById('chkAll'); if(master){master.checked=false;toggleAll(master);} }
function updateBulk(){
  const n=selected.size;
  document.getElementById('bulk').style.display=n>0?'flex':'none';
  document.getElementById('bulk-n').textContent=n+' selected';
}

function cpCell(field,rowId){
  const r=allRecords.find(x=>x._row===rowId); if(!r) return;
  let val=r[field]||'';
  if(field==='input'){ try{const m=JSON.parse(val);if(Array.isArray(m))val=m.map(x=>`[${x.role}]\n${x.content}`).join('\n\n');}catch{} }
  navigator.clipboard.writeText(val).then(()=>{
    const btn=document.getElementById('cb-'+field[0]+'-'+rowId);
    if(btn){btn.textContent='✓';btn.classList.add('ok');setTimeout(()=>{btn.textContent='copy';btn.classList.remove('ok');},1800);}
    toast(field+' copied','g');
  });
}
function copyRow(rowId){
  const r=allRecords.find(x=>x._row===rowId); if(!r) return;
  navigator.clipboard.writeText(JSON.stringify(r,null,2)).then(()=>toast('row copied as JSON'));
}
function copySelJSON(){
  const rows=allRecords.filter(r=>selected.has(r._row));
  if(!rows.length){toast('Nothing selected');return;}
  navigator.clipboard.writeText(rows.map(r=>JSON.stringify(r)).join('\n')).then(()=>toast(rows.length+' rows copied','g'));
}
function exportVisible(){
  const rows=selected.size>0?allRecords.filter(r=>selected.has(r._row)):allRecords;
  if(!rows.length){toast('Nothing to export');return;}
  const blob=new Blob([rows.map(r=>JSON.stringify(r)).join('\n')],{type:'application/jsonl'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='export.jsonl';a.click();
  toast('Exported '+rows.length+' rows','g');
}
function exportSel(){ exportVisible(); }

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){ closeNameModal(); closeSaveModal(); closeDeleteModal(); clearSel(); }
  if((e.ctrlKey||e.metaKey)&&e.key==='a'&&document.activeElement.tagName!=='INPUT'){e.preventDefault();selAll();}
  if((e.ctrlKey||e.metaKey)&&e.key==='c'&&selected.size>0&&document.activeElement.tagName!=='INPUT'){e.preventDefault();copySelJSON();}
  if(document.getElementById('nameOverlay').style.display!=='none'&&e.key==='Enter'){e.preventDefault();saveGroupName();}
  if(document.getElementById('saveOverlay').style.display!=='none'&&e.key==='Enter'){e.preventDefault();doSave();}
});

initFiles();
setInterval(initFiles, 30000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=VIEWER_PORT, debug=False)
