"""
按「自营爬虫搜索字段_queries.json」分组爬取：每组一个 CSV，组内每条关键词搜索一次，
不滚动、不翻页，仅从接口响应合并得到至多 30 条商品；列与原 jd_search_crawl 一致，
并在「商品名称」前增加「搜索字段」列。

用法（在项目目录下）：
  python jd_queries_group_crawl.py --out-dir ./jd_query_csv
  python jd_queries_group_crawl.py --out-dir ./jd_query_csv --start-from-keyword-substr 850W

依赖：DrissionPage、本机 Chrome/Edge；-queries-json 默认为同目录下
「自营爬虫搜索字段_queries.json」。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from DrissionPage import ChromiumPage

from jd_chromium import create_chromium_page
from jd_search_crawl import (
    CSV_FIELDS,
    LISTEN_MASK,
    _normalize_selling_point,
    _unwrap_packets,
)

SEARCH_FIELD_COL = "搜索字段"
OUTPUT_FIELDNAMES = [SEARCH_FIELD_COL] + list(CSV_FIELDS)

# 与历史 jd_category_jobs 命名习惯对齐，便于对照旧 CSV
GROUP_ID_TO_FILENAME: dict[str, str] = {
    "cpu": "jd_自营_CPU.csv",
    "motherboard": "jd_自营_主板.csv",
    "gpu": "jd_自营_显卡.csv",
    "ram": "jd_自营_内存.csv",
    "ssd": "jd_自营_硬盘.csv",
    "psu": "jd_自营_电源.csv",
    "cooler": "jd_自营_散热.csv",
    "case": "jd_自营_机箱.csv",
    "monitor": "jd_自营_显示器.csv",
    "case_fan": "jd_自营_机箱风扇.csv",
}


def _load_groups(queries_path: Path) -> list[dict]:
    data = json.loads(queries_path.read_text(encoding="utf-8"))
    groups = data.get("groups")
    if not isinstance(groups, list):
        raise ValueError("queries json 缺少有效的 groups 数组")
    return groups


def _extract_ware_list(json_data) -> list:
    if not isinstance(json_data, dict) or "abBuriedTagMap" not in json_data:
        return []
    data = json_data.get("data")
    if isinstance(data, dict):
        ware_list = data.get("wareList") or []
    else:
        ware_list = []
    return ware_list if isinstance(ware_list, list) else []


def _index_to_row(search_keyword: str, index: dict) -> dict:
    title = index.get("wareName") or ""
    new_title = re.sub(r"<.*?>", "", title)
    return {
        SEARCH_FIELD_COL: search_keyword,
        "商品名称": new_title,
        "价格": index.get("jdPrice", ""),
        "店铺名称": index.get("shopName", ""),
        "颜色": index.get("color", ""),
        "评论数": index.get("commentFuzzy", ""),
        "图片": index.get("imageurl", ""),
        "店铺ID": index.get("shopId", ""),
        "卖点": _normalize_selling_point(index.get("sellingPoint")),
        "skuId": index.get("skuId", ""),
        "总销量": index.get("totalSales", ""),
        "商品ID": index.get("wareId", ""),
    }


def _merge_packets_to_items(packets: list, max_items: int) -> list[dict]:
    """按响应顺序合并 wareList 条目，按 skuId/wareId 去重，最多 max_items 条。"""
    merged: list[dict] = []
    seen: set[str] = set()
    for resp in packets:
        try:
            body = resp.response.body
        except Exception:
            continue
        for index in _extract_ware_list(body):
            if not isinstance(index, dict):
                continue
            sku = (str(index.get("skuId") or index.get("wareId") or "")).strip()
            if sku:
                if sku in seen:
                    continue
                seen.add(sku)
            merged.append(index)
            if len(merged) >= max_items:
                return merged
    return merged


def _collect_packets_no_scroll(
    dp, *, extra_waits: int, wait_timeout: float
) -> list:
    packets: list = []
    packets.extend(_unwrap_packets(dp.listen.wait(timeout=25, fit_count=False)))
    for _ in range(max(0, extra_waits)):
        time.sleep(0.45)
        packets.extend(_unwrap_packets(dp.listen.wait(timeout=wait_timeout, fit_count=False)))
    return packets


def run_one_keyword(
    dp: ChromiumPage,
    *,
    keyword: str,
    listen_mask: str,
    max_rows: int,
    extra_packet_waits: int,
    packet_wait_timeout: float,
    after_click_sleep: float,
) -> tuple[int, int, list[dict]]:
    """执行一次搜索（不滚动、不翻页），返回 (响应包数, 商品条数, 行字典列表)。"""
    dp.get("https://search.jd.com/Search?keyword=&enc=utf-8")
    bar = dp.ele("css:.jd_pc_search_bar_react_search_input")
    try:
        bar.input(keyword, clear=True)
    except TypeError:
        bar.input(keyword)
    dp.listen.start(listen_mask)
    dp.ele("css:.jd_pc_search_bar_react_search_btn").click()
    time.sleep(after_click_sleep)
    packets = _collect_packets_no_scroll(
        dp,
        extra_waits=extra_packet_waits,
        wait_timeout=packet_wait_timeout,
    )
    items = _merge_packets_to_items(packets, max_rows)
    rows = [_index_to_row(keyword, it) for it in items]
    try:
        dp.listen.stop()
    except Exception:
        pass
    return len(packets), len(rows), rows


def _default_queries_path() -> Path:
    return Path(__file__).resolve().parent / "自营爬虫搜索字段_queries.json"


def _group_csv_name(group: dict) -> str:
    gid = (group.get("id") or "").strip()
    if not gid:
        raise ValueError("group 缺少 id")
    return GROUP_ID_TO_FILENAME.get(gid) or f"jd_自营_{gid}.csv"


def _find_first_keyword_match(
    groups: list[dict], substr: str
) -> tuple[int, int] | None:
    """返回 (group_index, keyword_index)，keyword_index 对应原始 keywords 列表下标。"""
    for gi, group in enumerate(groups):
        kws = group.get("keywords")
        if not isinstance(kws, list):
            continue
        for ki, w in enumerate(kws):
            if isinstance(w, str) and substr in w.strip():
                return (gi, ki)
    return None


def _build_chain_from_start(
    groups: list[dict], substr: str
) -> list[tuple[dict, list, bool]] | None:
    """
    从全文件中第一条含 substr 的关键词起，直到最后一个分组。
    返回 [(group, keywords 切片后的列表副本, skipped_prefix), ...]；
    skipped_prefix 为 True 表示该组丢掉了至少一条前置关键词（用于续跑追加 CSV）。
    未找到匹配时返回 None。
    """
    hit = _find_first_keyword_match(groups, substr)
    if hit is None:
        return None
    gi, ki = hit
    plan: list[tuple[dict, list, bool]] = []
    for i, group in enumerate(groups):
        if i < gi:
            continue
        raw = group.get("keywords")
        if not isinstance(raw, list) or not raw:
            continue
        raw = list(raw)
        if i == gi:
            sliced = raw[ki:]
            skipped_prefix = ki > 0
        else:
            sliced = raw
            skipped_prefix = False
        plan.append((group, sliced, skipped_prefix))
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="按 queries json 分组爬京东搜索首屏（每关键词至多 30 条，无滚动翻页）"
    )
    parser.add_argument(
        "--queries-json",
        type=Path,
        default=None,
        help="关键词分组 JSON（默认：脚本同目录 自营爬虫搜索字段_queries.json）",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("jd_query_csv"),
        help="CSV 输出目录（默认：jd_query_csv）",
    )
    parser.add_argument(
        "--max-rows-per-keyword",
        type=int,
        default=30,
        help="每个搜索关键词最多写入多少条（默认：30）",
    )
    parser.add_argument(
        "--extra-packet-waits",
        type=int,
        default=6,
        help="首包之后额外 listen.wait 次数，用于收齐分段接口（默认：6，无滚动）",
    )
    parser.add_argument(
        "--packet-wait-timeout",
        type=float,
        default=4.0,
        help="每次额外 wait 的超时秒数（默认：4）",
    )
    parser.add_argument(
        "--after-click-sleep",
        type=float,
        default=2.5,
        help="点击搜索后等待秒数再开始收包（默认：2.5，略放慢降低风控）",
    )
    parser.add_argument(
        "--pause-between-keywords",
        type=float,
        default=12.0,
        help="同一 CSV 内两条关键词之间的间隔秒数（默认：12）",
    )
    parser.add_argument(
        "--pause-between-groups",
        type=float,
        default=20.0,
        help="两个分组文件之间的间隔秒数（默认：20）",
    )
    parser.add_argument(
        "--listen-mask",
        default=LISTEN_MASK,
        help=f"监听 URL 子串（默认：{LISTEN_MASK}）",
    )
    parser.add_argument(
        "--only-group-id",
        default="",
        help="只处理 id 等于该值的分组（例如 cpu）",
    )
    parser.add_argument(
        "--skip-until-keyword-substr",
        default="",
        metavar="SUBSTR",
        help="每组内按顺序跳过关键词，直到某条完整关键词包含该子串（含该条）；"
        "未匹配则本组仍跑全部。常与 --only-group-id 合用续跑。不可与 --start-from-keyword-substr 同用。",
    )
    parser.add_argument(
        "--start-from-keyword-substr",
        default="",
        metavar="SUBSTR",
        help="在（--only-group-id 过滤后的）全部分组顺序中，定位第一条包含该子串的关键词，"
        "从该条起跑完本组，再依次跑 JSON 后续所有分组直到末尾；首组若跳过若干条且该组 CSV 已存在非空则追加。",
    )
    parser.add_argument(
        "--supplement-keywords",
        nargs="+",
        metavar="KW",
        default=None,
        help="仅爬取所列完整搜索词（可多个），结果追加到 --only-group-id 对应 CSV；"
        "须同时指定 --only-group-id；不可与 --start-from-keyword-substr / --skip-until-keyword-substr 同用。",
    )
    parser.add_argument(
        "--chrome-path",
        default="",
        metavar="EXE",
        help="Chrome 或 Edge 可执行文件路径（覆盖全局配置；勿填 Firefox）。也可用环境变量 JD_CHROME_PATH。",
    )
    args = parser.parse_args(argv)

    queries_path = args.queries_json or _default_queries_path()
    if not queries_path.is_file():
        print(f"找不到 queries 文件: {queries_path}", file=sys.stderr)
        return 2

    try:
        groups = _load_groups(queries_path)
    except Exception as ex:
        print(f"读取 JSON 失败: {ex}", file=sys.stderr)
        return 2

    only_gid = args.only_group_id.strip()
    if only_gid:
        groups = [g for g in groups if str(g.get("id", "")).strip() == only_gid]
        if not groups:
            print(f"--only-group-id {only_gid!r} 未匹配到任何分组", file=sys.stderr)
            return 2

    start_sub = (args.start_from_keyword_substr or "").strip()
    skip_sub = (args.skip_until_keyword_substr or "").strip()
    sup_kws_raw = getattr(args, "supplement_keywords", None)

    if sup_kws_raw is not None:
        if not only_gid:
            print(
                "--supplement-keywords 必须与 --only-group-id 同时使用。",
                file=sys.stderr,
            )
            return 2
        if start_sub or skip_sub:
            print(
                "补充模式不可与 --start-from-keyword-substr 或 --skip-until-keyword-substr 同用。",
                file=sys.stderr,
            )
            return 2

    if start_sub and skip_sub:
        print(
            "不能同时使用 --start-from-keyword-substr 与 --skip-until-keyword-substr，"
            "续跑整条链请只用前者。",
            file=sys.stderr,
        )
        return 2

    chain_plan: list[tuple[dict, list, bool]] | None = None
    if start_sub:
        chain_plan = _build_chain_from_start(groups, start_sub)
        if not chain_plan:
            print(
                f"--start-from-keyword-substr {start_sub!r} 在关键词中未找到匹配",
                file=sys.stderr,
            )
            return 2
        g0 = chain_plan[0][0]
        first_lab = str(g0.get("label") or g0.get("id") or "")
        print(
            f"[续跑] 从子串 {start_sub!r} 起执行 {len(chain_plan)} 个分组直至末尾"
            f"（首组 {first_lab!r}）"
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    chrome_path = args.chrome_path.strip() or None
    page = create_chromium_page(chrome_path)
    summary: list[tuple[str, int, int]] = []

    try:
        if sup_kws_raw is not None:
            kws = [
                k.strip()
                for k in sup_kws_raw
                if isinstance(k, str) and k.strip()
            ]
            if not kws:
                print("--supplement-keywords 至少需要一条非空关键词。", file=sys.stderr)
                return 2
            group = groups[0]
            gid = str(group.get("id", "")).strip()
            label = str(group.get("label", gid))
            filename = _group_csv_name(group)
            path = args.out_dir / filename
            append_existing = path.is_file() and path.stat().st_size > 0
            if append_existing:
                print("[补充] 在已有 CSV 末尾追加（不写表头）")
            else:
                print("[补充] 将新建 CSV 并写入表头")

            print("\n" + "=" * 60)
            print(f"[补充] {label} ({gid}) -> {path} ，共 {len(kws)} 条关键词")
            print("=" * 60)

            group_packets = 0
            group_rows = 0
            file_mode = "a" if append_existing else "w"
            with open(path, file_mode, encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
                if not append_existing:
                    writer.writeheader()
                for seq, kw in enumerate(kws):
                    print(f"  [{seq + 1}/{len(kws)}] 搜索: {kw}")
                    pkt, n, rows = run_one_keyword(
                        page,
                        keyword=kw,
                        listen_mask=args.listen_mask,
                        max_rows=args.max_rows_per_keyword,
                        extra_packet_waits=args.extra_packet_waits,
                        packet_wait_timeout=args.packet_wait_timeout,
                        after_click_sleep=args.after_click_sleep,
                    )
                    group_packets += pkt
                    group_rows += n
                    for row in rows:
                        writer.writerow(row)
                    f.flush()
                    print(f"       收包 {pkt}，写入 {n} 条")
                    if seq < len(kws) - 1:
                        time.sleep(args.pause_between_keywords)

            summary.append((filename, group_packets, group_rows))
            print(f"已保存 {path} ，累计收包 {group_packets} ，写入 {group_rows} 行")

            print("\n全部结束汇总：")
            for fn, pkt, r in summary:
                print(f"  {fn}: {r} 行, {pkt} 包")
            return 0

        if chain_plan is not None:
            _run_chain = chain_plan
            for j, (group, keywords, skipped_prefix_rows) in enumerate(_run_chain):
                gid = str(group.get("id", "")).strip()
                label = str(group.get("label", gid))
                keywords = list(keywords)
                if not keywords:
                    print(f"[跳过] 分组 {gid!r} 无有效关键词", file=sys.stderr)
                    continue

                filename = _group_csv_name(group)
                path = args.out_dir / filename
                append_existing = (
                    skipped_prefix_rows
                    and path.is_file()
                    and path.stat().st_size > 0
                )
                if append_existing:
                    print("[续跑] 已有该组 CSV 且非空，末尾追加新行（不写表头）")

                print("\n" + "=" * 60)
                print(
                    f"[分组 {j + 1}/{len(_run_chain)}] {label} ({gid}) -> {path}"
                )
                print("=" * 60)

                group_packets = 0
                group_rows = 0
                file_mode = "a" if append_existing else "w"
                with open(path, file_mode, encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
                    if not append_existing:
                        writer.writeheader()
                    valid_indices = [
                        i
                        for i, w in enumerate(keywords)
                        if isinstance(w, str) and w.strip()
                    ]
                    for seq, i in enumerate(valid_indices):
                        kw = keywords[i].strip()
                        print(f"  [{seq + 1}/{len(valid_indices)}] 搜索: {kw}")
                        pkt, n, rows = run_one_keyword(
                            page,
                            keyword=kw,
                            listen_mask=args.listen_mask,
                            max_rows=args.max_rows_per_keyword,
                            extra_packet_waits=args.extra_packet_waits,
                            packet_wait_timeout=args.packet_wait_timeout,
                            after_click_sleep=args.after_click_sleep,
                        )
                        group_packets += pkt
                        group_rows += n
                        for row in rows:
                            writer.writerow(row)
                        f.flush()
                        print(f"       收包 {pkt}，写入 {n} 条")
                        if seq < len(valid_indices) - 1:
                            time.sleep(args.pause_between_keywords)

                summary.append((filename, group_packets, group_rows))
                print(f"已保存 {path} ，累计收包 {group_packets} ，写入 {group_rows} 行")

                if j < len(_run_chain) - 1:
                    print(
                        f"pause between groups {args.pause_between_groups}s ..."
                    )
                    time.sleep(args.pause_between_groups)
        else:
            for gi, group in enumerate(groups):
                gid = str(group.get("id", "")).strip()
                label = str(group.get("label", gid))
                keywords = group.get("keywords")
                if not isinstance(keywords, list) or not keywords:
                    print(f"[跳过] 分组 {gid!r} 无 keywords", file=sys.stderr)
                    continue

                keywords = list(keywords)
                skipped_prefix_rows = False
                if skip_sub:
                    idx = next(
                        (
                            i
                            for i, w in enumerate(keywords)
                            if isinstance(w, str) and skip_sub in w.strip()
                        ),
                        None,
                    )
                    if idx is not None:
                        if idx > 0:
                            skipped_prefix_rows = True
                        print(
                            f"[续跑] 子串 {skip_sub!r} 起：本组从第 {idx + 1} 条关键词开始（余 {len(keywords) - idx} 条）"
                        )
                        keywords = keywords[idx:]
                    else:
                        print(
                            f"[续跑] 本组无关键词含 {skip_sub!r}，将跑本组全部关键词",
                            file=sys.stderr,
                        )

                filename = _group_csv_name(group)
                path = args.out_dir / filename
                append_existing = (
                    skip_sub
                    and skipped_prefix_rows
                    and path.is_file()
                    and path.stat().st_size > 0
                )
                if append_existing:
                    print("[续跑] 已有该组 CSV 且非空，末尾追加新行（不写表头）")

                print("\n" + "=" * 60)
                print(f"[分组 {gi + 1}/{len(groups)}] {label} ({gid}) -> {path}")
                print("=" * 60)

                group_packets = 0
                group_rows = 0

                file_mode = "a" if append_existing else "w"
                with open(path, file_mode, encoding="utf-8-sig", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDNAMES)
                    if not append_existing:
                        writer.writeheader()
                    valid_indices = [
                        i
                        for i, w in enumerate(keywords)
                        if isinstance(w, str) and w.strip()
                    ]
                    for seq, i in enumerate(valid_indices):
                        kw = keywords[i].strip()
                        print(f"  [{seq + 1}/{len(valid_indices)}] 搜索: {kw}")
                        pkt, n, rows = run_one_keyword(
                            page,
                            keyword=kw,
                            listen_mask=args.listen_mask,
                            max_rows=args.max_rows_per_keyword,
                            extra_packet_waits=args.extra_packet_waits,
                            packet_wait_timeout=args.packet_wait_timeout,
                            after_click_sleep=args.after_click_sleep,
                        )
                        group_packets += pkt
                        group_rows += n
                        for row in rows:
                            writer.writerow(row)
                        f.flush()
                        print(f"       收包 {pkt}，写入 {n} 条")
                        if seq < len(valid_indices) - 1:
                            time.sleep(args.pause_between_keywords)

                summary.append((filename, group_packets, group_rows))
                print(f"已保存 {path} ，累计收包 {group_packets} ，写入 {group_rows} 行")

                if gi < len(groups) - 1:
                    print(
                        f"pause between groups {args.pause_between_groups}s ..."
                    )
                    time.sleep(args.pause_between_groups)

    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        return 130
    except Exception as ex:
        print(f"运行异常: {ex}", file=sys.stderr)
        return 1

    print("\n全部结束汇总：")
    for fn, pkt, r in summary:
        print(f"  {fn}: {r} 行, {pkt} 包")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())