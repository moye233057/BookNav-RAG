# -*- coding: utf-8 -*-
"""
生成可再分发的演示手册 PDF（自造内容，非第三方版权）。

职责：写出 data/source/demo_handbook.pdf，带「目 录」页与若干正文页，供入库与 README 演示三问。
不入库、不起服务。

怎么跑：在仓库根执行 `python scripts/make_demo_pdf.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_PATH = ROOT / "data" / "source" / "demo_handbook.pdf"

# 目录印刷页码 = PDF 阅读器页码（与 pdf.py 约定一致）
TOC_ENTRIES = (
    ("安全须知", 2),
    ("折叠支架", 3),
    ("展开支架", 4),
    ("充电说明", 5),
    ("规格参数", 6),
)

BODY_PAGES = {
    2: (
        "安全须知",
        [
            "使用本演示设备前，请阅读本章全部内容。",
            "请勿在潮湿环境中给设备充电；发现外壳破损请停止使用。",
            "儿童请在监护人指导下操作折叠支架，避免夹伤手指。",
        ],
    ),
    3: (
        "折叠支架",
        [
            "折叠支架位于设备背面中部，用于收纳与携带。",
            "按下折叠开关后，左右支架臂会同时向内侧收拢；听到咔嗒声表示已锁止。",
            "折叠过程中请勿用力扳动支架臂，以免损坏铰链。",
            "完全折叠后可将设备放入附带收纳袋。",
        ],
    ),
    4: (
        "展开支架",
        [
            "再次按下折叠开关，左右支架臂会同时向外展开并锁定在支撑角度。",
            "展开后轻推支架臂，确认已锁止再放手；未锁止时设备可能倾倒。",
            "若支架无法展开，先检查折叠开关是否被异物卡住，再重试一次。",
        ],
    ),
    5: (
        "充电说明",
        [
            "本设备使用 5V/2A 适配器，接口位于机身右侧。",
            "充电时指示灯为橙色；充满后变为绿色。",
            "请选择干燥、通风的环境充电，远离火源与易燃物。",
            "连续充电超过十二小时仍未转绿，请停止充电并检查适配器。",
        ],
    ),
    6: (
        "规格参数",
        [
            "产品名称：演示折叠支架设备（虚构型号 DEMO-01）。",
            "外形尺寸：长 180 mm、宽 90 mm、高 12 mm（支架折叠状态）。",
            "质量：约 220 g。",
            "工作温度：0℃～40℃。",
            "本手册为开源演示样例，内容可自由复制与修改。",
        ],
    ),
}


def build_pdf(path: Path) -> None:
    """用 pymupdf 画目录页 + 正文页，写入 path。"""
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()

    toc_page = doc.new_page(width=595, height=842)
    # 每条目录用独立 text writer、行距 ≥36pt：过密时 pymupdf4llm 会把多行收成一行空格分隔。
    y = 72.0
    toc_page.insert_text((72, y), "目 录", fontsize=16, fontname="china-s")
    y += 48.0
    for title, page_no in TOC_ENTRIES:
        toc_page.insert_text(
            (72, y),
            f"{title}........{page_no}",
            fontsize=12,
            fontname="china-s",
        )
        y += 36.0

    for page_no in sorted(BODY_PAGES):
        title, paragraphs = BODY_PAGES[page_no]
        page = doc.new_page(width=595, height=842)
        # 正文也用 insert_text：insert_htmlbox 会把 CJK 字体嵌进 PDF，体积可到十几 MB。
        y = 72.0
        page.insert_text((72, y), title, fontsize=14, fontname="china-s")
        y += 36.0
        for paragraph in paragraphs:
            for line in _wrap_line(paragraph, width=28):
                page.insert_text((72, y), line, fontsize=12, fontname="china-s")
                y += 22.0
            y += 10.0

    doc.save(path)
    doc.close()


def _wrap_line(text: str, *, width: int) -> list[str]:
    """按字符数粗分行，避免单行超出页面。"""
    if len(text) <= width:
        return [text]
    return [text[i : i + width] for i in range(0, len(text), width)]


def main() -> int:
    build_pdf(OUT_PATH)
    print(f"已写入 {OUT_PATH.relative_to(ROOT)}（{len(BODY_PAGES) + 1} 页）")
    print("下一步：python scripts/ingest.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
