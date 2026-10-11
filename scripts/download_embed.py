# -*- coding: utf-8 -*-
"""
从 ModelScope 下载 bge-m3 到仓内 models/<models_embedder>。

职责：向量模型服务的权重准备，不启动 HTTP。跑完即退出。
对外：__main__ 调 snapshot_download。
前置：conda 环境 rag；modelscope 已装。
钉版：revision 在 conf/base.py 的 EMBED_MODEL_REVISION；留空则下默认分支并在日志里明说未钉版（TODO P2·17）。
换权重：改 conf/config.yaml 的 models_embedder 与本文件的 MODEL_ID，再跑一次。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modelscope import snapshot_download

from conf import BGE_MODEL_DIR, EMBED_MODEL_REVISION

MODEL_ID = "BAAI/bge-m3"

if __name__ == "__main__":
    BGE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    revision = EMBED_MODEL_REVISION.strip()
    if revision:
        print(f"[权重] {MODEL_ID} revision={revision} → {BGE_MODEL_DIR}")
        print(snapshot_download(MODEL_ID, revision=revision, local_dir=str(BGE_MODEL_DIR)))
    else:
        print(f"[权重] 未钉 revision：{MODEL_ID} 默认分支 → {BGE_MODEL_DIR}")
        print("[权重] 要复现同一份权重：把 ModelScope 的分支名或 tag 填进 conf/base.py 的 EMBED_MODEL_REVISION")
        print(snapshot_download(MODEL_ID, local_dir=str(BGE_MODEL_DIR)))
