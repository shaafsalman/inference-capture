import json
import csv
import httpx
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from pydantic_settings import BaseSettings
from datetime import datetime

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
DATASET_FILE = os.path.join(DATA_DIR, "dataset.csv")
DATASET_JSON_FILE = os.path.join(DATA_DIR, "dataset.jsonl")

row_counter = 0

ENFORCE_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "repetition_penalty": 1.05,
    "max_tokens": 8000,
}

THINKING_TOKEN_THRESHOLD = 1500

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Think briefly before answering — keep your reasoning concise. "
    "Go directly to the answer once you know it."
)
SYSTEM_PROMPT_NO_THINK = "You are a helpful AI assistant."

THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"

REPEAT_WINDOW = 60
REPEAT_UNIQUE_THRESHOLD = 3

CSV_FIELDS = [
    "timestamp", "row", "model", "input", "cot", "answer",
    "prompt_tokens", "completion_tokens", "total_tokens",
    "temperature", "max_tokens", "top_p", "frequency_penalty",
    "presence_penalty", "stop", "seed", "stream",
]


class Settings(BaseSettings):
    vllm_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"


settings = Settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vllm_proxy")

http_client: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=600.0)
    yield
    await http_client.aclose()


app = FastAPI(title="inference-capture proxy", lifespan=lifespan)


def is_looping(text: str) -> bool:
    if len(text) < REPEAT_WINDOW:
        return False
    tail = text[-REPEAT_WINDOW:]
    return len(set(tail)) <= REPEAT_UNIQUE_THRESHOLD


def clean_cot(text: str) -> str:
    if not text:
        return text
    lines = text.splitlines()
    clean = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 10 and len(set(stripped)) <= REPEAT_UNIQUE_THRESHOLD:
            logger.warning(f"Repetition loop detected, truncating CoT at: {repr(stripped[:40])}")
            break
        clean.append(line)
    return "\n".join(clean).strip()


def split_cot_and_answer(text: str) -> tuple[str, str]:
    if THINK_CLOSE in text:
        parts = text.split(THINK_CLOSE, 1)
        cot = parts[0].replace(THINK_OPEN, "").strip()
        answer = parts[1].strip()
        return cot, answer
    return "", text.strip()


def extract_cot_and_answer(reasoning: str, content: str) -> tuple[str, str]:
    reasoning = (reasoning or "").strip()
    content = (content or "").strip()
    if reasoning:
        return clean_cot(reasoning), content
    if THINK_CLOSE in content:
        if not content.startswith(THINK_OPEN):
            content = THINK_OPEN + content
        cot, answer = split_cot_and_answer(content)
        return clean_cot(cot), answer
    return "", content


def process_completion_response(data: dict) -> tuple[dict, str, str]:
    cot, answer = "", ""
    for choice in data.get("choices", []):
        if "message" in choice:
            msg = choice["message"]
            reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
            content = msg.get("content") or ""
            cot, answer = extract_cot_and_answer(reasoning, content)
            msg["content"] = answer
            msg.pop("reasoning", None)
            msg.pop("reasoning_content", None)
        elif "text" in choice:
            cot, answer = extract_cot_and_answer("", choice.get("text") or "")
            choice["text"] = answer
    return data, cot, answer


def estimate_tokens(body: dict) -> int:
    text = extract_input_text(body)
    return len(text) // 4


def enforce_request(body: dict) -> dict:
    body = dict(body)
    for k, v in ENFORCE_PARAMS.items():
        body[k] = v

    large_prompt = estimate_tokens(body) > THINKING_TOKEN_THRESHOLD

    if large_prompt:
        body["chat_template_kwargs"] = {"enable_thinking": False}
        body["temperature"] = 0.7
        body["top_p"] = 0.8
        body["repetition_penalty"] = 1.05
        system = SYSTEM_PROMPT_NO_THINK
        logger.info(f"Large prompt ({estimate_tokens(body)} est. tokens) — thinking disabled")
    else:
        body["chat_template_kwargs"] = {"enable_thinking": True}
        system = SYSTEM_PROMPT

    if "messages" in body:
        has_system = any(m.get("role") == "system" for m in body["messages"])
        if not has_system:
            body["messages"] = [{"role": "system", "content": system}] + body["messages"]
    return body


def extract_input_text(body: dict) -> str:
    if "messages" in body:
        return json.dumps(body["messages"])
    return body.get("prompt", "")


def extract_request_params(body: dict) -> dict:
    skip = {"messages", "prompt", "stream"}
    return {k: v for k, v in body.items() if k not in skip and v is not None}


def save_pair(input_text: str, cot: str, answer: str, params: dict, usage: dict) -> int:
    global row_counter
    row_counter += 1
    idx = row_counter
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "row": idx,
        "model": params.get("model", ""),
        "input": input_text,
        "cot": cot,
        "answer": answer,
        "prompt_tokens": usage.get("prompt_tokens", ""),
        "completion_tokens": usage.get("completion_tokens", ""),
        "total_tokens": usage.get("total_tokens", ""),
        "temperature": params.get("temperature", ""),
        "max_tokens": params.get("max_tokens", ""),
        "top_p": params.get("top_p", ""),
        "frequency_penalty": params.get("frequency_penalty", ""),
        "presence_penalty": params.get("presence_penalty", ""),
        "stop": json.dumps(params.get("stop")) if params.get("stop") is not None else "",
        "seed": params.get("seed", ""),
        "stream": params.get("stream", False),
    }
    file_exists = os.path.isfile(DATASET_FILE)
    with open(DATASET_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    with open(DATASET_JSON_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({**row, "params": params, "usage": usage}) + "\n")
    return idx


def log_pair(endpoint: str, body: dict, cot: str, answer: str, row_idx: int):
    D, d = "=" * 72, "-" * 72
    logger.info(f"{D}\n  ROW #{row_idx}  |  {endpoint}\n{D}")
    logger.info(f"  INPUT\n{d}")
    if "messages" in body:
        for msg in body["messages"]:
            logger.info(f"  [{msg.get('role', '?').upper()}]")
            for line in (msg.get("content") or "").splitlines():
                logger.info(f"  {line}")
    else:
        for line in body.get("prompt", "").splitlines():
            logger.info(f"  {line}")
    if cot:
        logger.info(f"{D}\n  <think>\n{d}")
        for line in cot.splitlines():
            logger.info(f"  {line}")
        logger.info(f"{d}\n  </think>")
    logger.info(f"{D}\n  OUTPUT\n{d}")
    for line in answer.splitlines():
        logger.info(f"  {line}")
    logger.info(D)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    url = f"{settings.vllm_base_url}/{path}"
    body = None
    body_bytes = await request.body()
    if body_bytes:
        try:
            body = json.loads(body_bytes)
        except json.JSONDecodeError:
            body = {}

    is_completion = path in ["v1/completions", "v1/chat/completions"]
    is_streaming = body and body.get("stream", False)

    if is_completion and body:
        body = enforce_request(body)
        body_bytes = json.dumps(body).encode()

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    if is_streaming and is_completion:
        return await handle_streaming(http_client, request.method, url, headers, body_bytes, body, path)

    response = await http_client.request(
        method=request.method, url=url, headers=headers, content=body_bytes
    )

    if response.status_code != 200:
        logger.error(f"Upstream {response.status_code}: {response.text}")

    if is_completion and response.status_code == 200:
        try:
            data = response.json()
            processed, cot, answer = process_completion_response(data)
            if body:
                row_idx = save_pair(
                    extract_input_text(body), cot, answer,
                    extract_request_params(body), processed.get("usage") or {}
                )
                log_pair(path, body, cot, answer, row_idx)
            resp_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")
            }
            return Response(
                content=json.dumps(processed), status_code=response.status_code,
                headers=resp_headers, media_type="application/json"
            )
        except json.JSONDecodeError:
            pass

    resp_headers = {
        k: v for k, v in response.headers.items()
        if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")
    }
    return Response(content=response.content, status_code=response.status_code, headers=resp_headers)


async def handle_streaming(
    client: httpx.AsyncClient, method: str, url: str,
    headers: dict, body: bytes, body_parsed: dict, path: str,
):
    accumulated_cot = ""
    accumulated_answer = ""
    using_reasoning_parser = False
    inline_buffer = ""
    cot_done = False
    stream_usage = {}

    async def generate():
        nonlocal accumulated_cot, accumulated_answer, using_reasoning_parser
        nonlocal inline_buffer, cot_done

        async with client.stream(method, url, headers=headers, content=body) as response:
            async for line in response.aiter_lines():
                if not line.strip():
                    yield f"{line}\n"
                    continue
                if not line.startswith("data: "):
                    yield f"{line}\n"
                    continue

                data_str = line[6:]

                if data_str.strip() == "[DONE]":
                    if body_parsed:
                        if not using_reasoning_parser and not cot_done and inline_buffer:
                            accumulated_answer = inline_buffer
                        final_cot = clean_cot(accumulated_cot.strip())
                        final_answer = accumulated_answer.strip()
                        row_idx = save_pair(
                            extract_input_text(body_parsed), final_cot, final_answer,
                            extract_request_params(body_parsed), stream_usage
                        )
                        log_pair(path, body_parsed, final_cot, final_answer, row_idx)
                    yield f"{line}\n"
                    continue

                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    yield f"{line}\n"
                    continue

                if "usage" in data and data["usage"]:
                    stream_usage.update(data["usage"])

                if "choices" not in data or not data["choices"]:
                    yield f"{line}\n"
                    continue

                choice = data["choices"][0]
                delta = choice.get("delta", {})
                reasoning_chunk = delta.get("reasoning") or delta.get("reasoning_content") or ""
                content_chunk = delta.get("content") or choice.get("text") or ""

                if reasoning_chunk:
                    using_reasoning_parser = True
                    if not is_looping(accumulated_cot):
                        accumulated_cot += reasoning_chunk
                    continue

                if not content_chunk:
                    yield f"{line}\n"
                    continue

                if using_reasoning_parser:
                    accumulated_answer += content_chunk
                    yield f"data: {json.dumps(data)}\n"
                    continue

                if not cot_done:
                    inline_buffer += content_chunk
                    if THINK_CLOSE in inline_buffer:
                        cot_done = True
                        cot_part, answer_part = split_cot_and_answer(inline_buffer)
                        accumulated_cot = cot_part
                        inline_buffer = ""
                        if answer_part:
                            accumulated_answer += answer_part
                            if "delta" in choice:
                                choice["delta"]["content"] = answer_part
                            else:
                                choice["text"] = answer_part
                            yield f"data: {json.dumps(data)}\n"
                    continue

                accumulated_answer += content_chunk
                yield f"data: {json.dumps(data)}\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
