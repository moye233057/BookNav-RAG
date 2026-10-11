# 交接指针

> 临时工作态，不是项目文档；长期规矩见 CONTEXT.md / docs/adr.md

**正文**：[docs/handoff/HANDOFF-2026-10-08-verify-first.md](handoff/HANDOFF-2026-10-08-verify-first.md)
**写于**：2026-10-08（第 1 阶段收口后重写）
**一句话目标**：book-nav-rag（原 self-rag）缺陷修复 —— 第 1 阶段（P0·1 / P0·2 / P0·3 / P0·5 / P0·18）已全部验收通过，下一步进第 2 阶段修离线数据正确性

**下一步**：做 P0·6，修 `offline/vector/chunk.py` 的 `clean_page_text` 与分段切分契约冲突（实测源页 388/390 含 `\n\n`，切完块里 0 个 → 按段分块从未生效）。改完跑 `python scripts/ingest.py --vector-only` 重跑向量层，再把 `TODO.md` 第 1 节的块数与 token 分布回填。重入库要写 `data/`，agent 的 workspace-write 沙箱写不进去：切「完全权限」，或在你自己的终端跑。

**另需你动手**：删 `tests\test_probe.py`（若仍在；2 行 `assert True` 空探针）；关 Cursor 占用后把本机目录 `self-rag` 改名为 `book-nav-rag`。

正文过期以本指针为准。
