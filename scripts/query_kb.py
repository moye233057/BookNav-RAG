# -*- coding: utf-8 -*-
"""
单轮快测：线上问答整条含生成，只问顶部 QUESTION 这一句，打出答案后退出。不评测 Hit@k，不多轮。

怎么跑（本文件入口）
  职责：开库一次，invoke 图一次，最后打一块问/途/答/引。
  入口步骤：
    1. open_knowledge_base — 读 data/lancedb，只做一次。
    2. run_ask_graph — 意图 → 召回 → 重排 → 同节邻块 → 拒答或生成。
  输入：下面常量 QUESTION；FILTER_* 非空则覆盖意图标签。
  前置：已入库；embed_server.py 已起；生成需 Chat API key。
  产出：控制台「结果」块；召回调试仍写 data/result/qa/step2_hits.json。
  对外：print_turn。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import conf  # ROOT 在 conf.base；读 yaml 与 .env

from online.graph import run_ask_graph
from online.intent.classify import ROUTE_CHITCHAT
from online.recall.retrieve import open_knowledge_base

# ========== 按需修改 ==========
QUESTION = "后视镜怎么折叠"
FILTER_SOURCE = ""
FILTER_TAGS = []
# ==============================


def default_filters() -> dict:
    """命令行顶部 FILTER_SOURCE / FILTER_TAGS 收成检索过滤。"""
    return {"source": FILTER_SOURCE, "tags": FILTER_TAGS}


def print_turn(question: str, result: dict, turn: int | None = None) -> None:
    """
    把一轮生成结果打成可读的命令行块。

    功能：问、途、检索问句（有改写才打）、标、答、引。
    应用场景：query_kb 单轮；chat_kb 每一轮。
    输入：question — 用户原文；result — run_ask_graph 返回值；turn — 多轮序号，单轮不传。
    输出：无。打到控制台。
    """
    if turn is None:
        print("\n======== 结果 ========")
    else:
        print(f"\n======== {turn} ========")
    print(f"问  {question}")
    way = "闲聊" if result["route"] == ROUTE_CHITCHAT else "检索"
    print(f"途  {way}")
    text = result["text"]
    if text != question:
        print(f"检索问句  {text}")
    tags = result["tags"]
    if tags:
        chips = "  ".join(f"{tag['field']}={tag['value']}" for tag in tags)
        print(f"标  {chips}")
    else:
        print("标  无")
    print("答")
    answer_lines = result["answer"].splitlines() or [""]
    for line in answer_lines:
        print(f"    {line}")
    citations = result["citations"]
    if not citations:
        print("引  无")
        return
    print("引")
    for index, citation in enumerate(citations, start=1):
        pages = citation["pages"]
        page_part = f" p.{','.join(str(page) for page in pages)}" if pages else ""
        snippet = " ".join(citation["snippet"].split())
        if len(snippet) > 80:
            snippet = snippet[:80] + "…"
        print(f"    {index}. {citation['source']}{page_part}")
        print(f"       {snippet}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    # 阶段1：LanceDB chunks 表 → 一份知识库
    knowledge_base = open_knowledge_base()
    # 阶段2：图内意图 → 召回 → 生成或拒答
    result = run_ask_graph(knowledge_base, QUESTION, default_filters())
    print_turn(QUESTION, result)
