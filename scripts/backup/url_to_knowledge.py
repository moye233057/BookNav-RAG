# -*- coding: utf-8 -*-
"""
把任意 URL / 本地文件变成可检索 kv 列表。

状态：KV 实验，还没接进流程。线上主路径与 tests 都不 import 本文件；它只写 `data/result/kv/`
      和 KV 存储预留实现 `offline/store/kv_store.py`，不进抽取 entrance、不进检索（ADR-0005、ADR-0030）。
      公开版不保留 KV 实验时，`scripts/backup/` 可整个删掉，其余功能不受影响。

职责：KV 实验脚本。anyurl2text 抽原文。PIPELINE=text 接到向量层分块与向量库；PIPELINE=knowledge 抽 KV。
      生产入库走 scripts/ingest.py。本文件不在抽取层。
      分块调 offline.vector.chunk。
      不问答。
步骤：
  1. step1_extract_text — POST /extract 或 /extract/file → kv/step1_extract_response.json
  2. step2_write_extracted — 扫 URL → kv/step2_extracted.txt
     PIPELINE=text：可分块原文 + 向量层写入 data/lancedb
  3. step3_split_chunks — 按 kind 分块（调用 offline.vector.chunk）；仅 knowledge
  4. step4_atomic_extract — 每块 LLM 原子化
  5. step5_fill_missing_urls — 补漏 URL → kv/step5_atomic_chunks.json
  6. step6_retrieve_rebuild — 每块 LLM 检索重组 → kv/step6_retrieve_rows.json
  7. step7_write_kv — rows → kv/step7_knowledge_kv.json 与 kv/kv_store.json
产出：
  data/result/kv/step1_extract_response.json
  data/result/kv/step2_extracted.txt
  data/result/<source>/chunkable_source.json（text）
  data/result/kv/step7_knowledge_kv.json
  data/result/kv/kv_store.json
前置：anyurl2text 已起；DEEPSEEK_API_KEY 已设环境变量，或写在本仓 .env。text 入库还需先起 embed_server.py。
对外：step1_extract_text … step7_write_kv；write_url_chunkable_source；index_url_chunks；call_chat_json。
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conf import (
    ANYURL2TEXT_URL,
    CHAT_API_URL,
    CHAT_MODEL_NAME,
    RESULT_DIR as KB_RESULT_DIR,
    SOURCE_DIR,
)
from offline.extract.enrich import infer_ingest_tags
from offline.store.kv_store import LocalKvStore
from offline.vector.chunk import split_text_for_kind
from offline.vector.entrance import run_vector

RESULT_DIR = KB_RESULT_DIR / "kv"

# ========== 按需修改 ==========
PIPELINE = "knowledge"  # text | knowledge
FILE_URL = ""  # 有值走 POST /extract
LOCAL_FILE = SOURCE_DIR / "sample_declaration.txt"
DEEPSEEK_API_KEY = ""  # 留空：环境变量 / 本仓 .env
CHAT_TIMEOUT_SEC = 600
LLM_MAX_TOKENS = 8192  # DeepSeek 非思考默认 8K，不显式给会被静默截断
EXTRACT_TIMEOUT_SEC = 300
MAX_DOC_TOKENS = 1800
# ==============================

ATOMIC_PROMPT = """
你是知识库结构化专家。你将收到一份从 __KIND__ 提取出的原文（可能包含 <table>... 结构以及 URL 链接）。

目标：把内容转成“原子化知识点二维表”，便于检索与匹配。

要求：
1）先给出文档主题 topic（尽量完整、准确）
2）输出知识点 items：必须尽可能多，覆盖每个章节/表格中的可检索信息；每一行必须尽可能“原子化”
   - index：原子化知识点名（例如：报到时间、比赛时间、比赛地点、报名截止时间、关门时间等）
   - content：尽可能保留原文的对应句子/条目（允许多行拼接，但必须来自原文，不得发明/总结/改写）
3）强约束：content 中不应出现连续重复的文本
4）强约束：下面列出的每一个 URL 都必须在 items 中至少出现 1 次（通常放在 content 中）
5）禁止输出 Markdown，禁止输出多余解释文字，只允许输出一个 JSON 对象
6）输出必须是合法 JSON；字符串中的双引号须转义；换行可保留为 \\n

输出 JSON 结构必须满足：
{
  "topic": "string",
  "items": [
    {
      "index": "string",
      "content": "string"
    }
  ]
}

必须覆盖的 URL 列表：
__URLS__

原文如下（请完整阅读后再输出 JSON）：
__DOC_TEXT__
""".strip()

RETRIEVE_PROMPT = """
你是知识库“检索结构化”专家。

你将收到：
1）某一段原文（chunk_index=__CHUNK_INDEX__，来源：__KIND__）
2）该段对应的“原子化知识点 JSON”（来自上一步抽取，分得很细）

目标：
把该段的原子化知识点重组为更利于检索的二维知识库结构。要求检索时尽量“一次命中得到足够答案”。

重要约束（必须遵守）：
1）输出必须是一个 JSON 对象，禁止输出 Markdown，禁止输出解释文字。
2）每条知识的 content 必须来自“原文片段”的原句/原条目拼接（允许换行拼接、允许重排顺序），不得发明/总结/改写。
3）index 是“可检索的标题/意图”（例如：报名方式、参赛资格、关门时间、注意事项、联系方式等）。
4）尽量减少行数：把同一意图下的内容合并到同一行，但不要把完全无关的内容硬塞在一起。
5）不得输出空 rows；若信息很少，也至少输出 1 条。
6）输出必须是合法 JSON；字符串中的双引号须转义；换行可保留为 \\n

输出 JSON 结构（严格遵守字段名）：
{
  "chunk_index": __CHUNK_INDEX__,
  "rows": [
    {
      "index": "string",
      "content": "string"
    }
  ]
}

原子化知识点 JSON：
__ATOM_ITEMS_JSON__

原文片段如下（请完整阅读后再输出 JSON）：
__DOC_TEXT__
""".strip()


def _resolve_deepseek_api_key() -> str:
    """DEEPSEEK_API_KEY 常量非空优先，否则进程环境变量或本仓 .env。"""
    return DEEPSEEK_API_KEY.strip() or os.getenv("DEEPSEEK_API_KEY", "").strip()


def _strip_thinking(text: str) -> str:
    """去掉思维链前缀（思考模式若被打开，DeepSeek 仍可能带 </think>）。"""
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    return (text or "").strip()


def extract_json_payload(text: str):
    """
    从模型输出里截出第一段能 parse 的 JSON 对象或数组。

    功能：容忍前后废话与思维链，只取 JSON。
    应用场景：call_chat_json 解析原子化 / 检索重组的回复。
    输入：text — 模型原始 content。
    输出：dict 或 list；截不出则 None。
    """
    text = _strip_thinking(text or "")
    if not text:
        return None

    obj_start = text.find("{")
    obj_end = text.rfind("}")
    if obj_start >= 0 and obj_end > obj_start:
        raw = text[obj_start : obj_end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    arr_start = text.find("[")
    arr_end = text.rfind("]")
    if arr_start >= 0 and arr_end > arr_start:
        raw = text[arr_start : arr_end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return None


def call_chat_json(full_prompt: str, stage: str = "") -> dict | list:
    """
    调 DeepSeek Chat Completions，要求回复能解析成 JSON。

    功能：关思考模式、json_object、显式 max_tokens；最多重试 3 次后截 JSON。
    应用场景：step4 原子化、step6 检索重组。
    输入：full_prompt — 整段 user 提示词；stage — 日志标签（atomic_1 / retrieve_1）。
    输出：解析后的 dict 或 list。
    异常：缺 API key、或三次都失败 → RuntimeError。
    """
    api_key = _resolve_deepseek_api_key()
    if not api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY：设进程环境变量或写入本仓 .env")

    last_err = None
    for attempt in range(1, 4):
        try:
            started = time.perf_counter()
            response = requests.post(
                CHAT_API_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": CHAT_MODEL_NAME,
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": LLM_MAX_TOKENS,
                    "thinking": {"type": "disabled"},
                    "response_format": {"type": "json_object"},
                },
                timeout=CHAT_TIMEOUT_SEC,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            parsed = extract_json_payload(content)
            elapsed = round(time.perf_counter() - started, 2)
            print(f"模型调用 stage={stage} attempt={attempt} cost={elapsed}s")
            if parsed is not None:
                return parsed
            last_err = RuntimeError("模型输出不是合法 JSON")
        except Exception as exc:
            last_err = exc
            print(f"模型调用失败 stage={stage} attempt={attempt}: {exc}")
    raise RuntimeError(f"模型调用失败 stage={stage}, last_error={last_err}")


def normalize_item_fields(index_text: str, content_text: str) -> tuple[str, str]:
    """
    压缩 index 空白、折叠 content 连续空行。

    功能：index 多空白压成单空格；content 连续空行压成最多两行换行。
    应用场景：原子化清洗与检索重组共用。
    输入：index_text — 标题；content_text — 正文。
    输出：(index, content) 规范化后的二元组。
    """
    index_text = re.sub(r"\s+", " ", (index_text or "").strip())
    content_text = (content_text or "").strip()
    content_text = re.sub(r"\n{3,}", "\n\n", content_text)
    return index_text, content_text


def clean_atomic_items(items: list[dict]) -> list[dict]:
    """
    清洗原子化 items：规范化字段，去掉 index 与 content 首行重复。

    功能：空条目丢弃；content 第一行若等于 index 则剥掉。
    应用场景：step4 收 LLM 结果、step5 补 URL 之后。
    输入：items — [{index, content}, ...]。
    输出：清洗后的同结构列表。
    """
    cleaned = []
    for item in items:
        index_text, content_text = normalize_item_fields(
            str(item.get("index", "")),
            str(item.get("content", "")),
        )
        if index_text and content_text:
            content_lines = content_text.splitlines()
            if content_lines and content_lines[0].strip() == index_text:
                content_text = "\n".join(content_lines[1:]).strip()
        if not index_text and not content_text:
            continue
        cleaned.append({"index": index_text, "content": content_text})
    return cleaned


def write_result(filename: str, text: str) -> Path:
    """
    把本步产物写到 data/result/kv/<filename>。

    功能：确保 kv 目录存在后写 UTF-8 文本。
    应用场景：各 step 写进磁盘共用。
    输入：filename — 如 step2_extracted.txt；text — 文件内容。
    输出：写出的路径。
    """
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / filename
    path.write_text(text, encoding="utf-8")
    return path


def collect_urls_from_text(text: str) -> list[str]:
    """
    从原文里按出现顺序去重收集 http(s) 链接。

    功能：正则扫 https?://，同一 URL 只留第一次。
    应用场景：step2 填 urls；step4 提示词要覆盖 URL 列表。
    输入：text — 抽取后的原文。
    输出：URL 字符串列表。
    """
    urls = []
    seen = set()
    for url in re.findall(r"https?://\S+", text or ""):
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def step1_extract_text() -> dict:
    """
    调 anyurl2text 抽出原文。

    功能：FILE_URL 非空则 POST /extract，否则把 LOCAL_FILE 以 multipart 传到 /extract/file。
    应用场景：流水线第 1 步。
    输入：读模块常量 FILE_URL / LOCAL_FILE / ANYURL2TEXT_URL。
    输出：anyurl2text 的完整 JSON（含 content、meta、error）。
    异常：HTTP 失败、error 非空、content 为空、meta.ext 缺失 → RuntimeError。
    """
    file_url = FILE_URL.strip()
    if file_url:
        print(f"[阶段1] POST {ANYURL2TEXT_URL}/extract url={file_url}")
        response = requests.post(
            f"{ANYURL2TEXT_URL}/extract",
            json={"url": file_url},
            timeout=EXTRACT_TIMEOUT_SEC,
        )
    else:
        local_path = Path(LOCAL_FILE)
        if not local_path.is_file():
            raise RuntimeError(f"本地文件不存在: {local_path}")
        print(f"[阶段1] POST {ANYURL2TEXT_URL}/extract/file file={local_path}")
        with local_path.open("rb") as file_obj:
            response = requests.post(
                f"{ANYURL2TEXT_URL}/extract/file",
                files={"file": (local_path.name, file_obj)},
                timeout=EXTRACT_TIMEOUT_SEC,
            )

    response.raise_for_status()
    payload = response.json()
    error = payload["error"]
    if error:
        raise RuntimeError(f"anyurl2text 抽取失败: {error}")
    content = payload["content"]
    if not str(content).strip():
        raise RuntimeError("anyurl2text 返回的 content 为空")
    ext = payload["meta"]["ext"]
    if not ext:
        raise RuntimeError("anyurl2text 未给出 meta.ext")
    print(f"[阶段1] ok ext={ext} chars={len(content)}")
    extract_path = write_result(
        "step1_extract_response.json",
        json.dumps(payload, ensure_ascii=False, indent=2),
    )
    print(f"[阶段1] 已写入 {extract_path}")
    return payload


def step2_write_extracted(extract_payload: dict) -> dict:
    """
    从抽取结果整理 kind / urls / text 并写进磁盘。

    功能：kind 取 meta.ext；urls 从正文正则扫描；写 step2_extracted.txt。
    应用场景：流水线第 2 步。PIPELINE=text 时接着写可分块原文并入库。
    输入：extract_payload — step1 的响应。
    输出：{kind, urls, text}，给后续分块与知识库步骤。
    """
    text = extract_payload["content"]
    kind = extract_payload["meta"]["ext"]
    urls = collect_urls_from_text(text)
    text_data = {"kind": kind, "urls": urls, "text": text}
    extracted_path = write_result("step2_extracted.txt", text)
    print(f"[阶段2] 已写入 {extracted_path} kind={kind} chars={len(text)} urls={len(urls)}")
    return text_data


def url_source_name() -> str:
    """
    URL 或本地文件收成来源目录名。

    功能：FILE_URL 用路径最后一段；否则用本地文件 stem。
    应用场景：可分块原文的 source、向量库子目录、KV id 前缀。
    输入：无，读 FILE_URL / LOCAL_FILE。
    输出：不含路径分隔符的字符串。
    """
    file_url = FILE_URL.strip()
    if file_url:
        parsed = urlparse(file_url)
        name = Path(parsed.path).stem or parsed.netloc or "url-source"
        slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name).strip("-")
        return slug or "url-source"
    return Path(LOCAL_FILE).stem


def write_url_chunkable_source(text_data: dict) -> dict:
    """
    URL 适配器吐可分块原文（无页，用 text）。

    功能：写 data/result/<source>/chunkable_source.json。
    应用场景：PIPELINE=text，step2 之后。
    输入：text_data — step2 的 {kind, text, urls}。
    输出：可分块原文对象。
    """
    source_name = url_source_name()
    tags = infer_ingest_tags(text_data["text"], source_name)
    payload = {
        "source": source_name,
        "kind": text_data["kind"],
        "text": text_data["text"],
        "tags": tags,
    }
    source_dir = KB_RESULT_DIR / source_name
    source_dir.mkdir(parents=True, exist_ok=True)
    path = source_dir / "chunkable_source.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"可分块原文 已写入 {path}")
    return payload


def index_url_chunks(source_obj: dict) -> Path:
    """
    共享分块后写进向量库。

    功能：调向量层 entrance.run_vector，与 ingest 同一条写库路径。
    应用场景：PIPELINE=text。
    输入：source_obj — 可分块原文（磁盘上已有 chunkable_source.json）。
    输出：LanceDB 目录路径。
    异常：知识块为空 → ValueError。
    """
    source_path = KB_RESULT_DIR / source_obj["source"] / "chunkable_source.json"
    return run_vector(source_path)


def step3_split_chunks(text_data: dict) -> list[str]:
    """
    按文件类型把原文切成原子化用的块。

    功能：调用 offline.vector.chunk.split_text_for_kind；pdf 按页组块，其余按段。空块视为失败。
    应用场景：流水线第 3 步，只在 PIPELINE=knowledge 时调用。
    输入：text_data — step2 的 {kind, text, urls}。
    输出：块文本列表。
    异常：分块为空 → ValueError。
    """
    # 切分实现在 offline/vector/chunk.py，本步只选 kind 并检查非空
    chunks = split_text_for_kind(text_data["text"], text_data["kind"], max_doc_tokens=MAX_DOC_TOKENS)
    if not chunks:
        raise ValueError("原文分块为空")
    print(f"[阶段3] 分块完成 kind={text_data['kind']} chunks={len(chunks)}")
    return chunks


def step4_atomic_extract(chunks: list[str], text_data: dict) -> list[dict]:
    """
    对每一块调用原子化提示词，得到 topic + items。

    功能：按块调 LLM，清洗 items；本步不补 URL（留给 step5）。
    应用场景：流水线第 4 步。
    输入：chunks — step3 的块；text_data — 提供 kind 与 urls。
    输出：[{chunk_index, topic, text, items}, ...]。
    异常：LLM 没返回对象 → RuntimeError。
    """
    kind = text_data["kind"]
    urls = text_data["urls"]
    urls_text = "\n".join(urls or re.findall(r"https?://\S+", text_data["text"]))
    atomic_chunks = []
    total = len(chunks)
    for chunk_index, chunk_text in enumerate(chunks, start=1):
        print(f"[阶段4] [{chunk_index}/{total}] 原子化 chars={len(chunk_text)}")
        prompt = (
            ATOMIC_PROMPT.replace("__KIND__", kind)
            .replace("__URLS__", urls_text)
            .replace("__DOC_TEXT__", chunk_text)
            .strip()
        )
        data = call_chat_json(prompt, stage=f"atomic_{chunk_index}")
        if not isinstance(data, dict):
            raise RuntimeError(f"原子化输出应为对象，实际为 {type(data).__name__}")
        items = data.get("items", [])
        if not isinstance(items, list):
            items = []
        items = [item for item in items if isinstance(item, dict)]
        atomic_chunks.append(
            {
                "chunk_index": chunk_index,
                "topic": str(data.get("topic", "") or ""),
                "text": chunk_text,
                "items": clean_atomic_items(items),
            }
        )
    print(f"[阶段4] 原子化完成 chunks={total}")
    return atomic_chunks


def step5_fill_missing_urls(atomic_chunks: list[dict], text_data: dict) -> list[dict]:
    """
    把原文里出现过、但 items 尚未覆盖的 URL 补进每一块。

    功能：用 URL 所在行的前两行当 index 上下文；默认 index 对文档类用「图片」，其余用「链接」。
          每个 chunk 都会检查全文 URL。
    应用场景：流水线第 5 步。
    输入：atomic_chunks — step4 产出；text_data — 提供 text 与 kind。
    输出：补完 URL 并再次清洗 items 的同一列表（原地修改后返回）。
    """
    kind = text_data["kind"]
    doc_text = text_data["text"]
    default_index = "图片" if kind in ("docx", "pdf", "excel", "xlsx") else "链接"
    doc_urls = re.findall(r"https?://\S+", doc_text or "")
    doc_lines = [line.rstrip() for line in (doc_text or "").splitlines()]
    filled = 0
    for chunk in atomic_chunks:
        items = chunk.get("items", [])
        for url in doc_urls:
            if any(url in str(item.get("index", "")) or url in str(item.get("content", "")) for item in items):
                continue
            ctx_index = default_index
            ctx_lines = []
            for index, line in enumerate(doc_lines):
                if url not in line:
                    continue
                prev1 = doc_lines[index - 1].strip() if index - 1 >= 0 else ""
                prev2 = doc_lines[index - 2].strip() if index - 2 >= 0 else ""
                if prev1:
                    ctx_index = prev1
                elif prev2:
                    ctx_index = prev2
                ctx_lines = [part for part in [prev2, prev1, url] if part]
                break
            items.append({"index": ctx_index, "content": "\n".join(ctx_lines) if ctx_lines else url})
            filled += 1
        chunk["items"] = clean_atomic_items(items)
    chunks_path = write_result(
        "step5_atomic_chunks.json",
        json.dumps(atomic_chunks, ensure_ascii=False, indent=2),
    )
    print(f"[阶段5] 已写入 {chunks_path} filled={filled} doc_urls={len(doc_urls)}")
    return atomic_chunks


def step6_retrieve_rebuild(atomic_chunks: list[dict], kind: str) -> list[dict]:
    """
    把每块的原子化 items 重组为更利于一次命中的检索行。

    功能：按块调检索重组提示词，规范化为 [{index, content}, ...]。
    应用场景：流水线第 6 步。
    输入：atomic_chunks — step5 产出；kind — 文件类型，写入提示词。
    输出：所有块的 rows 拼成一条列表。
    """
    rows = []
    total = len(atomic_chunks)
    for chunk in atomic_chunks:
        chunk_index = int(chunk.get("chunk_index") or 0)
        chunk_text = str(chunk.get("text") or "")
        atom_items = chunk.get("items", [])
        topic = str(chunk.get("topic") or "")
        print(f"[阶段6] [{chunk_index}/{total}] 检索重组 atom_items={len(atom_items)}")
        atom_items_text = json.dumps({"topic": topic, "items": atom_items}, ensure_ascii=False, indent=2)
        prompt = (
            RETRIEVE_PROMPT.replace("__KIND__", kind)
            .replace("__CHUNK_INDEX__", str(chunk_index))
            .replace("__ATOM_ITEMS_JSON__", atom_items_text)
            .replace("__DOC_TEXT__", chunk_text)
            .strip()
        )
        data = call_chat_json(prompt, stage=f"retrieve_{chunk_index}")
        if isinstance(data, list):
            raw_rows = data
        elif isinstance(data, dict):
            raw_rows = data.get("rows", [])
        else:
            raw_rows = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            index_text, content_text = normalize_item_fields(
                str(row.get("index", "")),
                str(row.get("content", "")),
            )
            if index_text and content_text:
                rows.append({"index": index_text, "content": content_text})
    rows_path = write_result(
        "step6_retrieve_rows.json",
        json.dumps(rows, ensure_ascii=False, indent=2),
    )
    print(f"[阶段6] 已写入 {rows_path} rows={len(rows)}")
    return rows


def step7_write_kv(retrieve_rows: list[dict]) -> list[dict]:
    """
    把重组行转成 kv_list 并写进磁盘。

    功能：{index, content} → {key, value}；写 step7_knowledge_kv.json，并 upsert 进 kv_store.json。
    应用场景：流水线第 7 步。
    输入：retrieve_rows — step6。
    输出：kv_list。
    """
    kv_list = []
    for row in retrieve_rows:
        key = str(row.get("index", "")).strip()
        value = str(row.get("content", "")).strip()
        if not key and not value:
            continue
        kv_list.append({"key": key, "value": value})

    kv_path = write_result(
        "step7_knowledge_kv.json",
        json.dumps(kv_list, ensure_ascii=False, indent=2),
    )
    print(f"[阶段7] 已写入 {kv_path} items={len(kv_list)}")

    source_name = url_source_name()
    store_path = RESULT_DIR / "kv_store.json"
    store = LocalKvStore()
    if store_path.is_file():
        store = LocalKvStore.load(store_path)
    entries = []
    for index, item in enumerate(kv_list, start=1):
        entries.append(
            {
                "id": f"{source_name}-kv-{index:04d}",
                "key": item["key"],
                "value": item["value"],
                "metadata": {"source": source_name, "tags": []},
            }
        )
    store.upsert(entries)
    store.save(store_path)
    print(f"[阶段7] KV 存储 已写入 {store_path} records={len(store.records)}")
    return kv_list


if __name__ == "__main__":
    source = FILE_URL.strip() or str(LOCAL_FILE)
    print(f"PIPELINE={PIPELINE}")
    print(f"source={source}")
    # 阶段1：anyurl2text 抽原文 → data/result/kv/step1_extract_response.json
    extract_payload = step1_extract_text()
    # 阶段2：扫 URL、写进磁盘 data/result/kv/step2_extracted.txt
    text_data = step2_write_extracted(extract_payload)
    if PIPELINE == "text":
        # 可分块原文 → 向量层写入 data/lancedb
        source_obj = write_url_chunkable_source(text_data)
        index_url_chunks(source_obj)
        print(f"完成 text kind={text_data['kind']} source={source_obj['source']}")
    else:
        # 阶段3：按 kind 分块（offline.vector.chunk.split_text_for_kind）
        chunks = step3_split_chunks(text_data)
        # 阶段4：LLM 原子化
        atomic_chunks = step4_atomic_extract(chunks, text_data)
        # 阶段5：补漏 URL → data/result/kv/step5_atomic_chunks.json
        atomic_chunks = step5_fill_missing_urls(atomic_chunks, text_data)
        # 阶段6：LLM 检索重组 → data/result/kv/step6_retrieve_rows.json
        retrieve_rows = step6_retrieve_rebuild(atomic_chunks, text_data["kind"])
        # 阶段7：kv_list → data/result/kv/step7_knowledge_kv.json
        kv_list = step7_write_kv(retrieve_rows)
        print(f"完成 knowledge items={len(kv_list)}")
