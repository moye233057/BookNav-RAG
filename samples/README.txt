本目录放可再分发的演示样例（进仓）。

demo_handbook.pdf
  - 自造 6 页短手册：第 1 页「目 录」，第 2～6 页正文（安全须知 / 折叠支架 / 展开支架 / 充电说明 / 规格参数）。
  - 供 README「快速开始」入库与演示三问；不是第三方厂商文档。体积应约数 KB～十几 KB。
  - 若文件缺失、过大或要改文案：在仓库根执行 python scripts/make_demo_pdf.py

用法：复制到 data/source/ 后再 python scripts/ingest.py（data/source/ 不进仓）。
