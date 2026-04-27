# inference-capture

A two-part toolkit for capturing and browsing LLM inference data from any vLLM-compatible server.

- **`vllm_proxy.py`** — FastAPI reverse proxy that transparently forwards requests while logging every (input, chain-of-thought, answer) triple to disk.
- **`viewer.py`** — Flask web app with a rich single-page UI for browsing, filtering, and exporting the captured dataset.

---

## How it works

```
Client  →  vllm_proxy (port 8080)  →  vLLM server (any host)
                   ↓
            data/dataset.jsonl
            data/dataset.csv
                   ↑
            viewer.py (port 8003)
```

The proxy intercepts `/v1/chat/completions` and `/v1/completions` requests, enforces a fixed set of generation parameters, injects a system prompt when none is present, and extracts chain-of-thought from either:

- Dedicated `reasoning` / `reasoning_content` delta fields (e.g. QwQ, DeepSeek-R1 variants), or
- Inline `<think>…</think>` tags in the content stream.

Everything else is forwarded verbatim.

---

## Quick start

```bash
pip install -r requirements.txt

# Start the proxy (set VLLM_BASE_URL to your vLLM server)
VLLM_BASE_URL=http://your-vllm-host:8000 uvicorn vllm_proxy:app --port 8080

# In a second terminal, start the viewer
python viewer.py
# Open http://localhost:8003
```

Point your client at `http://localhost:8080` instead of the vLLM server directly.

---

## Configuration

All proxy settings are read from environment variables:

| Variable | Default | Description |
|---|---|---|
| `VLLM_BASE_URL` | `http://localhost:8000` | Upstream vLLM server URL |
| `LOG_LEVEL` | `INFO` | Python logging level |

Generation parameters enforced on every completion request are defined in `ENFORCE_PARAMS` at the top of `vllm_proxy.py`. The system prompts (`SYSTEM_PROMPT` / `SYSTEM_PROMPT_NO_THINK`) are also plain string constants — edit them to suit your use case.

---

## Output format

Each captured record is appended to two files in `data/`:

**`dataset.jsonl`** — one JSON object per line:
```json
{
  "timestamp": "2024-01-01T12:00:00",
  "row": 1,
  "model": "model-name",
  "input": "[{\"role\":\"user\",\"content\":\"...\"}]",
  "cot": "chain-of-thought text",
  "answer": "final answer",
  "prompt_tokens": 128,
  "completion_tokens": 256,
  "total_tokens": 384,
  "params": { "temperature": 1.0, "max_tokens": 16384 },
  "usage": { "prompt_tokens": 128, "completion_tokens": 256 }
}
```

**`dataset.csv`** — same fields in tabular form, one row per record.

---

## Dataset viewer

Open `http://localhost:8003` after starting `viewer.py`.

Features:
- Browse any `.jsonl` file in `data/` from a dropdown
- Filter by: all / has CoT / no CoT, plus free-text search across input, CoT, and answer
- Expand any row in-place to see full input (with per-role message blocks), CoT, and answer
- View request params and token usage per record
- Select multiple rows and copy as JSONL or export to a file
- Keyboard shortcuts: `Esc` clear selection, `Ctrl+A` select all visible, `Ctrl+C` copy selected
- Auto-refreshes the current file every 10 seconds

---

## Repetition detection

Long streaming outputs from reasoning models can sometimes enter character-level repetition loops. The proxy detects this by checking the last 60 characters of accumulated CoT — if the unique character count drops to 3 or fewer, it truncates and stops accumulating. This prevents runaway outputs from inflating your dataset.

---

## License

MIT
