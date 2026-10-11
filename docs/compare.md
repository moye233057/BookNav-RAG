# GitHub RAG 产品设计对照

读 `E:\Project\GitHub\RAG` 里的实现，按各仓 README / 代码自己的叫法写设计；最后一节对照 `moye-notes/09-AI/RAG` 已有笔记。不把七家模块名收成一套。向量库与自建选型不在本文拍板。

分仓细读（技术栈 / 模块 / 链路）就是下面各节：一篇一仓，顺序与 `E:\Project\GitHub\RAG\` 下的目录一致。

产品仓路径均相对 `E:\Project\GitHub\RAG\`。

---

## 仓清单

| 目录 | 仓自己怎么定位 | 算不算产品 |
|------|----------------|------------|
| `ragflow-main` | RAG + Agent 上下文引擎 | 是 |
| `ragflow-plus-main` | RAGFlow 的中文行业特解 | 是（旧 fork） |
| `QAnything-qanything-v2` | 本地任意格式知识库问答 | 是 |
| `anything-llm-master` | All-in-one 私有 ChatGPT（RAG 是其中一块） | 是 |
| `bisheng-main` | 企业 LLM 应用 DevOps 平台 | 是（平台，RAG 是领域模块） |
| `WeKnora-main` | RAG + ReAct Agent + 自动 Wiki | 是 |
| `rag-knowledge-system-main` | 通用知识库管理平台 | 是（体量最小的可部署产品） |
| `FlowRAG-main` | Continual Learning RAG 研究框架 | 否，附录 |

---

## ragflow-main（RAGFlow）

依据：`README.md` / `README_zh.md`、`docs/basics/rag.md`、`AGENTS.md`、`rag/`、`deepdoc/`、`api/db/services/dialog_service.py`。

自称把复杂非结构化文档变成可检索、可引用、可编排的上下文层。README 用 System Architecture 图，代码上能对上的块是：

- 接入：`web/`、`api/`、`sdk/`、Chat Channels
- 应用：Chat/Dialog、Agent Canvas（`agent/`）、`memory/`、`mcp/`
- RAG 核心：`deepdoc/`（OCR、版面、MinerU/Docling）、`rag/`（task worker、混合检索、Embedding、rerank、GraphRAG、RAPTOR、Advanced/Agentic RAG）
- 文档引擎：全文 + 向量写进同一 Doc Engine（默认 Elasticsearch，可切 Infinity / OpenSearch / OceanBase）
- 基础设施：MySQL、Redis、MinIO；另有 Go 摄入栈 `cmd/` + `internal/ingestion/`

`docs/basics/rag.md` 把概念 RAG 写成三阶段：数据处理与向量化 → 检索 → 上下文构建与生成，并强调 **Hybrid Search（向量 + BM25/关键词）** 才是工业级检索层。

离线：`rag/svr/task_executor.py` 吃 Redis 队列。按 `task_type` 走标准解析、`raptor`、`graphrag`、`memory`、wiki 等。标准路径是 MinIO 拉文件 → `build_chunks()` 按 `parser_id` 选 `rag/app/*` 模板分块 → `embedding()` → `insert_chunks()` 写入租户索引 `ragflow_{uid}`。

在线：`dialog_service.async_chat`。metadata filter → 表有 `field_map` 则 `use_sql` → 多轮合并 / 跨语言 / `keyword_extraction` → `Dealer.retrieval()` 混合召回 + rerank → 可选 TOC、parent-child、Web Search、`use_kg` → `kb_prompt` → 流式生成 + `insert_citations`。Agent 走 Canvas / `agentic_rag`，不是单次 RAG。

沾边笔记：分块（《06》）、向量检索（《07》）、GraphRAG（《08》）、OCR/版面（`Multimodal/`、MinerU）、引用生成。仓内还有笔记几乎没写的：Doc Engine 混合索引、RAPTOR、Canvas Agent、Go 摄入、租户权限。

---

## ragflow-plus-main

依据：`README.md`、`management/`、`rag/svr/task_executor.py`、`graphrag/`。

自称在 RAGFlow 上做中文落地：独立 `management/` 后台、前台权限收缩、MinerU 替换 DeepDoc、引用块配图、文档撰写 `write_service`。代码代际是约 v0.5 的纯 Python fork，没有上游的 `deepdoc/`、`agent/`、`internal/`（Go）、`memory/`、`mcp/`。

检索仍是 `rag/nlp/search.py` 混合检索 + `rerank_model` + `insert_citations`。GraphRAG 在顶层 `graphrag/`，主 `dialog_service.chat` 不如上游那样内置 KG 召回。解析主路径在管理侧 `document_parser.py`（magic_pdf / MinerU）。

沾边笔记：MinerU、混合检索、旧结构 GraphRAG。它说明「同名产品」会分叉：plus 换的是治理与解析，不是检索公式。

---

## QAnything-qanything-v2

依据：`README_zh.md`、`qanything_kernel/`、`scripts/entrypoint.sh`、`core/local_doc_qa.py`、`core/retriever/parent_retriever.py`。

自称本地可离线的任意格式知识库问答。核心口号是 **一阶段 Embedding 召回 + 二阶段 BCE Rerank**，用来对抗大规模检索退化。启动六个 Python 进程：embedding / rerank / OCR / pdf_parser / insert worker / Sanic 主 API。前端 `front_end/`。

索引：Parent-Child。Milvus 存 child 向量；MySQL `MysqlStore` 存 parent 全文；`hybrid_search` 打开时 Elasticsearch 存 child 全文做 BM25，与 Milvus 结果去重合并。没有 GraphRAG。

在线：`LocalDocQA.get_knowledge_based_answer`。有历史则 `RewriteQuestionChain` 得到 `condense_question` → `ParentRetriever` → 可选 DuckDuckGo → BCE rerank 与阈值过滤 → FAQ 高分则跳过 LLM → 按 token 裁 `source_documents` → OpenAI 兼容接口生成。`user_id` 软隔离知识库，没有完整 RBAC。

沾边笔记：分块（这里是父子两层，不是《06》的按句组块）、向量库、rerank（耗时案例里有，基础文不当一等模块）、OCR/PDF 解析。没有图、没有笔记里的停用词/jieba 预处理。

---

## anything-llm-master

依据：`README.md` Technical Overview、`server/utils/chats/stream.js`、`collector/`、`server/utils/vectorDbProviders/`、`server/utils/agents/`。

自称私有 ChatGPT 一体化：文档 RAG + AI Agent + 多 LLM/向量库可插拔 + 多用户。分层是 `frontend/`、Express `server/`、独立解析微服务 `collector/`，外加 embed widget / 浏览器扩展。

RAG 主路径：collector 把文件/链接变成 `{ pageContent, metadata }` → 落 `storage/documents/*.json` → `TextSplitter` → 可插拔 EmbeddingEngine → 写入向量库 namespace（默认 LanceDB）。检索是 query embed + cosine，workspace 可开 Native Rerank。**Pin 文档不走向量，整篇塞进 prompt。** 无 BM25 文档检索、无 GraphRAG。

聊天：`streamChatWithWorkspace`。slash command → 匹配 Agent 则 **退出标准 RAG** 走 Aibitat / Agent Flows / MCP → 否则历史 + Memories + pinned + 向量召回 + `fillSourceWindow` 引用窗口 → `chatMode=query` 且无 context 则拒答 → 压缩消息 → 流式生成。Docker 版有 admin/manager/default 与 workspace 成员。

沾边笔记：解析（collector / Tesseract，对笔记里 MinerU/OCR）、TextSplitter（《06》《07》）、向量近邻（《07》）。Agent 在这个仓里是旁路，不是检索模块。笔记没有 Pin 全文直注、没有「query 模式无命中则拒答」。

---

## bisheng-main（BISHENG）

依据：`README_CN.md`、`docs/architecture/`（尤其 `04-knowledge-rag.md`）、`src/backend/bisheng/knowledge/`、`bisheng_langchain/rag/`、`workflow/nodes/rag/`。

自称企业 LLM 应用 DevOps：工作流 + 知识库 + 灵思 Agent + 评测/微调。RAG 不是整个产品，是 `knowledge/` 领域。官方管道名是 **Load → Transform → Ingest**，Celery 队列 `knowledge_celery`。

离线：上传 MinIO → Loader（PDF 可选 etl4lm / mineru / paddle_ocr / local）→ `SplitterTransformer`（`ElemCharacterTextSplitter`）→ 并行写入 **Milvus 向量 + Elasticsearch BM25**。换 Embedding 可从 ES 读 chunk 重建 Milvus。

在线：工作流 `RagNode` / `BishengRagPipeline`。检索器在 `bisheng_langchain/rag/init_retrievers/`：Keyword / BaselineVector / Mix / Ensemble / SmallerChunks。可选 YAML rerank、`citation/`（chunk 带 bbox/page 方便预览定位）。Query 侧几乎没有独立 LLM 改写，只有字符串规范化。无 GraphRAG。有 RAGAS 与 `evaluation/`。权限是完整 RBAC + 多租户文档。

沾边笔记：解析（MinerU / PaddleOCR）、分块、向量 + 关键词（《07》把倒排和向量并列成知识库分类，本仓做成默认双写）、引用、评测。工作流编排、RBAC、bbox 溯源是笔记没有的产品层。

---

## WeKnora-main

依据：`README_CN.md`、`internal/application/service/chat_pipeline/`、`internal/application/service/retriever/`、`internal/infrastructure/chunker/`、`docreader/`、`internal/types/task.go`。

腾讯开源。自称模块化 RAG / ReAct Agent / 自动 Wiki。在线不是单函数，是 `chat_pipeline` 的 **EventManager + Plugin 链**。`rag_stream` 典型顺序：

`LOAD_HISTORY` → `MEMORY_RECALL` → `QUERY_UNDERSTAND`（改写 + 意图，模板 `config/prompt_templates/rewrite.yaml`）→ `CHUNK_SEARCH_PARALLEL`（dense / BM25 / Neo4j 实体并行）→ `CHUNK_RERANK` → 可选 `WEB_FETCH` → `CHUNK_MERGE`（去重、父子扩展、FAQ、邻接块）→ `FILTER_TOP_K` → 可选 `DATA_ANALYSIS` → `INTO_CHAT_MESSAGE` → `CHAT_COMPLETION_STREAM`。

离线 Asynq：`TypeDocumentProcess` 主链是 DocReader → Chunking（`chunker/` 标题/启发式/父子）→ Embedding（`keywords_vector_hybrid_indexer` 向量+BM25）→ 可选多模态。PostProcess 再摘要、问题生成、`graph.go` 抽到 Neo4j、Wiki、自动标签。解析是 gRPC `docreader`（OCR / VLM / MinerU 等）。另有 ReAct `internal/agent/`、空间 RBAC、评测 handler。主体语言 Go。

沾边笔记：query 改写、混合检索、GraphRAG（《08》在本库案例只做到离线 CSV；这里离线抽图 + 在线 `search_entity`）、父子分块、rerank、引用、评测。长期记忆、Wiki 入库、插件链编排是笔记没有的。

---

## rag-knowledge-system-main

依据：`README.md`、`app/services/`、`app/ingestion/`、`app/retrieval/`、`app/integrations/`。

自称通用知识库管理平台。React 管理台 + FastAPI。业务名是 documents / ingestion / indexing / retrieval / qa / evaluation。`ParserRegistry` 十几种解析；`chunking.py` 六种策略（fixed / structural / table-aware / parent-child / semantic / chat-record）。向量走 Milvus/Zilliz 或 local；稀疏是进程内 `sparse_index.py` BM25；`hybrid.py` min-max 归一后 alpha 融合（默认 0.7）。Rerank 有 HTTP 客户端和 overlap fallback。`_rewrite_query` 只去空白，不是 LLM 改写。无 Agent、无 GraphRAG。QA 证据不足则固定拒答。有 Hit@1 / MRR 评测页，飞书/企微/钉钉回调进同一套 QA。

沾边笔记：解析（PaddleOCR）、多种切分（《06》只详细写了语义+token）、混合检索、引用、评测。权限是 `PermissionChecker` 插件 + `source_module`，不是 SaaS 多租户。

---

## 附录：FlowRAG-main

依据：`README.md`、`src/retrieval/`、`src/training/`、`run.py`。

Continual Learning RAG 论文框架：预处理好的 QA JSON → SentenceTransformer + Faiss → 训练检索器防遗忘（fp / replug / emdr / fid / l2r）。无文档 ingest、无 UI、无 API。`playground/` 里有一份与主框架无关的 Haystack BM25+rerank 演示。对照产品设计时当研究代码，不当知识库产品。

沾边笔记：纯向量召回（《07》）、评测指标。没有笔记里的分块/解析，因为语料已经是 passage。

---

## 与已知笔记的差异

笔记目录：`01` 流水线与三条索引路线、`02`–`05` 经典 NLP（分词/停用词/word2vec/Gensim）、`06` 语义分块与 token 预算、`07` 向量 RAG 原型、`08` GraphRAG 离线抽图、`Case/如何优化RAG全链路耗时.md`（embedding / 向量召回 / rerank / LLM / 缓存）。

下面只写「仓里是一等设计、笔记里没有或只点到」和「笔记里有、这批仓基本不用」。

### 1. 索引默认不是「三条路线选一条」

`01` 把建索引分成向量 / GraphRAG / 结构化 kv，并说可以组合。这批**产品仓的默认检索层是向量 + 关键词（BM25/倒排）写进同一套或双写**，GraphRAG 和 SQL/`field_map` 是开关，不是主菜单。

| 仓 | 默认检索 | 图 | 结构化 |
|----|----------|----|--------|
| RAGFlow | Doc Engine 向量+词项融合 | `use_kg` / `rag/graphrag/` | table `field_map` → `use_sql` |
| RAGFlow-Plus | 同源混合 | 顶层 `graphrag/`，主 chat 接得弱 | 仍有 `use_sql` |
| QAnything | Milvus；可选 ES `hybrid_search` | 无 | MySQL 元数据 + parent 全文 |
| AnythingLLM | 纯向量；Pin 是全文直注 | 无 | Prisma + JSON 文件 |
| BISHENG | Milvus + ES **默认双写** | 无 | chunk 元数据 |
| WeKnora | 可插拔向量 + BM25，可再加 Neo4j | 有，在线 entity search | FAQ / 父子 / 元数据表 |
| rag-knowledge-system | dense 或 hybrid（内存 BM25） | 无 | PostgreSQL 回表 |

AnythingLLM 是这批里唯一主路径不做 BM25 的产品仓。笔记 `07` 把倒排和向量写成「知识库分类」，没有写成生产默认的融合检索。

### 2. 在线问答比笔记多几段固定工序

`01` §六 的直觉是：检索 → 拼 prompt → 生成。`Case` 补了 embedding / 召回 / rerank / LLM 耗时。产品仓里常见、笔记不当一等模块的：

- **Query 改写**：QAnything `condense_question`、WeKnora `QUERY_UNDERSTAND`、RAGFlow `keyword_extraction` / 跨语言。BISHENG 和 rag-knowledge-system 几乎不做 LLM 改写。
- **Rerank**：QAnything 默认 BCE；RAGFlow / Plus / WeKnora / BISHENG / rag-knowledge-system / AnythingLLM（可选 Native）都有位置。笔记只在耗时案例里当优化项。
- **引用落地**：`insert_citations`、`source_documents`、bbox/page、引用抽屉。笔记在线示例没有「答案必须带出处」这一层。
- **拒答**：AnythingLLM `chatMode=query` 无 context 拒答；rag-knowledge-system 证据不足固定文案。
- **FAQ 短路**：QAnything、WeKnora merge 阶段。高分 FAQ 不走生成。

### 3. 分块是产品策略，不只是「按句组 token」

`06` 的可复制实现是拆句 → 按 token 组块。仓里的名字更碎：

- RAGFlow：`parser_id` 模板 + RAPTOR 摘要树 + parent-child / TOC
- QAnything / WeKnora / rag-knowledge-system：Parent-Child（子块检索、父块回填）
- BISHENG：`SmallerChunks` / `ElemCharacterTextSplitter`
- AnythingLLM：通用 `TextSplitter`

父子分块、RAPTOR、按文档类型选 parser 模板，笔记里都没有当成设计选项。

### 4. 解析是独立子系统，笔记放在 RAG 目录外面

`01` 把「转纯文本」指到 `Multimodal/`、MinerU。产品仓把它做成可替换服务：

- DeepDoc（RAGFlow）
- MinerU / magic_pdf（Plus、BISHENG、WeKnora 可选）
- 独立 OCR/PDF 微服务（QAnything）
- collector（AnythingLLM）
- gRPC DocReader（WeKnora）
- `ParserRegistry`（rag-knowledge-system）

设计含义：ingest 失败域、队列、镜像体积，都在「分块之前」就拆出去了。笔记的 RAG 文从「已有纯文本」讲起，和产品仓的代码量分布不一致。

### 5. GraphRAG：笔记停在离线 CSV，有的仓接到在线检索

`08` 和轻量案例：抽实体/关系/社区报告，导出 CSV，**在线遍历交给平台**。RAGFlow 在线 `use_kg`；WeKnora 离线 `graph.go` + Neo4j，在线并行 entity search。QAnything、AnythingLLM、BISHENG、rag-knowledge-system 没有这条路。不能从笔记推断「做 RAG 就要上图」。

### 6. Agent 在多数仓里是旁路，不是 RAG 的下一层

AnythingLLM：命中 Agent 则离开 `stream.js` 的 RAG 流。RAGFlow：Canvas / Agentic RAG 图编排。WeKnora：ReAct 另一条。BISHENG：灵思 + 工作流节点。QAnything 只有 Bot 配置和联网搜。rag-knowledge-system 没有 Agent。

笔记 RAG 目录不覆盖 Agent；Harness 目录是另一棵树。对照时不要把 Canvas/ReAct 画进「检索模块」。

### 7. 产品层（队列、权限、双前端、评测台）笔记基本没有

各仓真正多出来的文件往往是：Redis/Celery/Asynq 任务、租户/RBAC、管理后台、HTTP API、评测（RAGAS、ranx、Hit@K、HTTP benchmark）。`01` §八 提到「只建索引不做评测」，但没有评测服务长什么样。耗时案例讲了缓存/HNSW/流式，和某仓目录对不上——那是优化手段，不是模块名。

### 8. 笔记前半（`02`–`05`）这批仓几乎不用

jieba 分词、停用词表、word2vec、Gensim LDA/LSI：产品仓的检索输入是 **Embedding 模型看到的 chunk 原文**（外加 BM25 词项），不是先切成词袋再主题变换。`04`/`05` 对理解「文本如何变成可计算」有用，对读这些 GitHub 仓的目录几乎对不上。TF-IDF/BM25 以倒排组件的形式回来了，但不是 Gensim 那套流程。

### 9. 笔记已有、仓里能对上的

- 离线建索引 vs 在线问答（`01` §二）：七个产品仓都拆成「上传/worker」和「chat/QA API」，这一点笔记没有过时。
- 分块过长过短会伤检索（`01` §八、`06`）：各仓都在 chunker / splitter 上花代码。
- 向量近邻（`07`）：除 FlowRAG 的实验设定外，产品仓都有 embedding + 向量存储。
- rerank / 流式 / 缓存（耗时案例）：实现完整度差得远，但问题意识对得上。

---

## 本文不拍的板

对照当时留下的选型（向量库存哪、自建范围、是否接 anyurl2text、第一版模块）已在后续 ADR 与 [架构蓝图](architecture.md) 拍板。本文仍只负责产品仓怎么设计、和笔记差在哪，不改写成自建规范。
