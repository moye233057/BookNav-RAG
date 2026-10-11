# -*- coding: utf-8 -*-
"""
向量 HTTP 进程入口。

职责：绑定本文件 HOST/PORT，调用 embed/server.py 的实现。
前置：models/<models_embedder>/pytorch_model.bin 或 model.safetensors；可用 python scripts/download_embed.py 下载。
对外：POST /v1/embeddings。
"""

from __future__ import annotations

import conf  # ROOT 进 path；读 yaml 与 .env
from embed.server import serve

# ========== 按需修改 ==========
HOST = "127.0.0.1"
PORT = 8030
# ==============================


if __name__ == "__main__":
    serve(HOST, PORT)
