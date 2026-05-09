"""
viewer.py  —  inference-capture dataset viewer v3
-------------------------------------------------
  · Dark charcoal theme with Lucide icons
  · Groups rows by user-message prefix
  · Classifier collection breakdown per group
  · Per-group hit/miss stats with avg RAG score
  · Collapsible Stats Panel: sortable table
  · Delete whole group
  · Save processed dataset with category field
  · Incremental polling (appends only new rows)
  · Full RAG / classifier detail panel per row
  · Debounced search, DocumentFragment batch rendering
"""

import os, json, glob
from flask import Flask, jsonify, Response, request

DATA_DIR    = "data"
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
    data           = request.json or {}
    filename       = data.get("filename", "")
    rows_to_delete = set(int(x) for x in data.get("rows", []))
    if not filename:
        return jsonify({"status": "error", "message": "no filename"}), 400
    path = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(path):
        return jsonify({"status": "error", "message": "file not found"}), 404
    kept, deleted = [], 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if i in rows_to_delete:
                deleted += 1
            else:
                kept.append(line if line.endswith("\n") else line + "\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(kept)
    return jsonify({"status": "ok", "deleted": deleted, "remaining": len(kept)})


@app.route("/api/save_processed", methods=["POST"])
def save_processed():
    data     = request.json or {}
    filename = data.get("filename", "processed_dataset.jsonl")
    records  = data.get("records", [])
    if not filename.endswith(".jsonl"):
        filename += ".jsonl"
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return jsonify({"status": "ok", "path": path, "count": len(records)})


# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>inference-capture</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

/* ── Dark theme (default) ─────────────────────────────────── */
:root{
  --bg:      #1c1c22;
  --surf:    #252532;
  --surf2:   #2e2e3c;
  --surf3:   #373748;
  --bdr:     #3e3e50;
  --bdr2:    #505064;

  --acc:     #818cf8;
  --acc-d:   #6366f1;
  --acc-l:   rgba(129,140,248,.16);
  --acc-ll:  rgba(129,140,248,.08);

  --hit:     #4ade80;
  --hit-l:   rgba(74,222,128,.16);
  --hit-bg:  rgba(74,222,128,.08);
  --miss:    #f87171;
  --miss-l:  rgba(248,113,113,.16);
  --miss-bg: rgba(248,113,113,.08);

  --amber:   #fbbf24;
  --amber-l: rgba(251,191,36,.16);
  --blue:    #60a5fa;
  --blue-l:  rgba(96,165,250,.16);
  --pur:     #c084fc;
  --pur-l:   rgba(192,132,252,.16);

  --txt:     #eeeef5;
  --txt2:    #b0b0c4;
  --txt3:    #7c7c94;
  --txt4:    #565668;

  --mono: 'JetBrains Mono','Fira Code',monospace;
  --sans: 'Inter',-apple-system,sans-serif;
  --fs:   14px;
  --r:    7px;
  --shadow: 0 2px 8px rgba(0,0,0,.4), 0 8px 32px rgba(0,0,0,.28);
}

/* ── Light theme ──────────────────────────────────────────── */
html[data-theme="light"]{
  --bg:      #f0f0f6;
  --surf:    #ffffff;
  --surf2:   #f4f4f9;
  --surf3:   #eaeaf2;
  --bdr:     #dedee8;
  --bdr2:    #cacad8;

  --acc:     #6366f1;
  --acc-d:   #4f46e5;
  --acc-l:   rgba(99,102,241,.12);
  --acc-ll:  rgba(99,102,241,.06);

  --hit:     #16a34a;
  --hit-l:   rgba(22,163,74,.13);
  --hit-bg:  rgba(22,163,74,.07);
  --miss:    #dc2626;
  --miss-l:  rgba(220,38,38,.12);
  --miss-bg: rgba(220,38,38,.06);

  --amber:   #d97706;
  --amber-l: rgba(217,119,6,.13);
  --blue:    #2563eb;
  --blue-l:  rgba(37,99,235,.13);
  --pur:     #9333ea;
  --pur-l:   rgba(147,51,234,.12);

  --txt:     #18182e;
  --txt2:    #42425a;
  --txt3:    #68688a;
  --txt4:    #9494ae;

  --shadow: 0 2px 8px rgba(0,0,0,.08), 0 8px 32px rgba(0,0,0,.05);
}

html,body{height:100%;background:var(--bg);color:var(--txt);font-family:var(--sans);font-size:var(--fs);line-height:1.5}
body{display:flex;flex-direction:column;overflow:hidden}

/* ── Lucide icons ─────────────────────────────────────────── */
.icon{width:15px;height:15px;display:inline-block;vertical-align:middle;flex-shrink:0}
.icon-sm{width:13px;height:13px;display:inline-block;vertical-align:middle;flex-shrink:0}
.icon-lg{width:17px;height:17px;display:inline-block;vertical-align:middle;flex-shrink:0}
svg.lucide{stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;fill:none}

/* ── Topbar ───────────────────────────────────────────────── */
.topbar{
  height:58px;flex-shrink:0;display:flex;align-items:center;gap:10px;
  padding:0 20px;background:var(--surf);border-bottom:1px solid var(--bdr);
  box-shadow:0 1px 0 rgba(0,0,0,.2)
}
.logo{
  font-family:var(--mono);font-size:14px;font-weight:700;letter-spacing:-.02em;
  color:var(--txt);white-space:nowrap;display:flex;align-items:center;gap:8px
}
.logo-dot{
  width:10px;height:10px;border-radius:50%;background:var(--acc);flex-shrink:0;
  box-shadow:0 0 10px var(--acc-d)
}
.logo em{color:var(--acc);font-style:normal}
.vr{width:1px;height:22px;background:var(--bdr2);flex-shrink:0}

select,input[type=text]{
  background:var(--surf2);border:1px solid var(--bdr2);color:var(--txt);
  font-family:var(--mono);font-size:13px;padding:6px 10px;border-radius:var(--r);
  outline:none;transition:border-color .15s,box-shadow .15s
}
select:focus,input[type=text]:focus{border-color:var(--acc);box-shadow:0 0 0 3px rgba(129,140,248,.18)}
#fileSelect{min-width:240px}

.btn{
  background:var(--surf2);border:1px solid var(--bdr2);color:var(--txt2);
  font-family:var(--sans);font-size:13px;font-weight:500;padding:6px 13px;
  border-radius:var(--r);cursor:pointer;transition:all .15s;display:inline-flex;
  align-items:center;gap:6px;white-space:nowrap
}
.btn:hover{border-color:var(--acc);color:var(--acc);background:var(--acc-l)}
.btn.active{background:var(--acc-l);border-color:var(--acc);color:var(--acc)}
.btn.green{color:var(--hit);border-color:rgba(74,222,128,.4);background:var(--hit-l)}
.btn.green:hover{opacity:.85}
.btn.danger{color:var(--miss);border-color:rgba(248,113,113,.4);background:var(--miss-l)}
.btn:disabled{opacity:.35;cursor:not-allowed;pointer-events:none}

.topbar-r{margin-left:auto;display:flex;align-items:center;gap:6px}
.fsc{display:flex;align-items:center;gap:3px}
.fsb{
  width:28px;height:28px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;background:var(--surf2);border:1px solid var(--bdr2);
  color:var(--txt3);cursor:pointer;font-size:14px;transition:all .15s
}
.fsb:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}
.fsl{font-size:12px;color:var(--txt3);font-family:var(--mono);min-width:36px;text-align:center}

/* ── Stats Panel ──────────────────────────────────────────── */
.stats-panel{
  flex-shrink:0;background:var(--surf);border-bottom:1px solid var(--bdr);
  overflow:hidden;transition:max-height .28s cubic-bezier(.4,0,.2,1)
}
.stats-panel.closed{max-height:0}
.stats-panel.open{max-height:540px;overflow-y:auto}

.sp-inner{padding:16px 20px 18px}
.sp-overall{
  display:flex;align-items:center;gap:20px;margin-bottom:16px;
  padding-bottom:16px;border-bottom:1px solid var(--bdr)
}
.sp-overall-label{
  font-family:var(--mono);font-size:11px;font-weight:600;
  color:var(--txt4);text-transform:uppercase;letter-spacing:.08em
}
.sp-kpi{display:flex;align-items:baseline;gap:6px}
.sp-kpi-val{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--txt)}
.sp-kpi-sub{font-family:var(--mono);font-size:12px;color:var(--txt3)}
.sp-kpi-val.green{color:var(--hit)}
.sp-kpi-val.red{color:var(--miss)}
.sp-big-bar{flex:1;height:7px;background:rgba(248,113,113,.2);border-radius:4px;overflow:hidden;min-width:100px}
.sp-big-fill{height:100%;background:var(--hit);border-radius:4px;transition:width .4s ease}

.sp-table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:13px}
.sp-table th{
  padding:7px 12px;text-align:left;font-size:10px;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;color:var(--txt4);
  border-bottom:1px solid var(--bdr);cursor:pointer;user-select:none;white-space:nowrap
}
.sp-table th:hover{color:var(--acc)}
.sp-table th.sort-asc::after{content:' ▲';color:var(--acc)}
.sp-table th.sort-desc::after{content:' ▼';color:var(--acc)}
.sp-table td{padding:9px 12px;border-bottom:1px solid var(--bdr);vertical-align:middle}
.sp-table tr:last-child td{border-bottom:none}
.sp-table tr:hover td{background:var(--acc-ll);cursor:pointer}
.sp-name-cell{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--txt)}
.sp-name-cell.unnamed{color:var(--txt4);font-style:italic}
.sp-num{color:var(--txt2);text-align:right;font-variant-numeric:tabular-nums}
.sp-hit-num{color:var(--hit);font-weight:600;text-align:right}
.sp-miss-num{color:var(--miss);font-weight:600;text-align:right}
.sp-pct{font-weight:700;text-align:right;font-variant-numeric:tabular-nums}
.sp-bar-cell{width:130px}
.sp-mini-bar{height:5px;background:rgba(248,113,113,.2);border-radius:3px;overflow:hidden}
.sp-mini-fill{height:100%;background:var(--hit);border-radius:3px}
.sp-score{color:var(--txt3);text-align:right;font-variant-numeric:tabular-nums}

/* ── Filter bar ───────────────────────────────────────────── */
.fbar{
  height:46px;flex-shrink:0;display:flex;align-items:center;gap:8px;
  padding:0 20px;background:var(--surf2);border-bottom:1px solid var(--bdr);
  font-size:13px;overflow-x:auto;scrollbar-width:none
}
.pill{
  display:flex;align-items:center;gap:5px;background:var(--surf3);
  border:1px solid var(--bdr2);border-radius:20px;padding:3px 11px;
  font-size:12px;font-family:var(--mono);white-space:nowrap;color:var(--txt3)
}
.pill b{color:var(--txt)}
.pill.live b{color:var(--hit)}
.pill.live::before{
  content:'';width:7px;height:7px;border-radius:50%;
  background:var(--hit);flex-shrink:0;animation:pulse 2s infinite
}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}
.fw{margin-left:auto;display:flex;align-items:center;gap:6px;flex-shrink:0}
.chip{
  background:var(--surf3);border:1px solid var(--bdr);border-radius:20px;
  padding:3px 12px;font-size:12px;font-family:var(--mono);color:var(--txt3);
  cursor:pointer;transition:all .15s;white-space:nowrap
}
.chip:hover,.chip.on{background:var(--acc-l);border-color:var(--acc);color:var(--acc);font-weight:600}
.srch-wrap{position:relative;display:flex;align-items:center}
.srch-icon{position:absolute;left:9px;color:var(--txt4);pointer-events:none}
#srch{width:230px;padding-left:30px}

/* ── Table wrapper ────────────────────────────────────────── */
.tw{flex:1;overflow:auto;scrollbar-width:thin;scrollbar-color:var(--bdr2) transparent}
table{width:100%;border-collapse:collapse;table-layout:fixed}
colgroup col.cs{width:36px}
colgroup col.cn{width:52px}
colgroup col.ct{width:136px}
colgroup col.ci{width:24%}
colgroup col.cc{width:24%}
colgroup col.ca{width:22%}
colgroup col.cb{width:78px}

thead{position:sticky;top:0;z-index:20;background:var(--surf)}
th{
  padding:0 12px;height:40px;text-align:left;font-family:var(--mono);font-size:11px;
  font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--txt3);
  border-bottom:2px solid var(--bdr2);border-right:1px solid var(--bdr);white-space:nowrap
}
th:last-child{border-right:none}
th.tc{text-align:center}

/* ── Group header ─────────────────────────────────────────── */
.gh-cell{padding:0!important;border-right:none!important;background:transparent!important}
.gh-wrap{
  border-left:6px solid;
  border-bottom:1px solid rgba(128,128,128,.12);
  margin-top:6px;
  border-radius:0 8px 8px 0
}
html[data-theme="light"] .gh-wrap{border-bottom-color:rgba(0,0,0,.09)}

.gh-main{
  display:flex;align-items:center;min-height:54px;padding:10px 16px 10px 14px;gap:12px
}

/* Group number badge */
.gh-num{
  display:inline-flex;align-items:center;justify-content:center;
  min-width:26px;height:26px;border-radius:8px;font-family:var(--mono);
  font-size:11px;font-weight:800;flex-shrink:0;
  color:#fff;letter-spacing:-.02em;padding:0 4px
}
.gh-collapse{
  display:flex;align-items:center;gap:9px;cursor:pointer;flex:1;min-width:0;
  padding:2px 0;user-select:none
}
.gh-collapse:hover .gh-name{opacity:.75}
.gh-chev{
  color:var(--txt4);flex-shrink:0;transition:transform .18s;
  display:flex;align-items:center
}
.gh-chev.open{transform:rotate(90deg)}
.gh-name{
  font-family:var(--sans);font-size:15px;font-weight:700;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0;letter-spacing:-.01em
}
.gh-name.unnamed{opacity:.35;font-weight:400;font-style:italic}

/* Hit stats */
.gh-hitbar-wrap{display:flex;align-items:center;gap:8px;flex-shrink:0}
.gh-row-count{
  font-family:var(--mono);font-size:12px;color:var(--txt3);white-space:nowrap;
  background:var(--surf3);padding:2px 8px;border-radius:20px;border:1px solid var(--bdr)
}
.gh-hit-nums{display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:12px;font-weight:700}
.gh-hit-up{color:var(--hit)}
.gh-hit-dn{color:var(--miss)}
.gh-bar{width:72px;height:5px;background:rgba(248,113,113,.2);border-radius:3px;overflow:hidden;flex-shrink:0}
.gh-bar-fill{height:100%;background:var(--hit);border-radius:3px;transition:width .3s ease}
.gh-hit-pct{font-family:var(--mono);font-size:12px;font-weight:800;min-width:40px;text-align:right}
.gh-avg-score{
  font-family:var(--mono);font-size:11px;color:var(--txt3);
  padding:2px 8px;background:rgba(255,255,255,.04);border:1px solid var(--bdr);
  border-radius:5px;white-space:nowrap
}
html[data-theme="light"] .gh-avg-score{background:rgba(0,0,0,.04)}

/* Group actions */
.gh-actions{display:flex;align-items:center;gap:5px;flex-shrink:0}
.gab{
  font-family:var(--sans);font-size:12px;font-weight:500;padding:5px 11px;border-radius:6px;
  border:1px solid var(--bdr);background:rgba(255,255,255,.04);color:var(--txt3);
  cursor:pointer;transition:all .12s;white-space:nowrap;display:flex;align-items:center;gap:6px
}
html[data-theme="light"] .gab{background:rgba(0,0,0,.04)}
.gab:hover{background:var(--surf3);color:var(--txt);border-color:var(--bdr2)}
.gab.del{color:var(--miss);border-color:rgba(248,113,113,.3)}
.gab.del:hover{background:var(--miss-l);border-color:var(--miss)}
.gab.edit:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}

/* Classifier breakdown row */
.gh-clf-row{
  display:flex;align-items:center;gap:6px;padding:6px 16px 11px 46px;flex-wrap:wrap;
  border-top:1px solid rgba(128,128,128,.08)
}
.gh-clf-label{
  font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.07em;
  text-transform:uppercase;color:var(--txt4);white-space:nowrap;flex-shrink:0;
  display:flex;align-items:center;gap:4px
}
.clf-tag{
  display:inline-flex;align-items:center;gap:4px;font-family:var(--mono);font-size:11px;
  font-weight:500;padding:3px 10px;border-radius:20px;
  background:var(--surf3);color:var(--txt3);border:1px solid var(--bdr);
  white-space:nowrap;transition:all .12s;cursor:default
}
.clf-tag b{font-weight:700;color:var(--txt2)}
.clf-tag:hover{background:var(--acc-l);border-color:var(--acc);color:var(--acc)}
.clf-tag.clf-reject{background:var(--miss-l);color:var(--miss);border-color:rgba(248,113,113,.3)}
.clf-tag.clf-reject b{color:var(--miss)}
.clf-tag.clf-top{border-color:rgba(129,140,248,.5);background:var(--acc-l);color:var(--acc)}
.clf-tag.clf-top b{color:var(--acc)}

/* Group prompt panel */
.gh-panel{
  padding:12px 18px 14px 48px;border-top:1px solid rgba(128,128,128,.07);
  font-family:var(--mono);font-size:12px;color:var(--txt3);white-space:pre-wrap;
  line-height:1.8;max-height:220px;overflow-y:auto;border-left:4px solid
}

/* ── Data rows ────────────────────────────────────────────── */
.dr{border-bottom:1px solid var(--bdr);cursor:pointer;transition:background .08s}
.dr:hover td{background:rgba(129,140,248,.05)!important}
.dr.exp td{background:var(--acc-ll)!important}
.dr.sel{background:rgba(129,140,248,.10)!important;box-shadow:inset 4px 0 0 var(--acc)}
.dr.hid,.det-row.hid{display:none}

td{
  padding:0 12px;height:52px;vertical-align:middle;font-family:var(--mono);
  color:var(--txt2);border-right:1px solid var(--bdr);overflow:hidden
}
td:last-child{border-right:none}
td.tc{text-align:center}
td.ts{color:var(--txt3);font-size:12px}
.prev{
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  max-width:100%;display:block;font-size:13px;line-height:1.4
}
.pi{color:var(--txt)}
.pa{color:var(--hit);font-weight:600}
.pc{color:var(--txt2);font-style:italic}
.pn{color:var(--txt4);font-style:italic}
.hit-dot{
  display:inline-block;width:8px;height:8px;border-radius:50%;
  margin-right:6px;flex-shrink:0;vertical-align:middle
}
.hit-dot.on{background:var(--hit);box-shadow:0 0 6px rgba(74,222,128,.6)}
.hit-dot.off{background:var(--miss);box-shadow:0 0 4px rgba(248,113,113,.4)}
.badge{
  display:inline-flex;align-items:center;justify-content:center;font-family:var(--mono);
  font-size:11px;font-weight:600;padding:3px 7px;border-radius:5px;min-width:32px;
  background:var(--surf3);color:var(--txt3);border:1px solid var(--bdr)
}
.chk{width:14px;height:14px;cursor:pointer;accent-color:var(--acc)}
.acts{display:flex;align-items:center;justify-content:center;gap:4px}
.ib{
  width:28px;height:28px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;background:var(--surf2);border:1px solid var(--bdr);
  color:var(--txt3);cursor:pointer;transition:all .12s
}
.ib:hover{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}
.ib.on{color:var(--acc);border-color:var(--acc);background:var(--acc-l)}

/* ── Detail panel ─────────────────────────────────────────── */
.det-row td{height:auto;padding:0;border-right:none;background:var(--surf)}
.det-grid{
  display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;
  background:var(--bdr);border-top:3px solid var(--acc)
}
.det-col{background:var(--surf);padding:18px 20px}
.det-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.lbl{
  font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.09em;
  text-transform:uppercase;display:flex;align-items:center;gap:8px;flex:1;color:var(--txt3)
}
.lbl::after{content:'';flex:1;height:1px;background:var(--bdr)}
.li{color:var(--amber)}.lc{color:var(--txt3)}.la{color:var(--hit)}
.cpb{
  font-family:var(--mono);font-size:10px;font-weight:700;padding:4px 10px;border-radius:5px;
  border:1px solid var(--bdr2);background:var(--surf2);color:var(--txt3);cursor:pointer;
  transition:all .12s;text-transform:uppercase;display:flex;align-items:center;gap:5px
}
.cpb:hover{background:var(--acc-l);border-color:var(--acc);color:var(--acc)}
.cpb.ok{background:var(--hit-l);border-color:rgba(74,222,128,.4);color:var(--hit)}
.dc{
  font-family:var(--mono);line-height:1.85;font-size:13px;white-space:pre-wrap;
  word-break:break-word;max-height:320px;overflow-y:auto;scrollbar-width:thin;
  scrollbar-color:var(--bdr2) transparent
}
.di{color:var(--txt)}.dcc{color:var(--txt3);font-style:italic}.da{color:var(--hit);font-weight:600}
.mb{margin-bottom:12px}
.mr{
  font-size:10px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
  margin-bottom:4px;padding:3px 8px;border-radius:5px;display:inline-flex;
  align-items:center;gap:4px
}
.r-s{background:var(--blue-l);color:var(--blue)}
.r-u{background:var(--amber-l);color:var(--amber)}
.r-a{background:var(--acc-l);color:var(--acc)}
.mb-body{color:var(--txt);line-height:1.85;font-family:var(--mono);font-size:13px}
.no-c{color:var(--txt4);font-style:italic;font-size:13px;padding:4px 0}
.meta-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:1px;
  background:var(--bdr);border-top:1px solid var(--bdr)
}
.ms{background:var(--surf2);padding:14px 20px}
.mt{
  font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.09em;
  text-transform:uppercase;color:var(--txt4);margin-bottom:10px;
  display:flex;align-items:center;gap:6px
}
.mk{font-family:var(--mono);font-size:12px;color:var(--txt3);min-width:155px;flex-shrink:0}
.mv{font-family:var(--mono);font-size:12px;color:var(--txt);font-weight:600}
.mr2{display:flex;align-items:baseline;gap:10px;padding:5px 0;border-bottom:1px solid var(--bdr)}
.mr2:last-child{border-bottom:none}

/* ── RAG / Classifier panel ───────────────────────────────── */
.rag-panel{background:var(--surf);border-top:1px solid var(--bdr)}
.rag-sum{
  display:flex;align-items:center;gap:10px;padding:12px 20px;
  border-top-width:3px;border-top-style:solid
}
.rag-sum.hit{border-top-color:var(--hit);background:var(--hit-bg)}
.rag-sum.miss{border-top-color:var(--miss);background:var(--miss-bg)}
.rag-badge{
  display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);
  font-size:11px;font-weight:700;padding:4px 11px;border-radius:20px;border:1px solid
}
.rag-badge.hit{background:var(--hit-l);border-color:rgba(74,222,128,.4);color:var(--hit)}
.rag-badge.miss{background:var(--miss-l);border-color:rgba(248,113,113,.4);color:var(--miss)}
.clf-pill{
  font-family:var(--mono);font-size:11px;font-weight:600;padding:3px 10px;
  border-radius:20px;border:1px solid;white-space:nowrap
}
.clf-pill.ok{background:var(--hit-l);border-color:rgba(74,222,128,.4);color:var(--hit)}
.clf-pill.bad{background:var(--miss-l);border-color:rgba(248,113,113,.4);color:var(--miss)}
.clf-pill.skip{background:var(--amber-l);border-color:rgba(251,191,36,.4);color:var(--amber)}
.clf-pill.unk{background:var(--surf3);border-color:var(--bdr2);color:var(--txt3)}
.rag-sum-txt{font-family:var(--mono);font-size:12px;color:var(--txt3)}
.rag-score-txt{font-family:var(--mono);font-size:12px;font-weight:700}
.rag-toggle-btn{
  font-family:var(--sans);font-size:12px;font-weight:500;padding:5px 12px;
  border-radius:6px;border:1px solid var(--bdr2);background:var(--surf2);color:var(--txt3);
  cursor:pointer;transition:all .12s;margin-left:auto;white-space:nowrap;
  display:flex;align-items:center;gap:6px
}
.rag-toggle-btn:hover{background:var(--acc-l);border-color:var(--acc);color:var(--acc)}
.rag-g4{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:1px;background:var(--bdr)}
.rag-col{background:var(--surf2);padding:16px 20px}
.rag-hdr{
  font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--txt4);margin-bottom:12px;
  display:flex;align-items:center;gap:8px
}
.rag-hdr::after{content:'';flex:1;height:1px;background:var(--bdr)}
.rag-kv{
  display:flex;align-items:baseline;gap:8px;padding:5px 0;
  border-bottom:1px solid var(--bdr);font-family:var(--mono);font-size:12px
}
.rag-kv:last-of-type{border-bottom:none}
.rag-k{color:var(--txt3);min-width:140px;flex-shrink:0}
.rag-v{color:var(--txt);font-weight:600;word-break:break-all}
.rag-v.hi{color:var(--hit)}.rag-v.lo{color:var(--miss)}.rag-v.mr{color:var(--miss)}
.rag-blk{
  font-family:var(--mono);font-size:12px;line-height:1.8;white-space:pre-wrap;
  word-break:break-word;overflow-y:auto;border-radius:6px;padding:11px 13px;
  scrollbar-width:thin;scrollbar-color:var(--bdr2) transparent;margin-top:10px
}
.rag-blk.pas{background:var(--surf3);color:var(--txt2);max-height:260px;border:1px solid var(--bdr)}
.rag-blk.think{background:rgba(251,191,36,.07);color:#fcd34d;font-style:italic;max-height:220px;border:1px solid rgba(251,191,36,.2)}
.rag-blk.raw{background:var(--bg);color:var(--txt3);max-height:120px;font-size:11px;border:1px solid var(--bdr)}
.rag-blk.inj{background:rgba(96,165,250,.06);color:#93c5fd;border:1px solid rgba(96,165,250,.2);max-height:300px;font-size:12px}
.rag-blk.cot{background:var(--acc-ll);color:var(--acc);max-height:220px;border:1px solid rgba(129,140,248,.2)}
.rag-none{color:var(--txt4);font-style:italic;font-size:12px;padding:8px 0}

/* ── Modals ───────────────────────────────────────────────── */
.overlay{
  position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:300;
  display:flex;align-items:center;justify-content:center;
  backdrop-filter:blur(4px);animation:fi .15s ease
}
@keyframes fi{from{opacity:0}to{opacity:1}}
.modal{
  background:var(--surf);border:1px solid var(--bdr2);border-radius:12px;
  padding:28px 30px;width:480px;box-shadow:var(--shadow);animation:ms .15s ease
}
@keyframes ms{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.modal h3{font-size:17px;font-weight:700;margin-bottom:6px;color:var(--txt);display:flex;align-items:center;gap:9px}
.modal p{font-size:13px;color:var(--txt3);margin-bottom:18px;font-family:var(--mono);line-height:1.75}
.modal input{width:100%;margin-bottom:16px;font-size:14px;padding:8px 11px}
.modal-btns{display:flex;gap:8px;justify-content:flex-end}
.name-preview{
  font-family:var(--mono);font-size:12px;color:var(--txt3);margin-bottom:16px;
  padding:10px 12px;background:var(--surf2);border:1px solid var(--bdr);border-radius:6px;
  line-height:1.7;max-height:80px;overflow:hidden
}
.del-info{
  font-family:var(--mono);font-size:13px;color:var(--txt2);margin-bottom:18px;
  padding:13px 15px;background:var(--miss-l);border-radius:7px;
  border-left:4px solid var(--miss);line-height:1.75
}

/* ── Bulk bar ─────────────────────────────────────────────── */
.bulk{
  position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
  background:var(--surf3);color:var(--txt);border:1px solid var(--bdr2);
  border-radius:12px;padding:10px 18px;display:flex;align-items:center;gap:10px;
  box-shadow:var(--shadow);z-index:100;font-size:13px;font-family:var(--mono);
  animation:su .15s ease
}
@keyframes su{from{transform:translateX(-50%) translateY(8px);opacity:0}
              to{transform:translateX(-50%) translateY(0);opacity:1}}
.bb{
  background:rgba(255,255,255,.07);border:1px solid var(--bdr2);color:var(--txt2);
  font-family:var(--sans);font-size:12px;font-weight:500;padding:5px 12px;border-radius:6px;
  cursor:pointer;transition:all .12s;white-space:nowrap;display:flex;align-items:center;gap:5px
}
.bb:hover{background:rgba(255,255,255,.12);color:var(--txt)}
.bb.g{background:var(--hit-l);border-color:rgba(74,222,128,.3);color:var(--hit)}
.bb.r{background:var(--miss-l);border-color:rgba(248,113,113,.3);color:var(--miss)}

/* ── Toast ────────────────────────────────────────────────── */
.toast{
  position:fixed;bottom:72px;right:22px;background:var(--surf3);color:var(--txt);
  border:1px solid var(--bdr2);border-radius:8px;padding:10px 16px;font-size:13px;
  font-family:var(--mono);box-shadow:var(--shadow);z-index:500;
  animation:ti .15s ease;pointer-events:none;display:flex;align-items:center;gap:8px
}
.toast.g{background:var(--hit-l);border-color:rgba(74,222,128,.4);color:var(--hit)}
.toast.r{background:var(--miss-l);border-color:rgba(248,113,113,.4);color:var(--miss)}
@keyframes ti{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}

/* ── Empty state ──────────────────────────────────────────── */
.empty{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  flex:1;gap:14px;color:var(--txt3);padding:80px;text-align:center
}
.empty-ico{font-size:48px;margin-bottom:6px;opacity:.4}
.empty h4{font-size:18px;font-weight:700;color:var(--txt2)}
.empty p{font-size:14px;font-family:var(--mono);color:var(--txt4);line-height:1.7}

/* ── Loading overlay ──────────────────────────────────────── */
#loadOverlay{
  position:fixed;inset:0;background:rgba(15,15,17,.9);z-index:9999;
  display:none;flex-direction:column;align-items:center;justify-content:center;
  gap:20px;backdrop-filter:blur(6px)
}
#loadOverlay.show{display:flex}
.load-card{
  background:var(--surf);border:1px solid var(--bdr2);border-radius:14px;
  padding:36px 48px;display:flex;flex-direction:column;align-items:center;
  gap:18px;min-width:340px;box-shadow:0 8px 48px rgba(0,0,0,.5)
}
.load-spinner{
  width:40px;height:40px;border:3px solid var(--bdr2);
  border-top-color:var(--acc);border-radius:50%;
  animation:spin .7s linear infinite
}
@keyframes spin{to{transform:rotate(360deg)}}
.load-title{font-family:var(--mono);font-size:16px;font-weight:700;color:var(--txt);letter-spacing:-.01em}
.load-msg{font-family:var(--mono);font-size:13px;color:var(--txt3);text-align:center;min-height:1.5em}
.load-prog-wrap{width:100%;height:5px;background:var(--bdr);border-radius:3px;overflow:hidden}
.load-prog{height:100%;background:var(--acc);border-radius:3px;transition:width .15s ease;width:0%}
.load-sub{font-family:var(--mono);font-size:11px;color:var(--txt4);text-align:center}
</style>
</head>
<body>

<!-- ── TOPBAR ──────────────────────────────────────────────────────────────── -->
<div class="topbar">
  <div class="logo">
    <span class="logo-dot"></span>
    inference<em>capture</em>
  </div>
  <div class="vr"></div>
  <select id="fileSelect" onchange="onFileChange()"><option value="">— select file —</option></select>
  <div class="topbar-r">
    <button class="btn" id="statsBtn" onclick="toggleStats()" disabled>
      <i data-lucide="bar-chart-2" class="icon"></i> Stats
    </button>
    <div class="vr"></div>
    <button class="btn" id="themeBtn" onclick="toggleTheme()" title="Toggle light/dark mode">
      <i data-lucide="moon" class="icon"></i>
    </button>
    <div class="vr"></div>
    <div class="fsc">
      <button class="fsb" onclick="chFS(-1)" title="Decrease font size"><i data-lucide="minus" class="icon-sm"></i></button>
      <span class="fsl" id="fsl">14px</span>
      <button class="fsb" onclick="chFS(1)" title="Increase font size"><i data-lucide="plus" class="icon-sm"></i></button>
    </div>
    <div class="vr"></div>
    <button class="btn" onclick="collapseAll()"><i data-lucide="chevrons-down-up" class="icon"></i> collapse</button>
    <button class="btn" onclick="expandAll()"><i data-lucide="chevrons-up-down" class="icon"></i> expand</button>
    <button class="btn green" onclick="openSaveModal()"><i data-lucide="save" class="icon"></i> save</button>
    <button class="btn" onclick="exportVisible()"><i data-lucide="download" class="icon"></i> export</button>
  </div>
</div>

<!-- ── STATS PANEL ─────────────────────────────────────────────────────────── -->
<div class="stats-panel closed" id="statsPanel">
  <div class="sp-inner">
    <div class="sp-overall" id="spOverall">
      <span class="sp-overall-label">overall</span>
      <div class="sp-kpi"><span class="sp-kpi-val" id="sp-total">0</span><span class="sp-kpi-sub">rows</span></div>
      <div class="sp-kpi"><span class="sp-kpi-val green" id="sp-hits">0</span><span class="sp-kpi-sub">hits</span></div>
      <div class="sp-kpi"><span class="sp-kpi-val red" id="sp-miss">0</span><span class="sp-kpi-sub">miss</span></div>
      <div class="sp-big-bar"><div class="sp-big-fill" id="sp-bigfill" style="width:0%"></div></div>
      <div class="sp-kpi"><span class="sp-kpi-val" id="sp-rate">—</span><span class="sp-kpi-sub">hit rate</span></div>
    </div>
    <table class="sp-table" id="spTable">
      <thead><tr>
        <th onclick="sortStats('name')">Group</th>
        <th onclick="sortStats('total')" class="sort-desc">Rows</th>
        <th onclick="sortStats('hits')">Hits</th>
        <th onclick="sortStats('misses')">Miss</th>
        <th onclick="sortStats('pct')" class="sp-bar-cell">Hit Rate</th>
        <th onclick="sortStats('pct')">%</th>
        <th onclick="sortStats('score')">Avg Score</th>
      </tr></thead>
      <tbody id="spBody"></tbody>
    </table>
  </div>
</div>

<!-- ── FILTER BAR ──────────────────────────────────────────────────────────── -->
<div class="fbar" id="fbar" style="display:none">
  <div class="pill"><span>rows</span> <b id="st-rows">0</b></div>
  <div class="pill"><span>groups</span> <b id="st-groups">0</b></div>
  <div class="pill"><span>named</span> <b id="st-named">0</b></div>
  <div class="pill"><span>sel</span> <b id="st-sel">0</b></div>
  <div class="pill live"><b>live</b></div>
  <div class="fw">
    <span class="chip on"  id="c-all" onclick="setF('all')">all</span>
    <span class="chip"     id="c-hit" onclick="setF('hit')">hits only</span>
    <span class="chip"     id="c-mis" onclick="setF('mis')">misses only</span>
    <span class="chip"     id="c-cot" onclick="setF('cot')">has cot</span>
    <div class="srch-wrap">
      <i data-lucide="search" class="icon-sm srch-icon"></i>
      <input type="text" id="srch" placeholder="search input / answer…" oninput="debouncedFilter()">
    </div>
  </div>
</div>

<!-- ── MAIN ────────────────────────────────────────────────────────────────── -->
<div id="main" style="flex:1;display:flex;flex-direction:column;overflow:hidden">
  <div class="empty">
    <div class="empty-ico">🗂</div>
    <h4>No file selected</h4>
    <p>Choose a .jsonl file from the dropdown above to begin</p>
  </div>
</div>

<!-- ── BULK BAR ────────────────────────────────────────────────────────────── -->
<div class="bulk" id="bulk" style="display:none">
  <i data-lucide="layers" class="icon"></i>
  <span id="bulk-n">0 selected</span>
  <button class="bb g" onclick="copySelJSON()"><i data-lucide="clipboard" class="icon-sm"></i> copy JSONL</button>
  <button class="bb g" onclick="exportSel()"><i data-lucide="download" class="icon-sm"></i> export</button>
  <button class="bb" onclick="selAll()">select all</button>
  <button class="bb r" onclick="clearSel()"><i data-lucide="x" class="icon-sm"></i> clear</button>
</div>

<!-- ── MODAL: Name Group ───────────────────────────────────────────────────── -->
<div class="overlay" id="nameOverlay" style="display:none" onclick="closeNameModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3><i data-lucide="pencil" class="icon-lg"></i> Name this group</h3>
    <div class="name-preview" id="namePreview"></div>
    <input type="text" id="nameInput" placeholder="e.g. MedBullets, HeadQA…">
    <div class="modal-btns">
      <button class="btn" onclick="clearGroupName()">Clear</button>
      <button class="btn" onclick="closeNameModal()">Cancel</button>
      <button class="btn green" onclick="saveGroupName()"><i data-lucide="check" class="icon-sm"></i> Save</button>
    </div>
  </div>
</div>

<!-- ── MODAL: Save Processed ──────────────────────────────────────────────── -->
<div class="overlay" id="saveOverlay" style="display:none" onclick="closeSaveModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3><i data-lucide="save" class="icon-lg"></i> Save processed dataset</h3>
    <p>Records saved with a <b>category</b> field derived from group names.<br>
       Unnamed groups use their user-message prefix as the category.<br>
       Written to <b>data/</b> on the server.</p>
    <input type="text" id="saveFile" value="processed_dataset.jsonl">
    <div class="modal-btns">
      <button class="btn" onclick="closeSaveModal()">Cancel</button>
      <button class="btn green" onclick="doSave()"><i data-lucide="save" class="icon-sm"></i> Save to server</button>
    </div>
  </div>
</div>

<!-- ── MODAL: Delete Group ────────────────────────────────────────────────── -->
<div class="overlay" id="delOverlay" style="display:none" onclick="closeDelModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3><i data-lucide="trash-2" class="icon-lg"></i> Delete group</h3>
    <div class="del-info" id="delInfo"></div>
    <p>Permanently removes rows from <b id="delFilename"></b>.<br>The file will be rewritten. This cannot be undone.</p>
    <div class="modal-btns">
      <button class="btn" onclick="closeDelModal()">Cancel</button>
      <button class="btn danger" id="delConfirmBtn" onclick="confirmDelete()">
        <i data-lucide="trash-2" class="icon-sm"></i> Delete
      </button>
    </div>
  </div>
</div>

<!-- ── LOADING OVERLAY ────────────────────────────────────────────────────── -->
<div id="loadOverlay">
  <div class="load-card">
    <div class="load-spinner"></div>
    <div class="load-title">Loading dataset…</div>
    <div class="load-msg" id="loadMsg">Reading records</div>
    <div class="load-prog-wrap"><div class="load-prog" id="loadProg"></div></div>
    <div class="load-sub" id="loadSub"></div>
  </div>
</div>

<script>
// ── THEME ─────────────────────────────────────────────────────────────────────
const DARK_COLORS=[
  {bg:'rgba(129,140,248,.18)', bdr:'#818cf8', txt:'#a5b4fc', rowBg:'rgba(129,140,248,.05)'},
  {bg:'rgba(74,222,128,.16)',  bdr:'#4ade80', txt:'#86efac', rowBg:'rgba(74,222,128,.04)'},
  {bg:'rgba(251,191,36,.15)',  bdr:'#fbbf24', txt:'#fcd34d', rowBg:'rgba(251,191,36,.04)'},
  {bg:'rgba(96,165,250,.17)',  bdr:'#60a5fa', txt:'#93c5fd', rowBg:'rgba(96,165,250,.05)'},
  {bg:'rgba(192,132,252,.16)', bdr:'#c084fc', txt:'#d8b4fe', rowBg:'rgba(192,132,252,.04)'},
  {bg:'rgba(45,212,191,.15)',  bdr:'#2dd4bf', txt:'#5eead4', rowBg:'rgba(45,212,191,.04)'},
  {bg:'rgba(248,113,113,.15)', bdr:'#f87171', txt:'#fca5a5', rowBg:'rgba(248,113,113,.04)'},
  {bg:'rgba(250,204,21,.14)',  bdr:'#facc15', txt:'#fde047', rowBg:'rgba(250,204,21,.03)'},
];
const LIGHT_COLORS=[
  {bg:'rgba(99,102,241,.10)',  bdr:'#6366f1', txt:'#4f46e5', rowBg:'rgba(99,102,241,.03)'},
  {bg:'rgba(22,163,74,.10)',   bdr:'#16a34a', txt:'#15803d', rowBg:'rgba(22,163,74,.03)'},
  {bg:'rgba(217,119,6,.09)',   bdr:'#d97706', txt:'#b45309', rowBg:'rgba(217,119,6,.02)'},
  {bg:'rgba(37,99,235,.10)',   bdr:'#2563eb', txt:'#1d4ed8', rowBg:'rgba(37,99,235,.03)'},
  {bg:'rgba(147,51,234,.09)',  bdr:'#9333ea', txt:'#7e22ce', rowBg:'rgba(147,51,234,.03)'},
  {bg:'rgba(13,148,136,.09)',  bdr:'#0d9488', txt:'#0f766e', rowBg:'rgba(13,148,136,.02)'},
  {bg:'rgba(220,38,38,.09)',   bdr:'#dc2626', txt:'#b91c1c', rowBg:'rgba(220,38,38,.02)'},
  {bg:'rgba(202,138,4,.09)',   bdr:'#ca8a04', txt:'#a16207', rowBg:'rgba(202,138,4,.02)'},
];

let darkMode=localStorage.getItem('ic_theme')!=='light';
let COLORS=darkMode?[...DARK_COLORS]:[...LIGHT_COLORS];

function applyTheme(){
  document.documentElement.setAttribute('data-theme',darkMode?'dark':'light');
  COLORS.splice(0,COLORS.length,...(darkMode?DARK_COLORS:LIGHT_COLORS));
  const btn=document.getElementById('themeBtn');
  if(btn){btn.innerHTML=`<i data-lucide="${darkMode?'sun':'moon'}" class="icon"></i>`;lucide.createIcons({nodes:[btn]});}
  // Refresh group headers so colors update
  if(currentFile) groupKeys.forEach((_,key)=>refreshGroupHeader(key));
}
function toggleTheme(){
  darkMode=!darkMode;
  localStorage.setItem('ic_theme',darkMode?'dark':'light');
  applyTheme();
}

// ── STATE ─────────────────────────────────────────────────────────────────────

let currentFile = '';
let allRecords  = [];
let lastRow     = 0;
let groupKeys   = new Map(); // key → {gid,col,count,rows[],hits,misses,scoreSum,clfCounts{}}
let gidSeq      = 0;

let collapsed   = new Set();
let sysOpen     = new Set();
let selected    = new Set();
let catNames    = {};

let filterMode  = 'all';
let searchQ     = '';
let fontSize    = 14;
let pollTimer   = null;
let statsOpen   = false;
let _filterTimer = null;

let pendingDelete = {key:null, gid:null, rows:[]};
let statsSortCol  = 'total';
let statsSortDir  = -1;

// ── HELPERS ───────────────────────────────────────────────────────────────────
function esc(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }

function toast(msg, cls=''){
  const t=document.createElement('div');
  t.className='toast'+(cls?' '+cls:'');
  t.innerHTML=(cls==='g'?'<i data-lucide="check-circle" class="icon-sm"></i>':
               cls==='r'?'<i data-lucide="x-circle" class="icon-sm"></i>':
               '<i data-lucide="info" class="icon-sm"></i>')+' '+esc(msg);
  document.body.appendChild(t);
  lucide.createIcons({nodes:[t]});
  setTimeout(()=>t.remove(), 2800);
}

function isHit(r){
  return r.rag_hit===true||r.rag_hit==='True'||r.rag_hit===1||r.rag_hit==='true';
}

function getGroupKey(r){
  try{
    const msgs=JSON.parse(r.input);
    if(Array.isArray(msgs)){
      const u=msgs.find(m=>m.role==='user');
      if(u?.content){
        let content=u.content;
        const marker='ACTUAL CASE — evaluate this and only this';
        const mi=content.indexOf(marker);
        if(mi!==-1) content=content.slice(mi+marker.length);
        const line=content.split('\n').map(l=>l.trim()).find(l=>l&&!l.startsWith('='));
        return (line||'').slice(0,120)||'__ungrouped__';
      }
    }
  }catch{}
  return '__ungrouped__';
}

function catKey(){ return 'ic_cat_'+currentFile; }
function loadCats(){ try{ catNames=JSON.parse(localStorage.getItem(catKey())||'{}'); }catch{ catNames={}; } }
function persistCats(){ localStorage.setItem(catKey(),JSON.stringify(catNames)); refreshStatus(); }

function refreshStatus(){
  document.getElementById('st-rows').textContent   = allRecords.length;
  document.getElementById('st-groups').textContent = groupKeys.size;
  document.getElementById('st-named').textContent  = Object.keys(catNames).length;
  document.getElementById('st-sel').textContent    = selected.size;
}

function pct(a,b){ return b===0?0:Math.round(100*a/b); }
function fmtPct(a,b){ return b===0?'—':pct(a,b)+'%'; }
function fmtScore(sum,n){ return n===0?'—':(sum/n).toFixed(3); }

function chFS(d){
  fontSize=Math.min(20,Math.max(10,fontSize+d));
  document.documentElement.style.setProperty('--fs',fontSize+'px');
  document.getElementById('fsl').textContent=fontSize+'px';
}

function setF(f){
  filterMode=f;
  ['all','hit','mis','cot'].forEach(x=>document.getElementById('c-'+x).classList.toggle('on',x===f));
  applyFilter();
}

function debouncedFilter(){
  clearTimeout(_filterTimer);
  _filterTimer=setTimeout(applyFilter, 120);
}

function applyFilter(){
  searchQ=(document.getElementById('srch')?.value||'').toLowerCase().trim();
  const noFilter=filterMode==='all'&&!searchQ;
  allRecords.forEach(r=>{
    const rowEl=document.getElementById('r-'+r._row);
    if(!rowEl) return;
    const detEl=document.getElementById('d-'+r._row);
    const gid=rowEl.getAttribute('data-gid');
    const inColl=collapsed.has(gid);
    if(noFilter){
      rowEl.classList.toggle('hid',inColl);
      if(detEl) detEl.classList.toggle('hid',inColl||detEl.style.display==='none');
      return;
    }
    let show=true;
    const hit=isHit(r);
    if(filterMode==='hit'&&!hit) show=false;
    else if(filterMode==='mis'&&hit) show=false;
    else if(filterMode==='cot'&&!r.cot) show=false;
    if(searchQ&&show){
      const hay=(r.input||'')+(r.cot||'')+(r.answer||'');
      if(!hay.toLowerCase().includes(searchQ)) show=false;
    }
    rowEl.classList.toggle('hid',!show||inColl);
    if(detEl) detEl.classList.toggle('hid',!show||inColl||detEl.style.display==='none');
  });
}

// ── STATS PANEL ───────────────────────────────────────────────────────────────
function toggleStats(){
  statsOpen=!statsOpen;
  document.getElementById('statsPanel').className='stats-panel '+(statsOpen?'open':'closed');
  document.getElementById('statsBtn').classList.toggle('active',statsOpen);
  if(statsOpen) renderStatsPanel();
}

function renderStatsPanel(){
  let tot=0,hits=0,misses=0;
  groupKeys.forEach(g=>{ tot+=g.count; hits+=g.hits; misses+=g.misses; });
  document.getElementById('sp-total').textContent  = tot;
  document.getElementById('sp-hits').textContent   = hits;
  document.getElementById('sp-miss').textContent   = misses;
  document.getElementById('sp-rate').textContent   = fmtPct(hits,tot);
  document.getElementById('sp-bigfill').style.width= (tot?pct(hits,tot):0)+'%';

  const rows=[];
  groupKeys.forEach((g,key)=>{
    const name=catNames[key]||'';
    const p=pct(g.hits,g.count);
    const avgScore=g.hits>0?(g.scoreSum/g.hits).toFixed(3):'—';
    rows.push({key,gid:g.gid,name,total:g.count,hits:g.hits,misses:g.misses,pct:p,
               score:g.hits>0?g.scoreSum/g.hits:0,avgScore});
  });

  rows.sort((a,b)=>{
    let av=a[statsSortCol], bv=b[statsSortCol];
    if(typeof av==='string') av=av.toLowerCase(), bv=bv.toLowerCase();
    return statsSortCol==='name'?(av<bv?-1:1)*statsSortDir:(bv-av)*(-statsSortDir);
  });

  const tbody=document.getElementById('spBody');
  tbody.innerHTML='';
  rows.forEach(r=>{
    const tr=document.createElement('tr');
    const p=r.total?pct(r.hits,r.total):0;
    const pctColor=p>=70?'var(--hit)':p>=40?'var(--amber)':'var(--miss)';
    tr.innerHTML=`
      <td class="sp-name-cell${r.name?'':' unnamed'}">${esc(r.name||r.key.slice(0,60)+(r.key.length>60?'…':''))}</td>
      <td class="sp-num">${r.total}</td>
      <td class="sp-hit-num">${r.hits}</td>
      <td class="sp-miss-num">${r.misses}</td>
      <td class="sp-bar-cell"><div class="sp-mini-bar"><div class="sp-mini-fill" style="width:${p}%"></div></div></td>
      <td class="sp-pct" style="color:${pctColor}">${p}%</td>
      <td class="sp-score">${r.avgScore}</td>`;
    tr.onclick=()=>scrollToGroup(r.gid);
    tbody.appendChild(tr);
  });
}

function sortStats(col){
  if(statsSortCol===col){ statsSortDir*=-1; }
  else{ statsSortCol=col; statsSortDir=-1; }
  document.querySelectorAll('.sp-table th').forEach(th=>th.className='');
  const map={name:0,total:1,hits:2,misses:3,pct:5,score:6};
  const ths=document.querySelectorAll('.sp-table th');
  if(map[col]!==undefined) ths[map[col]].className=statsSortDir===-1?'sort-desc':'sort-asc';
  renderStatsPanel();
}

function scrollToGroup(gid){
  const el=document.querySelector(`tr[data-gh-gid="${gid}"]`);
  if(el) el.scrollIntoView({behavior:'smooth',block:'center'});
}

// ── LOADING OVERLAY ───────────────────────────────────────────────────────────
function showLoading(msg='Loading…'){
  document.getElementById('loadMsg').textContent=msg;
  document.getElementById('loadProg').style.width='0%';
  document.getElementById('loadSub').textContent='';
  document.getElementById('loadOverlay').classList.add('show');
}
function updateLoading(msg,pct=0,sub=''){
  document.getElementById('loadMsg').textContent=msg;
  document.getElementById('loadProg').style.width=pct+'%';
  document.getElementById('loadSub').textContent=sub;
}
function hideLoading(){
  document.getElementById('loadOverlay').classList.remove('show');
}
function yield_(){return new Promise(r=>setTimeout(r,0));}

// ── FILE LOAD ─────────────────────────────────────────────────────────────────
function makeTableHTML(){
  return `<div class="tw">
    <table>
      <colgroup>
        <col class="cs"><col class="cn"><col class="ct">
        <col class="ci"><col class="cc"><col class="ca"><col class="cb">
      </colgroup>
      <thead><tr>
        <th class="tc"><input type="checkbox" class="chk" id="chkAll" onchange="toggleAll(this)"></th>
        <th class="tc">#</th>
        <th>Timestamp</th>
        <th>Input</th>
        <th>Chain of Thought</th>
        <th>Answer</th>
        <th class="tc">Actions</th>
      </tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>`;
}

function onFileChange(){
  const f=document.getElementById('fileSelect').value;
  if(f===currentFile) return;
  currentFile=f; lastRow=0; allRecords=[];
  groupKeys.clear(); gidSeq=0; collapsed.clear();
  sysOpen.clear(); selected.clear(); catNames={};
  clearInterval(pollTimer);

  const statsBtn=document.getElementById('statsBtn');
  if(!f){
    document.getElementById('fbar').style.display='none';
    document.getElementById('main').innerHTML='<div class="empty"><div class="empty-ico">🗂</div><h4>No file selected</h4><p>Choose a .jsonl file above</p></div>';
    statsBtn.disabled=true;
    if(statsOpen) toggleStats();
    return;
  }
  statsBtn.disabled=false;
  document.getElementById('fbar').style.display='flex';
  loadCats();
  document.getElementById('main').innerHTML=makeTableHTML();
  fetchNew();
  pollTimer=setInterval(fetchNew, 8000);
}

async function reloadFile(){
  const f=currentFile;
  currentFile=''; lastRow=0; allRecords=[];
  groupKeys.clear(); gidSeq=0; collapsed.clear();
  sysOpen.clear(); selected.clear();
  currentFile=f;
  loadCats();
  document.getElementById('main').innerHTML=makeTableHTML();
  await fetchNew();
  if(statsOpen) renderStatsPanel();
}

async function fetchNew(){
  if(!currentFile) return;
  let data;
  try{ data=await fetch(`/api/records/${encodeURIComponent(currentFile)}?since=${lastRow}`).then(r=>r.json()); }
  catch(e){ hideLoading(); return; }
  if(!data.length) return;

  data.forEach(r=>{ allRecords.push(r); if(r._row>lastRow) lastRow=r._row; });

  const tbody=document.getElementById('tbody');
  if(!tbody) return;

  if(data.length>80){
    // Large batch: use chunked batch renderer with loading overlay
    await batchRenderAll(data, tbody);
  } else {
    // Small incremental update (polling)
    await appendRowsIncremental(data, tbody);
  }
  refreshStatus();
  if(statsOpen) renderStatsPanel();
}

// ── BATCH RENDERER (large initial loads) ──────────────────────────────────────
async function batchRenderAll(data, tbody){
  const CHUNK=80;
  showLoading('Indexing records…');
  await yield_();

  // Pass 1: build groupKeys from data (pure data, no DOM)
  const newGroups=[];
  for(const r of data){
    const key=getGroupKey(r);
    if(!groupKeys.has(key)){
      const gid='g'+(gidSeq++);
      const col=COLORS[(gidSeq-1)%COLORS.length];
      groupKeys.set(key,{gid,col,count:0,rows:[],hits:0,misses:0,scoreSum:0,clfCounts:{}});
      newGroups.push(key);
    }
    const grp=groupKeys.get(key);
    grp.count++; grp.rows.push(r._row);
    const hit=isHit(r);
    if(hit){grp.hits++;grp.scoreSum+=parseFloat(r.rag_score)||0;}else grp.misses++;
    const pred=(r.rag_collection_predicted||'').trim();
    if(pred) grp.clfCounts[pred]=(grp.clfCounts[pred]||0)+1;
  }

  updateLoading('Building groups…',5,`${groupKeys.size} groups found`);
  await yield_();

  // Pass 2: insert group headers for new groups
  const ghFrag=document.createDocumentFragment();
  for(const key of newGroups){
    const grp=groupKeys.get(key);
    const tr=document.createElement('tr');
    tr.setAttribute('data-is-gh','1');
    tr.setAttribute('data-gh-gid',grp.gid);
    const td=document.createElement('td');
    td.colSpan=7; td.className='gh-cell';
    td.innerHTML=buildGHHTML(key,grp.gid,grp.col,grp);
    tr.appendChild(td);
    ghFrag.appendChild(tr);
  }
  tbody.appendChild(ghFrag);

  // Pass 3: insert rows in chunks, each chunk yielding to browser
  // Build group→rows map preserving insertion order
  const groupRowMap=new Map();
  for(const r of data){
    const key=getGroupKey(r);
    const grp=groupKeys.get(key);
    if(!groupRowMap.has(grp.gid)) groupRowMap.set(grp.gid,[]);
    groupRowMap.get(grp.gid).push(r);
  }

  // Build gid → key reverse map for O(1) lookup
  const gidToKey=new Map();
  groupKeys.forEach((grp,key)=>gidToKey.set(grp.gid,key));

  // Insert rows group by group (before the next group header = natural order)
  let rendered=0;
  const groupEntries=[...groupRowMap.entries()];
  for(const [gid, rows] of groupEntries){
    const key=gidToKey.get(gid);
    const grp=groupKeys.get(key);
    const nextGH=findNextGroupHeaderByGid(tbody,gid);
    const hidden=collapsed.has(gid);
    let i=0;
    while(i<rows.length){
      const chunk=rows.slice(i,i+CHUNK);
      const frag=document.createDocumentFragment();
      for(const r of chunk){
        frag.appendChild(makeRowTR(r,grp,hidden));
        frag.appendChild(makeDetTR(r,key,hidden));
      }
      if(nextGH) tbody.insertBefore(frag,nextGH); else tbody.appendChild(frag);
      i+=CHUNK; rendered+=chunk.length;
      const pctDone=Math.round(10+85*rendered/data.length);
      updateLoading(`Rendering rows… ${rendered} / ${data.length}`,pctDone,`${Math.round(rendered/data.length*100)}% complete`);
      await yield_();
    }
  }

  updateLoading('Finalising…',97);
  await yield_();
  lucide.createIcons({nodes:[...tbody.querySelectorAll('[data-lucide]')]});
  applyFilter();
  hideLoading();
}

// ── INCREMENTAL APPEND (polling small batches) ────────────────────────────────
async function appendRowsIncremental(data, tbody){
  const changedKeys=new Set();
  for(const r of data){
    const key=getGroupKey(r);
    if(!groupKeys.has(key)){
      const gid='g'+(gidSeq++);
      const col=COLORS[(gidSeq-1)%COLORS.length];
      groupKeys.set(key,{gid,col,count:0,rows:[],hits:0,misses:0,scoreSum:0,clfCounts:{}});
      insertGroupHeader(tbody,key,gid,col);
    }
    const grp=groupKeys.get(key);
    grp.count++; grp.rows.push(r._row);
    const hit=isHit(r);
    if(hit){grp.hits++;grp.scoreSum+=parseFloat(r.rag_score)||0;}else grp.misses++;
    const pred=(r.rag_collection_predicted||'').trim();
    if(pred) grp.clfCounts[pred]=(grp.clfCounts[pred]||0)+1;
    changedKeys.add(key);

    const hidden=collapsed.has(grp.gid);
    const nextGH=findNextGroupHeader(tbody,grp.gid);
    const tr=makeRowTR(r,grp,hidden);
    const det=makeDetTR(r,key,hidden);
    if(nextGH){tbody.insertBefore(tr,nextGH);tbody.insertBefore(det,nextGH);}
    else{tbody.appendChild(tr);tbody.appendChild(det);}
  }
  // Refresh only changed group headers
  changedKeys.forEach(key=>refreshGroupHeader(key));
  lucide.createIcons({nodes:[...tbody.querySelectorAll('[data-lucide]')]});
  applyFilter();
}

async function initFiles(){
  const sel=document.getElementById('fileSelect'), cur=sel.value;
  const files=await fetch('/api/files').then(r=>r.json()).catch(()=>[]);
  sel.innerHTML='<option value="">— select file —</option>';
  files.forEach(f=>{ const o=document.createElement('option'); o.value=f; o.textContent=f; if(f===cur)o.selected=true; sel.appendChild(o); });
}

// ── ROW BUILDERS ─────────────────────────────────────────────────────────────
function makeRowTR(r,grp,hidden){
  const hit=isHit(r);
  const ts=(r.timestamp||'').replace('T',' ').slice(0,19);
  const ip=previewInput(r.input);
  const cp=r.cot?r.cot.slice(0,80).replace(/\n/g,' ')+(r.cot.length>80?'…':''):'';
  const ap=(r.answer||'').slice(0,80).replace(/\n/g,' ')+((r.answer||'').length>80?'…':'');
  const sel2=selected.has(r._row);
  const dotCls=hit?'on':'off';
  const tr=document.createElement('tr');
  tr.className='dr'+(hidden?' hid':'');
  tr.id='r-'+r._row;
  tr.setAttribute('data-gid',grp.gid);
  tr.style.borderLeft='3px solid '+grp.col.bdr;
  if(grp.col.rowBg) tr.style.background=grp.col.rowBg;
  tr.onclick=()=>toggleDet(r._row);
  tr.innerHTML=`
    <td class="tc" onclick="event.stopPropagation()">
      <input type="checkbox" class="chk" ${sel2?'checked':''} onchange="toggleSel(${r._row},this)">
    </td>
    <td class="tc"><span class="badge">${r._row}</span></td>
    <td class="ts">${esc(ts)}</td>
    <td><span class="prev pi"><span class="hit-dot ${dotCls}"></span>${esc(ip)}</span></td>
    <td><span class="prev ${cp?'pc':'pn'}">${cp?esc(cp):'—'}</span></td>
    <td><span class="prev pa">${esc(ap)}</span></td>
    <td class="tc" onclick="event.stopPropagation()">
      <div class="acts">
        <button class="ib" id="eb-${r._row}" onclick="toggleDet(${r._row})" title="expand">
          <i data-lucide="expand" class="icon-sm"></i>
        </button>
        <button class="ib" onclick="copyRow(${r._row})" title="copy JSON">
          <i data-lucide="clipboard" class="icon-sm"></i>
        </button>
      </div>
    </td>`;
  return tr;
}

function makeDetTR(r,key,hidden){
  const det=document.createElement('tr');
  det.className='det-row'+(hidden?' hid':'');
  det.id='d-'+r._row;
  det.style.display='none';
  const dtd=document.createElement('td');
  dtd.colSpan=7;
  dtd.innerHTML=detHTML(r,key);
  det.appendChild(dtd);
  return det;
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

function findNextGroupHeaderByGid(tbody,gid){
  return findNextGroupHeader(tbody,gid);
}

// ── GROUP HEADER ──────────────────────────────────────────────────────────────
function insertGroupHeader(tbody,key,gid,col){
  const tr=document.createElement('tr');
  tr.setAttribute('data-is-gh','1');
  tr.setAttribute('data-gh-gid',gid);
  const td=document.createElement('td');
  td.colSpan=7; td.className='gh-cell';
  td.innerHTML=buildGHHTML(key,gid,col,groupKeys.get(key)||{count:0,hits:0,misses:0,scoreSum:0,clfCounts:{}});
  tr.appendChild(td);
  tbody.appendChild(tr);
}

function buildGHHTML(key,gid,col,grp){
  const name=catNames[key]||'';
  const isOpen=sysOpen.has(gid);
  const isColl=collapsed.has(gid);
  const {count,hits,misses,clfCounts={}}=grp;
  const hitPct=count?pct(hits,count):0;
  const safeKey=encodeURIComponent(key);
  const avgScore=grp.hits>0?(grp.scoreSum/grp.hits).toFixed(3):'—';
  const pctColor=hitPct>=70?'var(--hit)':hitPct>=40?'var(--amber)':'var(--miss)';
  const groupNum=parseInt(gid.slice(1),10)+1;

  // Classifier breakdown pills — sorted by count desc, top entry highlighted
  const clfEntries=Object.entries(clfCounts).sort((a,b)=>b[1]-a[1]);
  const maxCnt=clfEntries[0]?.[1]||0;
  const clfPills=clfEntries.map(([c,n],i)=>{
    const isReject=/reject|low_conf|no_json|unknown|empty/i.test(c);
    const isTop=n===maxCnt && !isReject && i===0;
    const cls=isReject?'clf-reject':isTop?'clf-top':'';
    return `<span class="clf-tag${cls?` ${cls}`:''}" title="${esc(c)}">${esc(c.replace(/_/g,' '))} <b>${n}</b></span>`;
  }).join('');

  return `
  <div class="gh-wrap" style="background:${col.bg};border-left-color:${col.bdr}">
    <div class="gh-main">
      <div class="gh-collapse" onclick="toggleGroup('${gid}')">
        <span class="gh-num" style="background:${col.bdr}">${groupNum}</span>
        <span class="gh-chev${isColl?'':' open'}" id="chev-${gid}">
          <i data-lucide="chevron-right" class="icon"></i>
        </span>
        <span class="gh-name${name?'':' unnamed'}" style="color:${col.txt}" id="gname-${gid}">
          ${name?esc(name):'<span style="opacity:.45;font-weight:400;font-style:italic">unnamed — click ✏ to name</span>'}
        </span>
      </div>
      <div class="gh-hitbar-wrap" id="ghbar-${gid}">
        <span class="gh-row-count" id="gcnt-${gid}">${count} rows</span>
        <span class="gh-hit-nums">
          <span class="gh-hit-up" title="RAG hits">↑${hits}</span>
          <span class="gh-hit-dn" title="RAG misses">↓${misses}</span>
        </span>
        <div class="gh-bar"><div class="gh-bar-fill" id="gfill-${gid}" style="width:${hitPct}%"></div></div>
        <span class="gh-hit-pct" id="gpct-${gid}" style="color:${pctColor}">${count?hitPct+'%':'—'}</span>
        <span class="gh-avg-score" title="avg RAG score on hits">${avgScore}</span>
      </div>
      <div class="gh-actions">
        <button class="gab edit" style="color:${col.txt}" data-gid="${gid}" data-key="${safeKey}" onclick="handleNameBtn(this)">
          <i data-lucide="pencil" class="icon-sm"></i> name
        </button>
        <button class="gab" style="color:${col.txt}" id="pbtn-${gid}" onclick="toggleSys('${gid}')">
          <i data-lucide="terminal" class="icon-sm"></i> <span id="pbtntxt-${gid}">prompt</span>
        </button>
        <button class="gab del" onclick="openDelModal('${gid}','${safeKey}')">
          <i data-lucide="trash-2" class="icon-sm"></i>
        </button>
      </div>
    </div>
    ${clfPills?`
    <div class="gh-clf-row">
      <span class="gh-clf-label"><i data-lucide="cpu" class="icon-sm"></i> classifier</span>
      ${clfPills}
    </div>`:''}
    <div class="gh-panel" id="panel-${gid}"
      style="display:${isOpen?'block':'none'};border-left-color:${col.bdr}">${esc('User message starts with:\n'+key+(key.length>=120?'\n[truncated]':''))}</div>
  </div>`;
}

function refreshGroupHeader(key){
  const grp=groupKeys.get(key);
  if(!grp) return;
  const tbody=document.getElementById('tbody');
  if(!tbody) return;
  const ghRow=tbody.querySelector(`tr[data-gh-gid="${grp.gid}"]`);
  if(!ghRow) return;
  ghRow.querySelector('td').innerHTML=buildGHHTML(key,grp.gid,grp.col,grp);
  lucide.createIcons({nodes:[ghRow]});
}

// ── GROUP CONTROLS ────────────────────────────────────────────────────────────
function toggleGroup(gid){
  const tbody=document.getElementById('tbody');
  const rows=[...tbody.querySelectorAll(`[data-gid="${gid}"]`)];
  const chevEl=document.querySelector(`#chev-${gid}`);
  if(collapsed.has(gid)){
    collapsed.delete(gid);
    rows.forEach(r=>r.classList.remove('hid'));
    if(chevEl) chevEl.classList.add('open');
  } else {
    collapsed.add(gid);
    rows.forEach(r=>{
      r.classList.add('hid');
      const rid=r.id?.replace('r-','');
      if(rid&&!isNaN(rid)){ const d=document.getElementById('d-'+rid); if(d) d.style.display='none'; }
    });
    if(chevEl) chevEl.classList.remove('open');
  }
}

function toggleSys(gid){
  const panel=document.getElementById('panel-'+gid);
  const txtEl=document.getElementById('pbtntxt-'+gid);
  if(!panel) return;
  if(sysOpen.has(gid)){
    sysOpen.delete(gid); panel.style.display='none';
    if(txtEl) txtEl.textContent='prompt';
  } else {
    sysOpen.add(gid); panel.style.display='block';
    if(txtEl) txtEl.textContent='hide';
  }
}

function collapseAll(){
  groupKeys.forEach((_,key)=>{ const g=groupKeys.get(key); if(g&&!collapsed.has(g.gid)) toggleGroup(g.gid); });
}
function expandAll(){
  groupKeys.forEach((_,key)=>{ const g=groupKeys.get(key); if(g&&collapsed.has(g.gid)) toggleGroup(g.gid); });
}

// ── NAME MODAL ────────────────────────────────────────────────────────────────
let editingKey='';
function handleNameBtn(btn){
  const gid=btn.getAttribute('data-gid');
  const key=decodeURIComponent(btn.getAttribute('data-key'));
  editingKey=key;
  document.getElementById('nameInput').value=catNames[key]||'';
  document.getElementById('namePreview').textContent=key.slice(0,160)+(key.length>160?'…':'');
  document.getElementById('nameOverlay').style.display='flex';
  lucide.createIcons({nodes:[document.getElementById('nameOverlay')]});
  setTimeout(()=>document.getElementById('nameInput').focus(),50);
}
function closeNameModal(){ document.getElementById('nameOverlay').style.display='none'; editingKey=''; }
function saveGroupName(){
  const val=document.getElementById('nameInput').value.trim();
  if(val) catNames[editingKey]=val; else delete catNames[editingKey];
  persistCats();
  refreshGroupHeader(editingKey);
  closeNameModal();
  if(statsOpen) renderStatsPanel();
  toast(val?`Named: "${val}"`:'Name cleared','g');
}
function clearGroupName(){ document.getElementById('nameInput').value=''; }

// ── DELETE MODAL ──────────────────────────────────────────────────────────────
function openDelModal(gid, safeKey){
  const key=decodeURIComponent(safeKey);
  const grp=groupKeys.get(key);
  if(!grp) return;
  pendingDelete={key,gid,rows:[...grp.rows]};
  const name=catNames[key]||key.slice(0,80)+(key.length>80?'…':'');
  document.getElementById('delInfo').innerHTML=
    `<b>${grp.count} rows</b> from group:<br><span style="font-family:var(--mono);font-size:11px">${esc(name)}</span><br><br>`+
    `↑ ${grp.hits} hits &nbsp; ↓ ${grp.misses} misses &nbsp; ${pct(grp.hits,grp.count)}% hit rate`;
  document.getElementById('delFilename').textContent=currentFile;
  document.getElementById('delOverlay').style.display='flex';
  lucide.createIcons({nodes:[document.getElementById('delOverlay')]});
}
function closeDelModal(){ document.getElementById('delOverlay').style.display='none'; }

async function confirmDelete(){
  if(!pendingDelete.rows.length) return;
  const btn=document.getElementById('delConfirmBtn');
  btn.textContent='Deleting…'; btn.disabled=true;
  try{
    const res=await fetch('/api/delete_rows',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({filename:currentFile, rows:pendingDelete.rows})
    });
    const j=await res.json();
    if(j.status==='ok'){
      toast(`Deleted ${j.deleted} rows (${j.remaining} remaining)`,'g');
      closeDelModal();
      await reloadFile();
    } else { toast('Delete failed: '+j.message,'r'); }
  }catch(e){ toast('Delete error: '+e,'r'); }
  finally{
    btn.innerHTML='<i data-lucide="trash-2" class="icon-sm"></i> Delete';
    btn.disabled=false;
    lucide.createIcons({nodes:[btn]});
    pendingDelete={key:null,gid:null,rows:[]};
  }
}

// ── SAVE MODAL ────────────────────────────────────────────────────────────────
function openSaveModal(){
  document.getElementById('saveOverlay').style.display='flex';
  lucide.createIcons({nodes:[document.getElementById('saveOverlay')]});
  setTimeout(()=>document.getElementById('saveFile').focus(),50);
}
function closeSaveModal(){ document.getElementById('saveOverlay').style.display='none'; }
async function doSave(){
  const fn=document.getElementById('saveFile').value.trim()||'processed_dataset.jsonl';
  const records=allRecords.map(r=>{ const key=getGroupKey(r); return {...r,category:catNames[key]||key}; });
  const res=await fetch('/api/save_processed',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:fn,records})});
  const j=await res.json();
  closeSaveModal();
  toast(`Saved ${j.count} records → ${j.path}`,'g');
  setTimeout(initFiles,600);
}

// ── ROW DETAIL ────────────────────────────────────────────────────────────────
function toggleDet(row){
  const det=document.getElementById('d-'+row);
  const rowEl=document.getElementById('r-'+row);
  const btn=document.getElementById('eb-'+row);
  if(!det) return;
  const open=det.style.display!=='none';
  det.style.display=open?'none':'table-row';
  rowEl?.classList.toggle('exp',!open);
  if(btn) btn.classList.toggle('on',!open);
  if(!open) lucide.createIcons({nodes:[det]});
}

function detHTML(r,key){
  const u=r.usage||{}, id=r._row;
  const cat=catNames[key]||'(unnamed)';
  const pf=[
    ['category',cat],['model',r.model],
    ['temperature',r.temperature],['max_tokens',r.max_tokens],
    ['top_p',r.top_p],['seed',r.seed],['stream',r.stream],
  ].filter(([,v])=>v!==undefined&&v!==null&&v!=='');
  const uf=[
    ['prompt_tokens',r.prompt_tokens??u.prompt_tokens],
    ['completion_tokens',r.completion_tokens??u.completion_tokens],
    ['total_tokens',r.total_tokens??u.total_tokens],
  ].filter(([,v])=>v!==undefined&&v!==null&&v!=='');

  return `<div>
    <div class="det-grid">
      <div class="det-col">
        <div class="det-hdr">
          <div class="lbl li"><i data-lucide="message-square" class="icon-sm"></i> Input</div>
          <button class="cpb" id="cb-i-${id}" onclick="cpCell('input',${id})">
            <i data-lucide="clipboard" class="icon-sm"></i> copy
          </button>
        </div>
        ${renderInput(r.input)}
      </div>
      <div class="det-col">
        <div class="det-hdr">
          <div class="lbl lc"><i data-lucide="brain" class="icon-sm"></i> Chain of Thought</div>
          ${r.cot?`<button class="cpb" id="cb-c-${id}" onclick="cpCell('cot',${id})"><i data-lucide="clipboard" class="icon-sm"></i> copy</button>`:''}
        </div>
        ${r.cot?`<div class="dc dcc">${esc(r.cot)}</div>`:'<div class="no-c">No chain of thought recorded</div>'}
      </div>
      <div class="det-col">
        <div class="det-hdr">
          <div class="lbl la"><i data-lucide="check-circle" class="icon-sm"></i> Answer</div>
          <button class="cpb" id="cb-a-${id}" onclick="cpCell('answer',${id})">
            <i data-lucide="clipboard" class="icon-sm"></i> copy
          </button>
        </div>
        <div class="dc da">${esc(r.answer||'')}</div>
      </div>
    </div>
    <div class="meta-grid">
      <div class="ms">
        <div class="mt"><i data-lucide="settings" class="icon-sm"></i> Parameters</div>
        ${pf.map(([k,v])=>`<div class="mr2"><span class="mk">${k}</span><span class="mv">${esc(String(v))}</span></div>`).join('')}
      </div>
      <div class="ms">
        <div class="mt"><i data-lucide="zap" class="icon-sm"></i> Token Usage</div>
        ${uf.map(([k,v])=>`<div class="mr2"><span class="mk">${k}</span><span class="mv">${esc(String(v))}</span></div>`).join('')}
      </div>
    </div>
    ${ragHTML(r,id)}
  </div>`;
}

// ── RAG PANEL ─────────────────────────────────────────────────────────────────
function ragHTML(r,id){
  const hasRag=r.rag_hit!==undefined||r.clf_outcome!==undefined||r.rag_score!==undefined;
  if(!hasRag) return '';

  const hit=isHit(r);
  const score=parseFloat(r.rag_score)||0;
  const threshold=parseFloat(r.rag_threshold)||0;
  const scoreHi=score>=threshold;

  const clfOutcome=r.clf_outcome||'—';
  const clfConf=r.clf_confidence!==undefined?Number(r.clf_confidence).toFixed(4):'—';
  const clfMode=r.clf_mode||'—';
  const clfPred=r.rag_collection_predicted||'—';
  const clfReasoning=r.clf_reasoning||'';
  const clfJson=r.clf_raw_output||'';

  let outcomeClass='unk';
  if(clfOutcome.startsWith('OK')) outcomeClass='ok';
  else if(/REJECT|LOW_CONF|UNKNOWN|NO_JSON|EMPTY/.test(clfOutcome)) outcomeClass='bad';
  else if(/DISABLED|PARALLEL/.test(clfOutcome)) outcomeClass='skip';

  const ragMatch=r.rag_collection_matched||'—';
  const ragMiss=r.rag_miss_reason||'';
  const ragSub=r.rag_subset||'—';
  const ragOrig=r.rag_original_name||'—';
  const ragDs=r.rag_dataset_name||'—';
  const ragCat=r.rag_category||'—';
  const ragCached=r.rag_cached_answer||'';
  const ragPassage=r.rag_passage_text||'';
  const refBlock=r.rag_reference_injected||'';
  const upStatus=r.upstream_status??'—';
  const latency=r.latency_ms!==undefined?r.latency_ms+'ms':'—';
  const respRaw=r.response_content_raw||'';
  const respReason=r.response_reasoning||r.cot||'';
  const sumLabel=hit?'Reference injected into prompt':(ragMiss?`Miss — ${ragMiss}`:'No match found');

  return `
  <div class="rag-panel">
    <div class="rag-sum ${hit?'hit':'miss'}">
      <span class="rag-badge ${hit?'hit':'miss'}">
        <i data-lucide="${hit?'check':'x'}" class="icon-sm"></i>
        ${hit?'HIT':'MISS'}
      </span>
      <span class="clf-pill ${outcomeClass}">${esc(clfOutcome)}</span>
      <span class="rag-sum-txt">${esc(sumLabel)}</span>
      ${score?`<span class="rag-score-txt" style="color:${scoreHi?'var(--hit)':'var(--miss)'}">score ${score.toFixed(4)} / ${threshold}</span>`:''}
      <button class="rag-toggle-btn" onclick="toggleRagBody(${id})">
        <i data-lucide="cpu" class="icon-sm"></i> pipeline
      </button>
    </div>
    <div id="rb-${id}" style="display:none">
      <div class="rag-g4">
        <div class="rag-col">
          <div class="rag-hdr"><i data-lucide="cpu" class="icon-sm"></i> Classifier</div>
          <div class="rag-kv"><span class="rag-k">mode</span><span class="rag-v">${esc(clfMode)}</span></div>
          <div class="rag-kv"><span class="rag-k">outcome</span><span class="rag-v">${esc(clfOutcome)}</span></div>
          <div class="rag-kv"><span class="rag-k">confidence</span><span class="rag-v">${esc(clfConf)}</span></div>
          <div class="rag-kv"><span class="rag-k">predicted collection</span><span class="rag-v">${esc(clfPred)}</span></div>
          ${clfReasoning?`<div style="margin-top:10px"><div class="rag-hdr"><i data-lucide="brain" class="icon-sm"></i> reasoning</div><div class="rag-blk think">${esc(clfReasoning)}</div></div>`:'<div class="rag-none" style="margin-top:8px">No reasoning — returned JSON only</div>'}
          ${clfJson?`<div style="margin-top:8px"><div class="rag-hdr"><i data-lucide="code-2" class="icon-sm"></i> output JSON</div><div class="rag-blk raw">${esc(clfJson)}</div></div>`:''}
        </div>
        <div class="rag-col">
          <div class="rag-hdr"><i data-lucide="database" class="icon-sm"></i> Vector DB</div>
          <div class="rag-kv"><span class="rag-k">matched collection</span><span class="rag-v">${esc(ragMatch)}</span></div>
          <div class="rag-kv"><span class="rag-k">similarity score</span>
            <span class="rag-v ${scoreHi?'hi':'lo'}">${score.toFixed(6)} <span style="font-weight:400;color:var(--txt3)">(thresh ${threshold})</span></span>
          </div>
          <div class="rag-kv"><span class="rag-k">subset</span><span class="rag-v">${esc(ragSub)}</span></div>
          <div class="rag-kv"><span class="rag-k">source</span><span class="rag-v">${esc(ragOrig)}</span></div>
          <div class="rag-kv"><span class="rag-k">dataset</span><span class="rag-v">${esc(ragDs)}</span></div>
          <div class="rag-kv"><span class="rag-k">category</span><span class="rag-v">${esc(ragCat)}</span></div>
          ${ragMiss?`<div class="rag-kv"><span class="rag-k">miss reason</span><span class="rag-v mr">${esc(ragMiss)}</span></div>`:''}
          ${ragCached?`<div style="margin-top:10px"><div class="rag-hdr"><i data-lucide="bookmark" class="icon-sm"></i> cached answer</div><div class="rag-blk pas" style="max-height:90px">${esc(ragCached)}</div></div>`:''}
          ${ragPassage?`<div style="margin-top:8px"><div class="rag-hdr"><i data-lucide="file-text" class="icon-sm"></i> passage text</div><div class="rag-blk pas">${esc(ragPassage)}</div></div>`:''}
        </div>
        <div class="rag-col">
          <div class="rag-hdr"><i data-lucide="paperclip" class="icon-sm"></i> Injected Block</div>
          ${refBlock?`
            <div style="font-family:var(--mono);font-size:10px;color:var(--txt3);margin-bottom:8px">
              Exact block prepended to the user message before inference.
            </div>
            <button class="cpb" id="cb-ref-${id}" onclick="cpRef(${id})" style="margin-bottom:8px">
              <i data-lucide="clipboard" class="icon-sm"></i> copy block
            </button>
            <div class="rag-blk inj">${esc(refBlock)}</div>
          `:`<div class="rag-none">${hit?'Reference field empty.':'No reference injected (miss — prompt forwarded unchanged).'}</div>`}
        </div>
        <div class="rag-col">
          <div class="rag-hdr"><i data-lucide="send" class="icon-sm"></i> Model Response</div>
          <div class="rag-kv"><span class="rag-k">upstream HTTP</span><span class="rag-v">${esc(String(upStatus))}</span></div>
          <div class="rag-kv"><span class="rag-k">latency</span><span class="rag-v">${esc(latency)}</span></div>
          ${respReason?`<div style="margin-top:10px"><div class="rag-hdr"><i data-lucide="brain" class="icon-sm"></i> reasoning / CoT</div><div class="rag-blk cot">${esc(respReason)}</div></div>`:''}
          ${respRaw&&respRaw!==(r.answer||'')?`<div style="margin-top:8px"><div class="rag-hdr"><i data-lucide="code" class="icon-sm"></i> raw content</div><div class="rag-blk raw">${esc(respRaw)}</div></div>`:'<div class="rag-none" style="margin-top:8px">Raw = answer (no stripping)</div>'}
        </div>
      </div>
    </div>
  </div>`;
}

function toggleRagBody(id){
  const body=document.getElementById('rb-'+id);
  const btn=body?.previousElementSibling?.querySelector('.rag-toggle-btn');
  if(!body) return;
  const open=body.style.display!=='none';
  body.style.display=open?'none':'block';
  if(!open) lucide.createIcons({nodes:[body]});
  if(btn) btn.innerHTML=`<i data-lucide="${open?'cpu':'x'}" class="icon-sm"></i> ${open?'pipeline':'hide'}`;
  if(btn) lucide.createIcons({nodes:[btn]});
}

function cpRef(id){
  const r=allRecords.find(x=>x._row===id);
  if(!r?.rag_reference_injected){ toast('No reference block'); return; }
  navigator.clipboard.writeText(r.rag_reference_injected).then(()=>{
    const btn=document.getElementById('cb-ref-'+id);
    if(btn){ btn.innerHTML='<i data-lucide="check" class="icon-sm"></i> copied'; btn.classList.add('ok'); lucide.createIcons({nodes:[btn]}); setTimeout(()=>{ btn.innerHTML='<i data-lucide="clipboard" class="icon-sm"></i> copy block'; btn.classList.remove('ok'); lucide.createIcons({nodes:[btn]}); },1800); }
    toast('Reference copied','g');
  });
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
      let c=u?u.content:(msgs[0]?.content||'');
      const marker='ACTUAL CASE — evaluate this and only this';
      const mi=c.indexOf(marker);
      if(mi!==-1) c=c.slice(mi+marker.length);
      const line=c.split('\n').map(l=>l.trim()).find(l=>l&&!l.startsWith('='))||c;
      return line.slice(0,90)+(line.length>90?'…':'');
    }
  }catch{}
  return (raw||'').slice(0,90)+((raw||'').length>90?'…':'');
}

// ── SELECTION ─────────────────────────────────────────────────────────────────
function toggleSel(row,cb){
  if(cb.checked) selected.add(row); else selected.delete(row);
  document.getElementById('r-'+row)?.classList.toggle('sel',cb.checked);
  refreshStatus(); updateBulk();
}
function toggleAll(master){
  allRecords.forEach(r=>{
    if(master.checked) selected.add(r._row); else selected.delete(r._row);
    const el=document.getElementById('r-'+r._row);
    const cb=el?.querySelector('.chk');
    el?.classList.toggle('sel',master.checked);
    if(cb) cb.checked=master.checked;
  });
  refreshStatus(); updateBulk();
}
function selAll(){ const m=document.getElementById('chkAll'); if(m){m.checked=true;toggleAll(m);} }
function clearSel(){ const m=document.getElementById('chkAll'); if(m){m.checked=false;toggleAll(m);} }
function updateBulk(){
  const n=selected.size;
  document.getElementById('bulk').style.display=n>0?'flex':'none';
  document.getElementById('bulk-n').textContent=n+' selected';
}

// ── COPY / EXPORT ─────────────────────────────────────────────────────────────
function cpCell(field,rowId){
  const r=allRecords.find(x=>x._row===rowId); if(!r) return;
  let val=r[field]||'';
  if(field==='input'){ try{const m=JSON.parse(val);if(Array.isArray(m))val=m.map(x=>`[${x.role}]\n${x.content}`).join('\n\n');}catch{} }
  navigator.clipboard.writeText(val).then(()=>{
    const pfx={'input':'i','cot':'c','answer':'a'}[field]||field[0];
    const btn=document.getElementById(`cb-${pfx}-${rowId}`);
    if(btn){ btn.innerHTML='<i data-lucide="check" class="icon-sm"></i> copied'; btn.classList.add('ok'); lucide.createIcons({nodes:[btn]}); setTimeout(()=>{ btn.innerHTML='<i data-lucide="clipboard" class="icon-sm"></i> copy'; btn.classList.remove('ok'); lucide.createIcons({nodes:[btn]}); },1800); }
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
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='export.jsonl'; a.click();
  toast('Exported '+rows.length+' rows','g');
}
function exportSel(){ exportVisible(); }

// ── KEYBOARD ──────────────────────────────────────────────────────────────────
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    closeNameModal(); closeSaveModal(); closeDelModal(); clearSel();
    if(statsOpen) toggleStats();
  }
  if((e.ctrlKey||e.metaKey)&&e.key==='a'&&document.activeElement.tagName!=='INPUT'){e.preventDefault();selAll();}
  if((e.ctrlKey||e.metaKey)&&e.key==='c'&&selected.size>0&&document.activeElement.tagName!=='INPUT'){e.preventDefault();copySelJSON();}
  if(document.getElementById('nameOverlay').style.display!=='none'&&e.key==='Enter'){e.preventDefault();saveGroupName();}
  if(document.getElementById('saveOverlay').style.display!=='none'&&e.key==='Enter'){e.preventDefault();doSave();}
});

// ── INIT ──────────────────────────────────────────────────────────────────────
document.documentElement.setAttribute('data-theme', darkMode?'dark':'light');
lucide.createIcons();
// set correct theme icon after icons are created
(function(){
  const btn=document.getElementById('themeBtn');
  if(btn){btn.innerHTML=`<i data-lucide="${darkMode?'moon':'sun'}" class="icon"></i>`;lucide.createIcons({nodes:[btn]});}
})();
initFiles();
setInterval(initFiles, 30000);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=VIEWER_PORT, debug=False)
