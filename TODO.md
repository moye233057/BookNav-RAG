# TODO — 公开上线（简历可写）

目标：对齐 [anyurl2text](../anyurl2text) 的公开仓标准——访客能 clone → 装依赖 → 起服务 → 问通一题；README 能写进简历；面试官能讲清 3～5 个可深挖的设计点。

权威蓝图仍是 [docs/architecture.md](docs/architecture.md)。本清单**只服务快速公开**；旧工程债见文末「公开后可做」。

一项 = 能验收：改哪些文件 / 什么现象算过 / 用什么数字或命令证明。没有数字的形容不算项。

---

## 0. 本阶段明确不做（已从待办剔除，勿回流）

这些项耗时长、偏边界，或不抬「结构 / 演示可靠性 / 面试亮点」，**公开前不做**：

| 原编号 | 项 | 为什么砍 |
|--------|----|----------|
| P2·13 | 无印刷目录来源丢页码 | 本阶段只 PDF+目录；Known Limitations 一句话即可 |
| P2·14 | token 估算低估 / 单段超限 | 现有手册未触发；不挡演示 |
| P2·16 | 同名不同扩展互相覆盖 | 只支持 PDF，演示路径碰不到 |
| P1·22 | 全表扫 / 无 ANN 索引 | 百级块演示足够；规模优化公开后做 |
| P2·23 | 前端筛选芯片不可点 | 意图抽标签已够演示；来源全名匹配写进局限 |
| P1·33 | 问界前置页《前言》进不进库 | 样本域裁决；不挡「自备 PDF 跑通」 |
| P1·34 | 标签值前缀匹配放宽 | 只影响加权 0.02；钉成局限即可 |
| P3·26 | 结构化日志 / CORS / 鉴权 | 本地演示仓不做产品网关 |
| P3·32 | pytest capability markers | 纯测试基建，不抬对外观感 |
| OS·9 | CONTRIBUTING / issue 模板 / 全套社区文件 | 有 LICENSE + README + SECURITY 一行即可 |
| — | Docker / 容器化 | 与 anyurl2text 一致：本阶段不做 |
| — | 交叉编码器精排 / OCR / Agent 沙箱 | 蓝图「本阶段不做」 |

旧「环境与跑法」里 DSH 沙箱 / `tmp_path` / 孤儿进程等**本机 Agent 笔记**不进公开清单；需要时查 git 历史或 `AGENTS.md`。

---

## 1. 硬阻断（不解决不能 push 公开）

- [x] **PUB·1 许可**（2026-10-11） — 整仓 [AGPL-3.0](LICENSE)，与 `pymupdf4llm` 兼容。README 写明：**个人学习与展示，不用商业/生产**；商用须自担 AGPL 或 PyMuPDF 商业授权。`pyproject.toml` 挂 license 文件。
  - **验收**：根有 LICENSE；README「许可与第三方」可读。

- [x] **PUB·2 密钥与隐私扫尾**（2026-10-11）
  - 密钥：用户确认本机 `DEEPSEEK_API_KEY` **早已更换**（不再列为待办）。
  - `PROCESS_ONLY = ()`（此前已清）。
  - README 无本机盘符。
  - 第三方手册评测集迁到 `scripts/eval_samples.private.json`（gitignore）；公开默认 `eval_samples.json` 只覆盖 `demo_handbook`。
  - `.env` / `/data/*` / `/models/` 已 ignore；`data/source/` 仅放行 `README.txt`。
  - **验收**：拟公开路径无真实 key、无第三方手册 PDF/大评测 grounding；私有样本本机保留。

- [x] **PUB·3 样例数据可再分发**（2026-10-11） — `samples/demo_handbook.pdf`（自造 6 页，~8KB，可再生）；第三方车手册仅本机 `data/source/`、不进仓。
  - **验收**：README 路径只依赖 `demo_handbook`；`verify_ingest` 默认也指向它。

- [x] **PUB·4 命名**（2026-10-11） — 英文仓名 **`book-nav-rag`**；简历系统名 **BookNav-RAG 目录导航问答**。文档 / `pyproject` / 前端包名已改；本机文件夹仍叫 `self-rag` 时需关 Cursor 占用后执行：`Rename-Item E:\Project\Individual\self-rag book-nav-rag`。与 SELF-RAG 论文 / PageRAG 产品区分见 README。
  - **验收**：README / pyproject / 简历标题一致。

---

## 2. 安装与复现（对齐 anyurl2text「访客 15 分钟」）

对照 anyurl2text：一句定位 → clone → `.env` → 一键或少步起服务 → 表格列出端口。本仓现状：三进程手起、conda 长文、无截图、无 License 段、演示句绑死车手册。

- [x] **RUN·1 一键拉起**（2026-10-11） — 根目录 `start.py`：检查依赖 / 权重 / 非空库 / 端口 → 起 8030/8031/8032 → 探测就绪 → 开浏览器；Ctrl+C 收子进程树。缺权重或未入库打印下一步。
  - **验收**：新人入口命令是 `python start.py`；缺前置时不静默挂起。

- [x] **RUN·2 README 访客化**（2026-10-11） — 按 anyurl2text 主线重排：介绍 → 快速开始 Ⅰ/Ⅱ/Ⅲ → 怎么工作 → 接口 → 结构 → 局限 → 许可；去掉 Agent 长文；亮点表 + 与 Self-RAG 区别。截图仍缺（公开前可补）。
  - **验收**：不读 `docs/` 能从 README 跑通最小路径。

- [x] **RUN·3 最小演示路径写死数字**（2026-10-11） — `samples/demo_handbook.pdf`（自造 6 页）+ `scripts/make_demo_pdf.py`；README 演示三问不绑品牌；`PROCESS_ONLY` 改回 `()`。顺带：`pdf.py` 拆开 pymupdf4llm 拼成一行的多条目录（`tests/test_pdf_catalogue.py` 钉住）。
  - **验收**：样例目录抽出 5 区间；入库后 verify 口径见 README（约 5 块、均摊 1.00）。端到端三问交用户本机跑。

---

## 3. 演示可靠性（少改代码，挡当场翻车）

- [x] **REL·1 写入半截来源**（2026-10-11） — `replace_source`：暂存来源 `::__writing__` → 删旧 → 写正式 → 删暂存；`load_payload` / 近邻跳过暂存并告警。`tests/test_replace_source_safe.py`。
  - **验收**：monkeypatch 暂存 add 失败 → 旧来源行数不变。

- [x] **REL·2 会话字段护栏**（2026-10-11） — `AskBody.session` 限 64 字符 + `[A-Za-z0-9_-]`（超长/脏字符 → 422）；`AskState.turns` 用 `_clip_turns` 只留 `SESSION_TURNS_MAX=20`。README 已知局限已写刷新/重启丢多轮。`tests/test_session_guard.py`。
  - **验收**：超长 session ValidationError；turns 截断到 20。

- [x] **REL·3 拒答阈值有依据**（2026-10-11） — `conf/base.py` 旁注 2026-10-08 实测两条负样本余弦与 0.4 的关系；README 演示节写域外问法与 `--calibrate`。未改阈值数值（换公开样例库后由你本机 calibrate）。
  - **验收**：注释与 README 有数字来源；端到端域外拒答交你本机验。

---

## 4. 面试亮点（要能讲清，且仓里看得见）

下列能力**代码里大多已有**；公开阶段的活是「写进 README 亮点表 + 保证可演示/可答」，不是再堆功能。

| 亮点 | 仓内落点 | 面试官可能追问 | 公开阶段要补的 |
|------|----------|----------------|----------------|
| 块级页码 + 入库验收 | `chunk.py` 块级 `pages`；`scripts/verify_ingest.py`（声明页次/页并集=1） | 为什么不能整节复制页码？均摊倍数怎么验？ | README 给改前/改后数字（已有 3.21→1.00） |
| 标签加权不硬切 | ADR-0035；`tag_match_count` + RRF 加分 | 为什么不用硬过滤？多文档同字段多值会怎样？ | 一句对比「硬切→空命中拒答」 |
| 向量挂了不 500 | `retrieve_hits` → BM25 + `lexical_fallback`；拒答改词面规则 | 降级后质量如何？拒答为什么不能沿用余弦？ | README 写「停 8030 仍可问」验收句 |
| 印刷目录动态扫描 | `pdf.py::_select_catalogue_pages` | 写死预览页数会怎样？ | Known Limitations：无目录 PDF 的页码策略 |
| 在线同路径评测 | `eval_kb.py` → `ask_once_core`；73 样本机制 | Hit@k 怎么定义？闲聊注入为何必须全未命中？ | 用**可公开样例**重跑并贴 Hit@1/Hit@k/拒答数字（旧车手册数字勿当公开成绩） |
| 意图分流 | 闲聊 / 检索 / 身份追问强制检索 | 「资料来自哪个品牌」为何不能判闲聊？ | 演示三问覆盖 |

可选加分（有余力再做，**不挡公开**）：

- [ ] **HL·1 单问 LLM 次数**（原 P1·21 最小刀） — 分类+改写+抽标签合并为一次结构化输出，或复用 `ChatOpenAI` 客户端。验收：单问 LLM 调用从 4 降到 ≤2，并在日志或评测里可数。讲得清「延迟从哪来」。

不做也要在 README Known Limitations 写明：无流式、会话仅内存、精排只截断不换序。

---

## 5. 公开当天检查单

```text
[x] LICENSE + README 许可段（个人展示 / AGPL-3.0）
[x] 密钥已更换（用户确认）；拟公开树无 .env / 无盘符 / 第三方手册不进仓
[x] PROCESS_ONLY = ()
[x] 公有样例 PDF + 演示三问可复现
[x] start.py + 端口表（截图仍缺）
[x] README：客观介绍 / 局限 / 命名说明（已去掉「面试可深挖」表；截图仍缺）
[x] REL·1/2/3 演示可靠性
[x] 本机文件夹 `self-rag` → `book-nav-rag`
[ ] pytest 全绿（本机）：python -m pytest tests -q
[x] git init → 首 commit 目检 → push GitHub / Gitee（`b666325`）
```

---

## 6. 公开后可做（不进本阶段排期）

写入原子性完整版、会话落盘+TTL、ANN/规模、前端筛选 UI、标签前缀匹配、前置页策略、token 估算、CI、流式输出、交叉编码器。需要时从 git 历史里的旧 TODO 编号捡回。

---

## 7. 完成判定

1. 陌生人只靠 README 能否在一台干净机器上问通一题？
2. 简历上能否用一句话概括，并用上表任一亮点撑 3 分钟追问？
3. 公开树里是否还有密钥、版权手册、本机路径？
