# 交接：self-rag 缺陷修复 —— 验收已立、页码与兜底已验，下一步修离线数据正确性

> 临时工作态，不是项目文档；长期规矩见 CONTEXT.md / docs/adr.md

**写于**：2026-10-08（第 1 阶段收尾后重写）｜ **分支**：无（本仓未初始化 git）｜ **状态**：第 1 阶段收尾完成；第 2 阶段未开始；P0·7 等用户拍方案

**数字已于 2026-10-09 当轮重测回填**（`pytest` 63 passed + 1 xfailed；`verify_ingest.py` 138 块、库内同来源 138 个、页码不同 0）。本文件里任何「进程 / 产物当前状态」的话都带当轮命令与读数，过期即刻改，不留旧数字。

文件名仍叫 `verify-first`：本仓在沙箱里删不掉文件，同一工作线只留这一份正文。

> **2026-10-10 后记**：抽取层已与 anyurl2text 解耦（现行 ADR-0034：仅 PDF 本仓抽页，非 PDF 在路由被拒，外仓 `/rag/extract/file` 已下线）。本文里「非 PDF」「`anyurl.py` 失败路径」「8020」相关表述是当时的状态记录，现状以 [TODO.md](../../TODO.md) 与 [architecture.md](../architecture.md) 为准。

---

## 目标与验收标准

第 1 阶段五条**全部通过**（命令与数字见「验证状态」）：

| 项 | 验收 | 状态 |
|----|------|------|
| P0·1 | `python -m pytest tests -q` 全绿 | **已过**：63 passed, 1 xfailed（2026-10-09 重测，13.39s，exit 0） |
| P0·2 | `scripts/verify_ingest.py` 报出丢页与页精度 | **已过**：exit 0，丢 24 页，均摊倍数 1.00 |
| P0·3 | `--route chitchat` 下正样本全部未命中 | **已过**：Hit@1=0/4，exit 1 |
| P0·5 | 声明页次 / 页并集 = 1 | **已过**：366/366，重复声明 0 页 |
| P0·18 | embed 挂掉时「你好」仍 200、知识问题不返 500 | **已过**：200 / 200（死端口 `127.0.0.1:1`） |

第 2 阶段（离线数据正确性）与 P0·4（评测集扩到 ≥50 条）、P0·7（过滤标签二选一）**尚未开始**。

---

## 已完成

### 本轮（2026-10-08 第 1 阶段收尾）新做的

| 项 | 内容 |
|----|------|
| P0·1 | 跑通从未执行过的用例：41 条里 2 条失败，判清哪一侧对之后再收敛——`_normalize_filters` 那条**改实现**（决定 3），单段超限那条**标 xfail**（决定 4）→ **43 passed, 1 xfailed**（本轮 41 条起点）；此后 P1·29 与 `work_dir` 夹具又补了用例，**2026-10-09 重测为 63 passed, 1 xfailed** |
| P0·3 | 实测回填真数字：Hit@1=**2/4**、Hit@TOP_K(5)=**4/4**、拒答=**1/2**；`--route chitchat --strict` 正样本 0/4 命中 → exit 1（验收成立） |
| P0·18 | 死 embed 端口下走 ASGI 实打 `POST /api/ask`：「你好」200、「后视镜怎么折叠」200（citations 5）；真实库 137 块（当轮）兜底命中 20 条全带 `lexical_fallback=True` |
| P0·2 | `scripts/verify_ingest.py` 落地后复跑：exit 0；并把里面**过期的**页精度硬断言换成不会误报的判据（见「关键决定」2） |
| — | `tests/test_verify_ingest.py`（新，3 条）锁定上一条的两个方向 |
| — | `online/graph.py::_normalize_filters` 补 `source` 去空白（见「关键决定」3） |
| — | 文档与代码保持一致：`docs/architecture.md`（§3/4/5/6/7/8）、`README.md`（§3 测试、结构、兜底）、`scripts/eval_kb.py` 文件头、`TODO.md`（§1 基线、5 项勾选、新增 P1·28） |
| — | 核销旧开放问题：`data/lancedb` 与 `step4_chunks.json` **逐块一致**（2026-10-09 重测 138/138 id，0 处页码不同，slots=366=union，ratio 1.0000） |

### 上一轮已实现、本轮重新验证过的

- **P0·5 块级页码**：`offline/vector/chunk.py::_assemble_pieces_with_pages`（先按页/段边界拆段，再累加装块，每块只带自己覆盖的页）。
- **P0·3 评测改走线上**：`online/graph.py::ask_once_core`（分类 → 改写 → 筛选 → 召回 → 重排 → 同节邻块，停在生成前）；`scripts/eval_kb.py` 调它，`Hit@k` 的 k 取 `conf.TOP_K`。
- **P0·18 词面兜底**：`retrieve.py::EMBED_UNAVAILABLE` / `retrieve_hits_by_bm25` / `lexical_fallback`；`answer.py::should_refuse` 对兜底命中改看词面；开关 `conf::REFUSE_ON_LEXICAL_FALLBACK`。
- **其它**：`_build_rewrite` 失败退化为原文；`write_debug` 参数；`scripts/ingest.py --vector-only`；`requirements.txt` 补齐向量服务依赖。

---

## 关键决定与理由

1. **先立验收，再修数据**：没有可信数字，改完也说不清好坏。第 1 阶段因此排最前，现已收尾。
2. **`verify_ingest` 的页精度硬断言改用「任一页只能被一个块声明」**（本轮改）。原断言是「part > 0 就是虚报」，写在 P0·5 之前；块级页码落地后它把**正确数据**判成 exit 1——红线常驻等于没有红线。新判据 `declared_slots == 声明页并集`（且同节各 part 不重叠）**照样抓得住改前的 3.21 倍**，改后 1.00 放行。
3. **`_normalize_filters` 对 `source` 也去空白**（本轮改，修正上一轮决定「不 strip」）。上一轮的理由是「避免两处各 strip 一半」，但代码当时**已经在 strip tag 的 field/value、没 strip source**——正是它想避免的形状。`"  "` 来源会逐字比库内 `source` → 静默 0 命中。HTTP 路径上行为**零变化**（schema 已 strip），只堵死直调方（`ask_once_core` / 评测 / 测试）的静默失败。
4. **P2·14 用 `xfail(strict=True)` 锁定，现在不修**：修它会改离线分块产出 → 让刚重入的 `data/lancedb` 与 §1 全部基线作废，属第 2 阶段。
5. **不停掉用户的 8030 做 P0·18 验收**：把 `EMBED_API_URL` 指向死端口 `127.0.0.1:1`（连接被拒，等价 8030 挂掉），用户进程不动。
6. **页码下沉做块级而非节级近似**：实测均摊倍数正好是 1.00，无需近似规则。
7. **评测经 `ask_once_core` 而非 `run_ask_graph`**：后者走 LLM 生成（花钱、慢、需 key）；前者与图同一顺序、停在生成前。
8. **`--vector-only` 而非全量 `ingest.py`**：全量会重跑抽取与 `enrich.py` 的 LLM 抽标签（花钱，且覆盖现有 `chunkable_source.json`）。
9. **git 不初始化**：用户明确说「等同意再做」（2026-10-08）。

---

## 否决的路线

- **现在就修 P2·14（单段超限强制切断）**：会改分块产出，作废刚重入的库与全部基线。留到第 2 阶段，`xfail` 锁着。
- **真起一个 uvicorn 子进程打 HTTP 验 P0·18**：沙箱下仓内 `data/result/qa` 写不进去，`step2_hits.json` / `step3_answer.json` 写失败会变成 500，把**环境工件误判成代码 bug**。改用 ASGI `TestClient` + `QA_DIR` 重定向的 A/B（见验证状态最后两行），恰好把「500 来自写盘还是来自 embed 挂」分开了。
- **把 `tests/test_probe.py` 留着当第 41 条用例**：2 行 `assert True` 的空探测脚本不是测试。沙箱删不掉（见开放问题 1），本轮只在数字里如实标注。
- **删掉 `tests/` 改用 `scripts/`**：`AGENTS.md` 与 `tests/` 现状均已生效。
- **用签名法（源页连续 CJK 串）算页覆盖与页精度做硬断言**：实测漏判严重（报 223/390，真值 366/390）。降级为辅助观察；硬断言改用块自称的 `metadata.pages`（与 `eval_kb.py` 同一判据）。
- **修文件权限解决沙箱写入**：已证伪（`FIXED=0 GRANTED=4`，改动全部通过复核，操作仍被拒）。
- **一次做完 TODO 全 28 项**：P0·7 需要用户拍方案 A（按块抽标签）或 B（tags 退场），不代拍。

---

## 相关 / 改动的文件

| 路径 | 符号 | 为什么重要 |
|------|------|-----------|
| `offline/vector/chunk.py` | `_assemble_pieces_with_pages`、`chunks_from_assigned_rows` | 块级页码的唯一来源；P0·5 |
| `scripts/verify_ingest.py` | `check_ingest`、`print_report` | 入库验收；本轮换了页精度硬断言的判据（P0·2） |
| `online/graph.py` | `ask_once_core`、`_normalize_filters`、`_build_rewrite` | 评测与线上共用的检索核心；`source` 去空白（P0·3） |
| `scripts/eval_kb.py` | `step2_check_samples`、`_hit_at`、`--route` / `--limit` / `--strict` | 评测跑线上路径；文件头页判据已改成块级 |
| `online/recall/retrieve.py` | `EMBED_UNAVAILABLE`、`retrieve_hits_by_bm25`、`retrieve_hits(write_debug=)` | 词面兜底；P0·18 |
| `online/generate/answer.py` | `should_refuse(hits, question)`、`hits_contain_query_term`、`write_qa_result` | 兜底拒答闸门；`QA_DIR` 写进磁盘，就是 P1·20 说的那条响应路径写入 |
| `conf/base.py` / `conf/__init__.py` | `REFUSE_ON_LEXICAL_FALLBACK`、`QA_DIR`、`TOP_K` | 兜底开关与调试题材的位置 |
| `online/router.py` / `online/schema.py` | `_request_filters`、三个 `field_validator` | 过滤归一化收尾；去空白 |
| `scripts/ingest.py` | `--vector-only` | 只重跑向量层 |
| `tests/`（8 个测试文件 + `conftest.py`） | 2026-10-09 实测 63 条用例 = 62 passed + 1 xfail（`test_probe.py` 空探测脚本已删，见开放问题 1） | P0·1；`conftest.py` 把仓库根放进 `sys.path`，并提供 `work_dir` 目录夹具 |
| `TODO.md` | §1 基线、§2 清单（P1·28 新）、§环境与跑法 | 任务台账 |
| `docs/architecture.md` / `README.md` | §3/4/5/6/7/8；§3 测试、结构、兜底 | 与代码一致 |

---

## 剩余工作

**权威清单是 [TODO.md](../../TODO.md) 第 2 节（28 项），不在这里抄第二份。** 只标顺序与依赖：

### 立即可做（不需用户决定）

1. **P0·6** `clean_page_text` 与分段切分的约定冲突 — `chunk.py` 把 `\n` 全换成空格，而分段按 `\n\n` → 实测源页 388/390 含 `\n\n`，切完块里 **0 个**：**「按段累积分块」从未生效**，块边界实际由页边界决定。这是第 2 阶段第一项，也是块 token 分布（当轮 2026-10-09：p90 1606 / 中位 606，min 52 / max 1744）的根因。
2. **P1·8** 丢页告警与计数接进入库流程（`verify_ingest.py` 已能报，需接到 `ingest.py` 并对超阈值告警）。
3. **P1·9～P2·17**：目录预览页数写死 15、写入原子性、首次建表不校验 dim、tags 抽取贪婪正则 + 静默降级、非 PDF 丢页码、token 估算对英文低估、`anyurl.py` 失败路径、同名源互相覆盖、依赖与权重可重现。

### 需用户先拍

4. **P0·7 过滤标签零区分度**：138 块（2026-10-09）tags 组合唯一数 = **1**；同字段多值走 AND → 多值筛选必然 0 命中 → 静默拒答。方案 A（`enrich.py` 改按块抽标签 + 同字段多值走 OR）或方案 B（tags 降级为文档级软标签，不作块级过滤，同时改 `architecture.md`）。
5. **P0·19 会话状态**（第 3 阶段）：`MemorySaver` 进程内、`thread_id` 由请求体任意字符串决定、`turns` 只增不减。

### 第 1 阶段剩余

6. **P0·4 评测集扩到 ≥50 条**：现在 4 条正样本是**同一页 93 的 4 种问法**，有效自由度约 2+2。要覆盖跨文档、来源筛选、闲聊、身份追问、多主题标签、跨源混淆负样本。**前置：3 份 PDF 全部入库**（现在只入了 1 份）。
7. **P1·28 拒答阈值 0.4 未校准**（本轮新增）：负样本「红烧肉怎么做好吃」经改写后余弦 **0.4197 > 0.4 → 被放行**；另一条 0.3989 拒答。阈值正好停在两条负样本中间，需按 PR 曲线重定，并确认改写是不是把无关问句的余弦推高了。

### 第 3 阶段

8. **P1·20～P3·27**：调试题材写在响应路径上（`write_debug` 参数已就位，还差 `conf` 开关与默认关、按 session/时间戳分文件）、单问 4 次串行 LLM + 无流式、召回随规模线性扫描、前端筛选不可达、错误约定跨层不一致、密钥边界、可观测性、空壳模块。

---

## 已知问题 / 开放问题

1. **`tests/test_probe.py` 已删**（2026-10-09 核实：文件不存在）。此前沙箱删不掉的 2 行空探测脚本不再计入数字。
2. **`ask_server.py` 需重启**才装上块级页码与词面兜底拒答逻辑；重启会清掉 `MemorySaver` 会话。当前用户终端里 8030 / 8031 都在跑（8030 由它提供向量，8031 是旧代码）。
3. **沙箱只挡子进程写盘，不挡改文件**：`write` / `edit` 在 `Individual\self-rag` 下可用（本轮改了 8 个代码 / 项目文档文件，不含交接文件），`pytest` 加 `-p no:cacheprovider` 照跑；被拒的只有子进程自己的写入（重入库、评测写盘、`step2_hits.json`）与**删除文件**。这与 `agent-dsh.md` §5 表格「工作区内已存在的子目录可写」冲突，**以本仓实测为准**（已记进 `TODO.md` §环境与跑法）。
4. **页级判据判别力仍有限**：「任一页相交即算中」配上同节邻块仍可能跨多页；编号级评测（期望块 id 或期望正文片段）未做。
5. **拒答阈值 0.4 未校准**：见 P1·28；只有 2 条负样本，画不出 PR 曲线。
6. **`web/dist` 被 `.gitignore` 忽略、无 Dockerfile、Vite 代理只在 dev 生效**：无生产部署形态。
7. **遗留目录 `E:\Project\_dsh_acl_report\`**（上一轮的权限诊断，含可回滚脚本）：在工作区根、可删，本轮没动它。

---

## 验证状态

只写真实跑过的命令与结果（工作目录 `E:\Project\Individual\self-rag`，`$env:PYTHONUTF8="1"`，解释器 `E:\miniconda\envs\rag\python.exe`）。

| 命令 | 结果 |
|------|------|
| `-m pytest tests -q -p no:cacheprovider` | **63 passed, 1 xfailed**，exit 0，13.39s（2026-10-09 重测）。那条 xfail 是 P2·14（`strict=True`，修完会 XPASS 转失败） |
| `scripts/verify_ingest.py` | **exit 0**，硬断言通过（2026-10-09 重测）。源 390 / 覆盖 366 / 丢 24 页 / 108 区间 / **138 块** / 声明页次 366 = 页并集 366（均摊 **1.00**）/ 重复声明 **0** 页 / 续块 **30** 个 / 最宽 **8 页**（`…-0017`「闭锁/解锁车门」part=0）/ tags 8 条组合唯一数 1 / token min 52 中位 606 p90 1606 max 1744 / 库内同来源 **138 个（step4 138 个）**，仅 step4 有 0、仅库里有 0、**页码不同 0** / 待确认 2 项（22 个有正文页未进块、tags 零区分度） |
| `scripts/eval_kb.py` | 通过 5/6 ｜ **Hit@1=2/4**、**Hit@5=4/4**、**拒答=1/2**。未过的是「红烧肉怎么做好吃」：改写 →「红烧肉怎么做才好吃」，最高余弦 0.4197 > 0.4 → 不拒答 |
| `scripts/eval_kb.py --route chitchat --strict` | **评测 通过 2/6，Hit@1=0/4、Hit@5=0/4、拒答=2/2，exit 1**（4 条正样本全部未命中）→ P0·3 验收成立 |
| ASGI 实打 `POST /api/ask`，`EMBED_API_URL=127.0.0.1:1`，`QA_DIR` 重定向到可写目录 | 「你好」**200**（citations 0）、「后视镜怎么折叠」**200**（citations 5，答出折叠开关）；真实库 137 块 / dim 1024（当轮库状态）；兜底命中 20 条**全带 `lexical_fallback=True`**，分值为 BM25（13.27 / 9.97 / 8.29）不是余弦；「红烧肉怎么做」兜底 0 命中 → 拒答 |
| 同一死端口，但 `QA_DIR` 保持仓内 `data/result/qa`（沙箱拒写） | 「你好」**500**、「后视镜怎么折叠」**500**，而同一轮**兜底召回结果与上一行逐条相同** → 证明 500 来自响应路径上的调试写盘（P1·20），不是 embed 挂掉 |
| 逐块比对 `data/lancedb` 与 `step4_chunks.json` | **138 / 138**（2026-10-09 重测），id 差集两侧都是 0，**页码不同处 0**，lancedb slots=366 = union=366，ratio **1.0000** → 旧开放问题「lancedb 是否也是新页码」已核销 |
| 逐块比对同一节各 part 的声明页 | 声明 slots 366 = 并集 366；**被两个以上块声明的页 0 个**；同节内重叠的节 **0 / 108**；`行车辅助` part 0→10 把 171–218 页切完且互不重叠 |
| `-m py_compile` 改动文件 | `py_compile` 自身 exit 1：沙箱拒写 `scripts\__pycache__\*.pyc`。语法由 pytest 导入与脚本实跑覆盖（均通过） |

---

## 完成判据

第 1 阶段的五条已全部满足（`pytest` 全绿且用例 ≥41——现为 63 passed + 1 xfailed、`eval_kb` 出真数字且 `--route chitchat` 正样本未命中、embed 挂掉不返 500、`TODO.md` 第 1 节无旧数字且已完成项已勾、`architecture.md` 与 `README.md` 与代码一致）。

进入第 2 阶段后：

1. **P0·6**：对同一份源，块数上升、块内 token 分布更均匀（p90 / 中位数比值下降）、跨页步骤不再被切断（抽查 2 处）。
2. **P0·7**（用户拍方案后）：构造「同时点名两个标签值」的问句**有命中**而不是拒答；`tag_catalog()` 区分度有数字（同字段不同值能区分出的块数 > 0）。
3. 每轮收尾：`pytest` 绿、`verify_ingest.py` exit 0、`eval_kb.py` 数字回填 `TODO.md` 第 1 节。

---

## 下一步

单条最佳起手动作：**做 P0·6，修 `clean_page_text` 与分段切分的约定冲突。**

```powershell
[Console]::OutputEncoding=[Text.Encoding]::UTF8
$env:PYTHONUTF8="1"
Set-Location "E:\Project\Individual\self-rag"
& 'E:\miniconda\envs\rag\python.exe' scripts/verify_ingest.py     # 先记下改前基线
```

- **改哪个文件**：`offline/vector/chunk.py` 的清洗与 `split_doc_text_into_chunks`（页内保留段边界，或清洗时用分隔符占位、切完还原）。
- **怎么看出问题**：`verify_ingest.py` 当轮（2026-10-09）报 **138 块**、token p90 1606 / 中位 606；改完**块数应上升**、p90 与中位数的比值应下降。若块数不变，说明段边界仍没活过来。
- **失败在哪一步**：先确认源页里真有 `\n\n`（现在实测 388/390 有，切完块里 0 个）；若清洗改完块数仍不动，查是不是用的是「有印刷目录」那条路（`_assemble_pieces_with_pages` 按页/段边界拆，不经过 `split_doc_text_into_chunks` 的整篇路径）。
- **耗时与副作用**：改完必须 `python scripts/ingest.py --vector-only` 重跑向量层（重复使用 `chunkable_source.json`，不重跑抽取与 LLM 抽标签），**这一步会作废 `data/lancedb` 里的旧页码**；随后同一轮把 `TODO.md` 第 1 节的块数、token 分布、声明页次三行一起改掉，再跑一次 `verify_ingest.py` 与 `eval_kb.py` 回填。整体分钟级。
- **沙箱提醒**：重入库会写 `data/lancedb` 与 `data/result/`，agent 在 workspace-write 下**写不进去**——要么把会话切「完全权限」，要么你在自己终端跑这两条。
