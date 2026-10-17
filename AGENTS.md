# 给 AI 的本仓约定

本仓例外与禁令。只放本仓特有、且从代码与文档里查不到的部分。

事实源指针：跑法 [README.md](README.md) ｜ 叫法 [CONTEXT.md](CONTEXT.md) ｜ 目标设计 [docs/architecture.md](docs/architecture.md) ｜ 为什么 [docs/adr.md](docs/adr.md) ｜ 主流程 [docs/pipelines.md](docs/pipelines.md)

废决策见 [docs/history.md](docs/history.md)，不要把里面的旧选定当成不许做的事。产品仓对照见 [docs/compare.md](docs/compare.md)。

## 环境：uv

`uv sync`，再 `uv run python ...`。包清单在 `pyproject.toml`。跑测试先 `uv pip install pytest`。
AI 在非交互 shell 里跑本仓 Python：`uv run`，或 `uv sync` 之后用 `.venv\Scripts\python.exe`，并设 `PYTHONUTF8=1`。

不给本仓发明命令行参数。长驻服务从仓库根 `uv run python start.py`（一键）启动，或分别 `uv run python -m embed.server` / `uv run python -m online.server`，以及 `cd frontend && npm run dev`。不要 `python embed/server.py` 或 `python online/server.py`（sys.path 会指到子目录）。命令行脚本只当调试。
问答页视觉规范在 `frontend/DESIGN.md`，不在仓库根。待做勾选在 `docs/TODO.md`。

## 端口从 8030 连号

向量 8030、问答 8031、Vite 8032、可选 VLM 8033。不要写回 8081 / 8090 / 5173 / 8080。

## 只读本仓 .env

`conf.apply_env()` 是唯一读取点。不要读别的仓的 `.env`。密钥模板 `.env_example` 可以进仓；填了密钥的 `.env`、权重不要提交。

## 长任务与残留进程

入库、评测、全量 pytest 不许在前台干等：后台作业起、要停就停作业本身；前台调用的 timeout 不超过 120 秒。看不到进度的长任务按卡死处理——入库每批都打进度（`EMBED_REQUEST_BATCH`）。

中止一轮或停掉作业之后，必须核对有没有留下 python 残留进程：中止只杀 shell，孙进程会活下来。2026-10-08 有一个被中止的 `pytest tests -q` 空转一小时，烧掉 3400s CPU，而同一命令正常只要 21s。

## 测试落点

测试卡住时要能自己退出：到点自己退出的超时开关在 `pyproject.toml` 的 `[tool.pytest.ini_options]`（`faulthandler_timeout`）。要写到磁盘的用例用 `tests/conftest.py` 的 `work_dir`，不要用 `tmp_path`（沙箱里用 `0o700` 建出来的目录连创建者都列不出）。

## 改代码时的硬约束

1. 新代码进目标架构规定的位置。不要重建 `query/`。离线不要再拆独立的分块层 / 向量化层 / 向量存储层。向量模型服务不要放进 `offline/` 或 `online/`。向量库不要写回每来源一份 `step5` JSON。
2. 层与模块开关只改 `conf/base.py`，不要写回各层顶部常量。不把 ROOT、host、port、第三方地址、密钥写进 `conf/config.yaml`。权重目录是 `embed/models/`（下载脚本同目录），不写进 yaml。
3. `vlm_ocr.py` / `anyurl.py` 是预留实现文件：本阶段不调用、不要删、不要接进流程。抽取目录只放流程会调用的模块。向量层不要 import 抽取方式。不要拆共享 Chat 客户端。
4. 不把产品仓的模块名、类名、`parser_id` 写进本仓代码或术语表。不 fork 产品仓。不把 anyurl2text、MinerU、anydoc 源码引进本仓。不要再接外仓 `/rag/extract/file`。
5. 提问口不接 `create_agent` / `create_deep_agent`、KV 查询侧短路、词重叠重排。不要做图片 OCR、ask 热加载。
