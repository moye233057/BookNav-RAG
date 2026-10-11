本目录放本机样本文档，**不进仓**（.gitignore 只放行本文件）。

放什么：
- 自造文档，或可再分发的文档（公有领域、CC 授权、你自己写的）。
- 仓库自带演示：把 `samples/demo_handbook.pdf` 复制到本目录（见 README「快速开始」）。
- 第三方版权文档（厂商手册、付费标准、内部资料）只在本机跑，不要提交、也不要压进发布包。

入库：文件放这里后，先起 `python embed_server.py`，再 `python scripts/ingest.py`。
本阶段只支持 PDF。
