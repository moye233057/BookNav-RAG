"""
从 ModelScope 下载 bge-m3 到本脚本同目录的 models/。

职责：向量模型服务的权重准备，不启动 HTTP。跑完即退出。
对外：__main__ 调 snapshot_download。
前置：已 `uv sync`。
锁定版本：revision 在 conf/base.py 的 EMBED_MODEL_REVISION；留空则下默认分支并在日志里明说未锁定版本（TODO P2·17）。
换权重：改本文件的 MODEL_ID，以及 conf/base.py 的 EMBED_MODEL_NAME / EMBED_DIM_BY_NAME，再跑一次。
怎么跑：在仓库根 `uv run python embed/download_embed.py`。
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from modelscope import snapshot_download

from conf import EMBED_MODEL_REVISION

MODEL_ID = "BAAI/bge-m3"
MODEL_DIR = SCRIPT_DIR / "models"

if __name__ == "__main__":
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    revision = EMBED_MODEL_REVISION.strip()
    if revision:
        print(f"[权重] {MODEL_ID} revision={revision} → {MODEL_DIR}")
        print(snapshot_download(MODEL_ID, revision=revision, local_dir=str(MODEL_DIR)))
    else:
        print(f"[权重] 未锁定 revision：{MODEL_ID} 默认分支 → {MODEL_DIR}")
        print("[权重] 要重现同一份权重：把 ModelScope 的分支名或 tag 填进 conf/base.py 的 EMBED_MODEL_REVISION")
        print(snapshot_download(MODEL_ID, local_dir=str(MODEL_DIR)))
