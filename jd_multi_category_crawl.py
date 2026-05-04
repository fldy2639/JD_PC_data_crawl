"""
按 jd_category_jobs 中的九类关键词依次爬取，每类一个 CSV，默认每类约 500 条（去重后行数）。

用法（在项目目录下）：
  python jd_multi_category_crawl.py --out-dir ./jd_data --target-rows 500

共用同一个浏览器实例，品类之间会间隔 pause 秒，降低风控概率。
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from jd_chromium import create_chromium_page
from jd_category_jobs import CATEGORY_JOBS
from jd_search_crawl import CSV_FIELDS, LISTEN_MASK, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="京东九类「品类+自营」批量抓取")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("jd_category_csv"),
        help="CSV 输出目录（默认：jd_category_csv，不存在会自动创建）",
    )
    parser.add_argument(
        "--target-rows",
        type=int,
        default=500,
        help="每类目标行数（去重后），达到即停（默认：500）",
    )
    parser.add_argument(
        "-n",
        "--max-pages",
        type=int,
        default=80,
        help="单类最多翻页数，与目标行数同时生效，先到先停（默认：80）",
    )
    parser.add_argument(
        "--pause-between",
        type=float,
        default=8.0,
        help="两类之间暂停秒数（默认：8）",
    )
    parser.add_argument(
        "--listen-mask",
        default=LISTEN_MASK,
        help=f"监听 URL 子串（默认：{LISTEN_MASK}）",
    )
    parser.add_argument(
        "--only",
        default="",
        help="只跑文件名或关键词包含该子串的任务，例如：显卡",
    )
    parser.add_argument(
        "--from",
        dest="start_from",
        default="",
        metavar="SUBSTR",
        help="从第一个文件名或关键词包含该子串的任务开始往后跑（用于断点续跑），例如：硬盘",
    )
    parser.add_argument(
        "--chrome-path",
        default="",
        metavar="EXE",
        help="Chrome 或 Edge 可执行文件路径（勿填 Firefox）。也可用环境变量 JD_CHROME_PATH。",
    )
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    page = create_chromium_page(args.chrome_path.strip() or None)
    only = args.only.strip()
    start_from = args.start_from.strip()

    chain = list(CATEGORY_JOBS)
    if start_from:
        start_idx = None
        for j, (fn, kw) in enumerate(chain):
            if start_from in fn or start_from in kw:
                start_idx = j
                break
        if start_idx is None:
            print(
                f"「--from {start_from}」未匹配到任何任务，请对照 jd_category_jobs.py 检查。",
                file=sys.stderr,
            )
            return 2
        chain = chain[start_idx:]
        print(f"从第 {start_idx + 1} 项起跑（匹配: {start_from}），共 {len(chain)} 个任务")

    jobs = [
        (fn, kw)
        for fn, kw in chain
        if not only or only in fn or only in kw
    ]
    if not jobs:
        print("没有匹配的任务，请检查 --only", file=sys.stderr)
        return 2

    summary: list[tuple[str, int, int]] = []
    try:
        for i, (filename, keyword) in enumerate(jobs):
            path = args.out_dir / filename
            print("\n" + "=" * 60)
            print(f"[{i + 1}/{len(jobs)}] 关键词: {keyword} -> {path}")
            print("=" * 60)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                w.writeheader()
                packets, rows = run(
                    page,
                    w,
                    keyword=keyword,
                    max_pages=args.max_pages,
                    max_rows=args.target_rows,
                    listen_mask=args.listen_mask,
                    csv_file=f,
                )
            summary.append((filename, packets, rows))
            print(f"已保存 {path} ，本类数据包 {packets} ，写入 {rows} 行")
            if i < len(jobs) - 1:
                print(f"pause {args.pause_between}s ...")
                time.sleep(args.pause_between)
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130

    print("\n全部任务结束汇总：")
    for fn, pkt, r in summary:
        print(f"  {fn}: {r} 行, {pkt} 包")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
