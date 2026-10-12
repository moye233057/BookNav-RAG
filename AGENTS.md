# AGENTS.md

本仓给 AI 的例外。编码风格走全局 skill，不在本文重复。

写或改本仓代码之前读：[CONTEXT.md](CONTEXT.md)（叫法）、[docs/architecture.md](docs/architecture.md)（位置、步骤调用、明确不做、约定，现行约束）、[docs/adr.md](docs/adr.md)（仍有效的为什么）。废决策见 [docs/HISTORY.md](docs/HISTORY.md)，不要把里面的旧选定当成不许做的事。怎么跑见 [README.md](README.md)。

## 本仓规矩

密钥与第三方对接放根目录 `.env`（模板 `.env_example`）：`DEEPSEEK_API_KEY`、`CHAT_API_URL`、`CHAT_MODEL_NAME`、`EMBED_API_URL`、`EMBED_API_KEY`、`ANYURL2TEXT_URL`（只剩 KV 实验脚本打 `/extract` 用）。**只读本仓 `.env`，不读别的仓的 `.env`**（2026-10-10 已删除读取外仓 `.env` 的兜底做法，见 TODO P2·25）。ROOT 只在 `conf/base.py`。`conf/config.yaml` 只放相对数据目录、模型目录名、向量库目录。本服务 host/port 写在 `ask_server.py` / `embed_server.py`。层与模块的开关、阈值、提示词在 `conf/base.py`，按层注释分隔；不要写回各层顶部常量。手册 PDF 本仓 pymupdf4llm 抽页与印刷目录；与 anyurl2text 抽取解耦，路由不登记非 PDF。不要按样本文件名切换抽取。不要按「源适配器」加 Office 文件。新代码放到目标架构规定的位置：抽取进 `offline/extract/`，离线向量进 `offline/vector/`，向量模型服务进仓库根 `embed/`（入口 `embed_server.py`）。权重下载走 `scripts/download_embed.py`。入库走 `scripts/ingest.py`。向量权威库是 `data/lancedb/` 的 `chunks` 表，不要写回 `step5` JSON。不要为 KV 或其它对象预埋第二库。HTTP 路由写在 `online/router.py`，进程入口是仓库根 `ask_server.py`。命令行调试、评测、入库、下载放 `scripts/`，不另开 `query/`。领域词用术语表里的那个。不要接 KV 查询侧短路，也不要接词重叠重排。过滤标签已迁动态键值（ADR-0026）。评测口已扩 Hit@k（正样本可对页）；改写默认开；拒答按向量余弦。召回吐出候选窗口，`TOP_K` 由重排节点截断（ADR-0027）。重排后再并同节邻块（ADR-0028）。不要做图片 OCR、ask 热加载（不重启就换上新代码）、Agent 沙箱。向量层不要 import 抽取方式。检索门面指 `web/`，不要把 `retrieve.py` 叫门面。不要拆共享 Chat 客户端。不要把样本领域写进表列或提示词当系统定义。旧 LanceDB 缺 `tags` 或 `catalogue_title` 列须删后重入库。

在线主路径：LangGraph 图串层；生成用 LangChain `prompt | model | parser`。提问口不接 `create_agent` / `create_deep_agent`。Agent 学习沙箱只放 `scripts/`，不接提问口。

产品仓怎么设计，读 [docs/compare.md](docs/compare.md)：一篇一仓，分仓细读就是其中各节。

## 硬性约束

- 不把 ROOT、host、port、第三方地址、密钥写进 `conf/config.yaml`。
- 层与模块开关只改 `conf/base.py`，不要写回各层顶部常量。
- 不把密钥、填了密钥的 `.env`、权重写进本仓。`.env_example` 可以进仓。
- 不给本仓发明命令行参数；长驻服务从仓库根 `start.py`（一键）启动，或分别起 `embed_server.py` / `ask_server.py` / `web`。启动命令分两步：先 `conda activate rag`，再 `python ...`，不要写 `conda run -n`。AI 在非交互 shell 里跑本仓 Python，一律用解释器绝对路径加 `PYTHONUTF8=1`（`conda activate` 在非交互 shell 里静默无效，会让命令用上 base 解释器），命令见 README「快速开始」。命令行脚本只当调试。
- 长任务（入库、评测、全量 pytest）不许在前台干等：后台作业起、要停就停作业本身；前台调用的 timeoutMs 不超过 120000。看不到进度的长任务按卡死处理——入库每批都打进度（`EMBED_REQUEST_BATCH`）。
- 中止一轮或停掉作业之后，必须核对有没有留下 python 残留进程：中止只杀 shell，孙进程会活下来。2026-10-08 有一个被中止的 `pytest tests -q` 空转一小时，烧掉 3400s CPU，而同一命令正常只要 21s。
- 测试卡住时要能自己退出：到点自己退出的超时开关在 `pytest.ini`（`faulthandler_timeout`）；导入 / 收集阶段就卡住时用 README「跑测试」里的包装入口。要写到磁盘的用例用 `tests/conftest.py` 的 `work_dir`，不要用 `tmp_path`（沙箱里用 `0o700` 建出来的目录连创建者都列不出）。
- 本仓端口从 8030 连号：向量 8030、问答 8031、Vite 8032、可选 VLM 8033。不要写回 8081 / 8090 / 5173 / 8080。
- 不把产品仓的模块名、类名、`parser_id` 写进本仓代码或术语表。
- 不 fork 产品仓进本仓。
- 不把 KV 当第二套必建库，也不把 KV 条目再编进向量库。
- 不把 Deep Agent 或工具循环接进问答主路径。
- 不另起目录绕开目标架构规定的代码位置。不要重建 `query/`。离线不要再拆独立的分块层 / 向量化层 / 向量存储层。向量模型服务不要放进 `offline/` 或 `online/`。向量库不要写回每来源一份 `step5` JSON。
- 不把对照附录改写成自建规范。
- 不把 anyurl2text、MinerU、anydoc 源码引进本仓。手册抽取只走 `offline/extract/methods/pdf.py`；不要再接外仓 `/rag/extract/file`。
- 抽取目录只放流程会调用的模块；测试与调试不进 `offline/extract/`。`vlm_ocr.py` / `anyurl.py` 是预留实现文件（先放着，本阶段不接进流程），本阶段不调用、不要删、不要接进流程。
- 新抽取方式必须符合目标架构规范并在路由登记；不按格式新开源适配器。
