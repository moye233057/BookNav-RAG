# -*- coding: utf-8 -*-
"""
多轮命令行：同一 session 循环提问，看跟进、筛选沿用、闲聊再回到检索。不经问答页。空行或 q 结束。

原理（按系统流程）
  线上多轮：同一 session 的 turns 只给意图识别。检索问句可改写；筛选可沿用上一轮。
  本脚本开库一次，自造一份 session，每行输入问一句，invoke 同一张图。不评测 Hit@k。

  例子
    「后视镜怎么折叠」→ 检索，出答案和引用。
    「它怎么展开」→ 跟进，筛选沿用，仍答后视镜。
    「你好」→ 闲聊，无引用。
    「资料来源是哪份」→ 身份追问，走检索。

怎么跑（本文件入口；编号和上面例子不是同一套）
  职责：开库一次，固定 session，循环 input 直到空行或 q。
  入口步骤：
    1. open_knowledge_base — 读 data/lancedb，只做一次。
    2. 循环：input → run_ask_graph（带 session）→ print_turn。
  输入：键盘；不覆盖意图标签。
  前置：已入库；embed_server.py 已起；生成需 Chat API key。
  产出：控制台每一轮一块「结果」；召回调试仍写 data/result/qa/step2_hits.json（只留最后一条）。
  对外：无。print_turn 在 query_kb.py。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

repo_root = Path(__file__).resolve().parent.parent
scripts_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(scripts_dir))
import conf  # ROOT 在 conf.base；读 yaml 与 .env

from online.graph import run_ask_graph
from online.recall.retrieve import open_knowledge_base
from query_kb import print_turn

if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    session = str(uuid4())
    print("多轮对话")
    print("空行或 q 结束")
    print(f"session  {session}")
    # 阶段1：LanceDB chunks 表 → 一份知识库
    knowledge_base = open_knowledge_base()
    turn = 0
    while True:
        try:
            raw = input("\n问: ")
        except (EOFError, KeyboardInterrupt):
            print("\n结束")
            break
        question = raw.strip()
        if not question or question.lower() in ("q", "quit", "exit"):
            print("结束")
            break
        turn += 1
        # 阶段2：同一 session 再跑意图 → 召回 → 生成
        result = run_ask_graph(knowledge_base, question, session=session)
        print_turn(question, result, turn)
