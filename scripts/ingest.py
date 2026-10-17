# -*- coding: utf-8 -*-
"""
入库：源文件 → 可分块原文 → 向量库。

职责：人跑的离线入库入口。逐份串行：先调抽取层，再调向量层。
      抽取实现在 offline/extract/，向量实现在 offline/vector/。本文件只编排。
      不问答。
步骤：
  1. step1_extract — 一份源 → data/result/<stem>/chunkable_source.json
  2. step2_vector — 可分块原文 → step4_chunks.json 与 data/lancedb chunks 表
输入：data/source/ 下的文件。PROCESS_ONLY 非空则只跑名单里的那几份。
前置：python -m embed.server 已起（EMBEDDER_KIND=http）。仅 PDF 本仓抽页，不依赖 anyurl2text。
只跑哪几份源，改本文件 PROCESS_ONLY（名字带后缀，与 data/source 下的名字一致；空元组 = 全部）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import conf  # ROOT 在 conf.base；读 yaml 与 .env

from offline.extract.entrance import list_source_files, run_extract
from offline.vector.entrance import list_chunkable_paths, run_vector

# ========== 按需修改 ==========
# 非空则只跑名单里的源文件（名字带后缀，与 data/source 下的一致）；空元组则扫 data/source 全部。
PROCESS_ONLY: tuple[str, ...] = ()
PROCESS_ONLY_STEMS = frozenset(Path(name).stem for name in PROCESS_ONLY)
# ==============================


def step1_extract(source_path: Path) -> Path:
    """
    一份源走完抽取层。

    功能：调 extract.entrance.run_extract。
    应用场景：入库阶段1。
    输入：source_path — data/source 下的文件。
    输出：chunkable_source.json 路径。
    """
    print(f"[阶段1] 抽取 {source_path.name}")
    out_path = run_extract(source_path)
    print(f"[阶段1] 已写入 {out_path}")
    return out_path


def step2_vector(chunkable_path: Path) -> Path:
    """
    一份可分块原文走完向量层。

    功能：调 vector.entrance.run_vector。
    应用场景：入库阶段2。须已起 python -m embed.server。
    输入：chunkable_path — chunkable_source.json。
    输出：LanceDB 目录路径。
    """
    print(f"[阶段2] 向量层 {chunkable_path.parent.name}")
    out_path = run_vector(chunkable_path)
    print(f"[阶段2] 已写入 {out_path}")
    return out_path


def report_empty_tags(chunkable_paths: list[Path]) -> None:
    """
    把 tags 抽空的来源单独列出来。

    功能：读每份可分块原文的 tags，空的收成一行汇总（TODO P1·12：抽空不算入库失败，
          但必须与「有标签」可区分，否则一份没有标签的文档混在「成功 N」里看不出来）。
    应用场景：入库汇总。
    输入：chunkable_paths — 本次真正入库成功的可分块原文路径。
    输出：无（打印）；读不出来的文件跳过，那属于失败列表的事。
    """
    empty = []
    for path in chunkable_paths:
        try:
            tags = json.loads(path.read_text(encoding="utf-8")).get("tags") or []
        except (OSError, json.JSONDecodeError):
            continue
        if not tags:
            empty.append(path.parent.name)
    if empty:
        print(f"标签抽空的来源 {len(empty)} 个（检索时不会按标签加权）：{'、'.join(empty)}")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    parser = argparse.ArgumentParser(description="入库：抽取再向量")
    parser.add_argument(
        "--vector-only",
        action="store_true",
        help="跳过抽取，复用已有的 data/result/<来源>/chunkable_source.json 只重跑向量层"
             "（改过分块或页码判据、embed 服务曾经不可用时用这个）",
    )
    args = parser.parse_args()

    if args.vector_only:
        # 只跑阶段2：分块 + 调 8030 + 写入 LanceDB
        chunkable_paths = list_chunkable_paths()
        if PROCESS_ONLY:
            chunkable_paths = [
                path for path in chunkable_paths if path.parent.name in PROCESS_ONLY_STEMS
            ]
        if not chunkable_paths:
            raise FileNotFoundError(f"没有可重跑的可分块原文 PROCESS_ONLY={PROCESS_ONLY!r}")
        print(f"ingest --vector-only sources={len(chunkable_paths)}")
        succeeded = []
        failed = []
        chunkable_done = []
        for chunkable_path in chunkable_paths:
            try:
                step2_vector(chunkable_path)
                succeeded.append(chunkable_path.parent.name)
                chunkable_done.append(chunkable_path)
            except Exception as exc:
                print(f"失败 {chunkable_path.parent.name}: {exc}")
                failed.append((chunkable_path.parent.name, f"{type(exc).__name__}: {exc}"))
                continue
        print(f"成功 {len(succeeded)} / 失败 {len(failed)}")
        for name, reason in failed:
            print(f"  失败项 {name}: {reason}")
        report_empty_tags(chunkable_done)
        raise SystemExit(1 if failed else 0)

    source_paths = list_source_files()
    if PROCESS_ONLY:
        source_paths = [path for path in source_paths if path.name in PROCESS_ONLY]
    if not source_paths:
        raise FileNotFoundError(f"没有可入库的源文件 PROCESS_ONLY={PROCESS_ONLY!r}")
    print(f"ingest sources={len(source_paths)}")
    succeeded = []
    failed = []
    chunkable_done = []
    for source_path in source_paths:
        try:
            # 阶段1：抽取 → data/result/<stem>/chunkable_source.json
            chunkable_path = step1_extract(source_path)
            # 阶段2：分块 + 调 8030 + 写入 LanceDB
            step2_vector(chunkable_path)
            succeeded.append(source_path.name)
            chunkable_done.append(chunkable_path)
        except Exception as exc:
            print(f"失败 {source_path.name}: {exc}")
            failed.append((source_path.name, f"{type(exc).__name__}: {exc}"))
            continue
    print(f"成功 {len(succeeded)} / 失败 {len(failed)}")
    for name, reason in failed:
        print(f"  失败项 {name}: {reason}")
    report_empty_tags(chunkable_done)
    # 有失败就非零退出：以前这里退 0，「入库失败」在 CI 和脚本调用方看来等于成功（TODO P2·15）
    raise SystemExit(1 if failed else 0)
