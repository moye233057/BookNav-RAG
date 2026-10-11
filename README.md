# book-nav-rag

**BookNav-RAG 目录导航问答** — 把带印刷目录的 PDF，按目录归页后再问答，答案带来源与页码引用。

离线入库 · 目录归页 · 向量 + BM25 召回 · 意图分流 · 拒答闸门 · 问答页

[项目介绍](#项目介绍) · [快速开始](#快速开始) · [怎么工作](#怎么工作) · [接口用法](#接口用法) · [项目结构](#项目结构) · [已知局限](#已知局限) · [许可与第三方](#许可与第三方)

> **个人展示项目**：仅供学习与简历展示，**不会用于任何商业或生产环境**。  
> 中心思想是**印刷目录导航 → 块级页码**，思路接近 PageIndex 一类「页结构优先」的 RAG；不是论文 [SELF-RAG](https://arxiv.org/abs/2310.11511) 那套反思检索。

---

## 项目介绍

把 PDF 放进 `data/source/`，系统识别印刷目录、按章节区间归页并切成带页码的知识块，写入本地 LanceDB；提问时走意图识别（闲聊 / 检索 / 跟进），混合向量与 BM25 召回，生成带来源与页码的答案。向量服务挂了时降级为关键词召回，不把整个问答口打成 500。

### 项目包含什么

| 能力 | 做什么 | 重要性 |
|---|---|---|
| PDF 抽取与目录归页 | 本仓 pymupdf4llm 抽页；印刷目录 → 块级页码 | **核心**。本阶段只支持 PDF |
| 向量入库 | bge-m3 编向量，LanceDB 一张 `chunks` 表 | **核心**。须本机权重 + 向量服务 |
| 在线问答 | 意图 → 召回 → 拒答/生成；`POST /api/ask` | **核心**。须 Chat API 密钥 |
| 问答页 | Vite 对话 UI，侧栏展示引用 | 本机演示与调试 |
| 入库验收 / 评测口 | `verify_ingest.py`、`eval_kb.py` | 证明页码与 Hit@k，不是产品 UI |

远程仓库：（公开后填 GitHub / Gitee URL）  
许可证：[AGPL-3.0-only](LICENSE)  
仓库**不收录** embedding 权重、第三方版权 PDF、本机私有评测集；演示样例见 `samples/demo_handbook.pdf`。

### 设计亮点（面试可深挖）

| 点 | 一句话 |
|---|---|
| 印刷目录动态扫描 | 不写死「只读前 N 页目录」，避免后半本书并进错误标题 |
| 块级页码 | 子块只声明自己覆盖的页；验收脚本要求「声明页次 / 页并集 = 1」 |
| 标签加权不硬切 | 多文档同字段多值时不把候选筛空，按命中条数加分 |
| 向量降级 | 8030 不可用 → 纯 BM25，拒答改看词面规则 |
| 同路径评测 | `eval_kb.py` 走线上同一条检索图，可校准拒答阈值 |

---

## 快速开始

命令默认在**仓库根目录**执行。需要：Python 3.12、Node.js ≥ 18、约 2GB+ 磁盘（bge-m3 权重）。

### Ⅰ 安装依赖

**A. conda（本机常用）**

```powershell
conda env create -f environment.yml
conda activate rag
pip install -r requirements.txt
```

**B. venv + pip**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

`-e` 不能省：`conf` 用 `__file__` 推算仓库根，装成普通 wheel 会找不到 `.env` / `data/` / `models/`。

```powershell
copy .env_example .env
# 编辑 .env，至少填 DEEPSEEK_API_KEY（入库抽标签与问答生成都要用）

python scripts/download_embed.py
# 权重落到 models/bge-m3/，须有 pytorch_model.bin 或 model.safetensors

cd web
npm install
cd ..
```

### Ⅱ 放入样例并入库

```powershell
copy samples\demo_handbook.pdf data\source\
# macOS/Linux: cp samples/demo_handbook.pdf data/source/

# 入库要向量服务：先开一个终端
python embed_server.py
```

另开终端（同一 conda/venv）：

```powershell
python scripts/ingest.py
```

样例是**自造 6 页**短手册（目录 + 5 节正文）。CPU 上 bge-m3 大约几十秒到两分钟；看到 `[向量层] 批 n/N` 即在推进。结束后可关临时向量服务。

验收（可选）：

```powershell
python scripts/verify_ingest.py --source "data/result/demo_handbook/chunkable_source.json" --chunks "data/result/demo_handbook/step4_chunks.json"
```

预期量级：源 **6** 页、目录区间 **5**、入库约 **5** 块、声明页次 / 页并集 **= 1**。

### Ⅲ 一键起服务并试问

```powershell
python start.py
```

| 入口 | 地址 |
|---|---|
| 问答页 | http://127.0.0.1:8032 |
| 接口文档 | http://127.0.0.1:8031/docs |
| 探活 | http://127.0.0.1:8031/ |
| 向量 | http://127.0.0.1:8030/v1/embeddings |

`start.py` 会检查依赖、权重、非空知识库与端口，依次拉起 8030 / 8031 / 8032，就绪后打开浏览器；Ctrl+C 一并停掉。缺权重或尚未入库时会打印下一步，不会静默挂起。

也可分开起：`python embed_server.py` → `python ask_server.py` → `cd web && npm run dev`。入库或改在线代码后请重启问答进程。

**演示三问**（同一会话，**不要刷新**页面）：

| # | 输入 | 预期 |
|---|---|---|
| 1 | 你好 | 闲聊一两句，右侧「参考资料」为空 |
| 2 | 支架怎么折叠 | 按手册说明折叠步骤；侧栏有引用，带来源与页码（约第 3 页） |
| 3 | 那它怎么展开？ | 仍围绕支架；应答展开步骤（约第 4 页），侧栏继续有引用 |

域外对照（可选）：问「红烧肉怎么做好吃」→ 宜拒答（文案含「没有足够依据」）。阈值 `REFUSE_MIN_SCORE=0.4`（`conf/base.py`）：曾在车手册库上测得域外余弦约 0.40～0.42，卡在边界；换库后用 `python scripts/eval_kb.py --calibrate` 重定。

---

## 怎么工作

```text
PDF → 抽取（页 + 印刷目录）→ 分块（块级页码）→ 8030 编向量 → LanceDB
问句 → 意图（闲聊/检索/跟进）→ 改写 → 向量+BM25 召回 → 截 TOP_K → 拒答或生成 → 引用
```

- **离线**：`scripts/ingest.py` 串抽取层与向量层；写库成功后才落 `step4_chunks.json`。
- **在线**：`ask_server.py` 启动时读库建 BM25；问答页只调 `POST /api/ask`。
- **过滤**：文档身份 `source` 可硬筛；动态标签 `{field,value}` 只加权，不硬切。

---

## 接口用法

```powershell
curl http://127.0.0.1:8031/
curl -X POST http://127.0.0.1:8031/api/ask -H "Content-Type: application/json" -d "{\"text\":\"支架怎么折叠\",\"session\":\"demo-1\"}"
```

响应含答案文本与 citations（来源、页码、摘录）。浏览器打开 http://127.0.0.1:8031/docs 可交互试。

命令行：`scripts/query_kb.py`（单轮）、`scripts/chat_kb.py`（多轮）。单元测试：`python -m pytest tests -q`（不调 LLM、不调 8030）。

---

## 项目结构

```text
book-nav-rag/
├── start.py                 # 一键起 8030/8031/8032
├── ask_server.py            # 问答 HTTP
├── embed_server.py          # 向量 HTTP
├── embed/                   # 向量服务实现
├── conf/                    # ROOT、开关、路径
├── offline/extract/         # PDF 抽取、目录、标签
├── offline/vector/          # 分块、LanceDB
├── online/                  # 意图、召回、生成、图编排
├── web/                     # 问答页（Vite 8032）
├── scripts/                 # 入库、验收、评测、下载权重、生成样例 PDF
├── samples/                 # 可再分发演示 PDF（进仓）
├── data/source/             # 你的 PDF（不进仓，仅 README.txt）
├── models/                  # embedding 权重（不进仓）
└── docs/                    # 内部说明，日常使用不必读
```

---

## 已知局限

- 本阶段只支持 **PDF**；无印刷目录时引用页码可能为空。
- 会话在进程内存（MemorySaver）：**刷新页面或重启问答进程会丢多轮上下文**；`session` 限 64 字符且只含 `[A-Za-z0-9_-]`，历史 turns 只保留最近 20 轮。
- 无流式输出；单问默认多次 LLM 调用（分类 / 改写 / 标签 / 生成）。
- 精排节点目前只截断 `TOP_K`，不换序。
- 前端筛选芯片为展示；按来源筛选需问句含完整来源名。
- 入库中断若留下半截暂存行，启动日志会警告；对该来源重新 `ingest` 即可。
- 第三方版权手册请只放本机 `data/source/`，不要提交或打进发布包。

---

## 许可与第三方

Copyright (c) 2026 moye

本仓库以 [GNU Affero General Public License v3.0](LICENSE)（AGPL-3.0）发布。选择 AGPL 是为了与抽取依赖 `pymupdf4llm`（AGPL-3.0 或 Artifex 商业双许可）兼容；**本仓定位为个人学习与展示，作者不将其用于商业或生产环境**。若你要商用或闭源衍生，须自行满足 AGPL 义务，或为 PyMuPDF 系列取得 Artifex 商业授权并另选许可策略——作者不提供商用支持。

| 依赖 / 资产 | 说明 |
|---|---|
| `pymupdf4llm` | AGPL-3.0 或商业授权；驱动本仓 PDF 抽页 |
| bge-m3 权重 | 不进仓；按 ModelScope 模型卡许可自行下载 |
| Chat API（如 DeepSeek） | 密钥只放本机 `.env`，勿提交 |
| `samples/demo_handbook.pdf` | 自造演示手册，可再分发 |
| 第三方厂商手册 | 只可放本机 `data/source/`，已被 gitignore |

### 名称与相近工作

| | 本仓 BookNav-RAG | SELF-RAG 论文 | PageIndex 一类思路 |
|---|---|---|---|
| 目标 | 目录导航归页 + 可核验页码引用 | 检索时反思、按需再检索 | 页/结构优先的文档索引 |
| 主路径 | 印刷目录 → 块向量 → LangGraph | reflection token | 视具体实现而定 |
| 本仓关系 | — | **不是**该论文实现 | 中心思想相近，品牌与实现独立 |

---

换 embedding 或维数后删 `data/lancedb` 再入库。完整开关与阈值在 `conf/base.py`。
