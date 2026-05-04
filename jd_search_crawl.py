"""
京东 PC 搜索列表：监听 search-pc-java 接口，多页翻页 + 分段滚动收包，写入 CSV。
依赖：DrissionPage、本机已安装 Chrome/Edge（与 DrissionPage 配置一致）。
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time

from DrissionPage import ChromiumPage

from jd_chromium import create_chromium_page

LISTEN_MASK = "search-pc-java"

CSV_FIELDS = [
    "商品名称",
    "价格",
    "店铺名称",
    "颜色",
    "评论数",
    "图片",
    "店铺ID",
    "卖点",
    "skuId",
    "总销量",
    "商品ID",
]


def _unwrap_packets(r):
    if r is None or r is False:
        return []
    if isinstance(r, (list, tuple)):
        return [x for x in r if x is not None and x is not False]
    return [r]


def _normalize_selling_point(sp):
    if sp is None:
        return ""
    if isinstance(sp, (list, tuple)):
        return ";".join(str(x) for x in sp)
    return str(sp)


def _process_one_json(json_data, writer: csv.DictWriter, seen_skus: set | None = None) -> int:
    if not isinstance(json_data, dict) or "abBuriedTagMap" not in json_data:
        return 0
    data = json_data.get("data")
    if isinstance(data, dict):
        ware_list = data.get("wareList") or []
    else:
        ware_list = []
    if not isinstance(ware_list, list):
        return 0
    n = 0
    for index in ware_list:
        if not isinstance(index, dict):
            continue
        sku = (str(index.get("skuId") or index.get("wareId") or "")).strip()
        if seen_skus is not None and sku:
            if sku in seen_skus:
                continue
            seen_skus.add(sku)
        title = index.get("wareName") or ""
        new_title = re.sub(r"<.*?>", "", title)
        row = {
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
        writer.writerow(row)
        print(row)
        n += 1
    return n


def _parse_total_pages(dp) -> int | None:
    try:
        el = dp.ele('css:div[class*="_pagination_total"]', timeout=3)
        m = re.search(r"共\s*(\d+)\s*页", el.text)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _collect_page_packets(
    dp,
    scroll_steps: int,
    scroll_delta: int,
    scroll_pause: float,
):
    packets = []
    packets.extend(_unwrap_packets(dp.listen.wait(timeout=25, fit_count=False)))
    for _ in range(scroll_steps):
        dp.scroll.down(scroll_delta)
        time.sleep(scroll_pause)
        packets.extend(_unwrap_packets(dp.listen.wait(timeout=2.5, fit_count=False)))
    time.sleep(1.5)
    miss = 0
    while miss < 4:
        chunk = _unwrap_packets(dp.listen.wait(timeout=4, fit_count=False))
        if not chunk:
            miss += 1
        else:
            packets.extend(chunk)
            miss = 0
    return packets


def _click_next_page(dp) -> None:
    btn = dp.ele('css:div[class*="_pagination_next"]', timeout=8)
    btn.click()


def run(
    dp: ChromiumPage,
    writer: csv.DictWriter,
    *,
    keyword: str,
    max_pages: int,
    max_rows: int | None = None,
    listen_mask: str = LISTEN_MASK,
    scroll_steps: int = 12,
    scroll_delta: int = 550,
    scroll_pause: float = 1.0,
    after_next_page_sleep: float = 2.0,
    flush_every_page: bool = True,
    csv_file=None,
) -> tuple[int, int]:
    """
    执行爬取。返回 (数据包总数, 写入行数)。
    csv_file：传入时可每页 flush。
    max_rows：达到该写入行数后停止翻页（按页截断，可能略大于目标）。
    """
    dp.get("https://search.jd.com/Search?keyword=&enc=utf-8")
    dp.ele("css:.jd_pc_search_bar_react_search_input").input(keyword)
    dp.listen.start(listen_mask)
    dp.ele("css:.jd_pc_search_bar_react_search_btn").click()
    time.sleep(1.5)

    total_pg = _parse_total_pages(dp)
    pages_to_do = min(max_pages, total_pg) if total_pg else max_pages
    print("检测到总页数:", total_pg, "| 本次爬取页数:", pages_to_do)

    seen_skus: set[str] = set()
    packet_total = 0
    row_total = 0

    for pi in range(1, pages_to_do + 1):
        print(f"===== 第 {pi}/{pages_to_do} 页 =====")
        packets = _collect_page_packets(
            dp, scroll_steps, scroll_delta, scroll_pause
        )
        packet_total += len(packets)
        hit_limit = False
        for resp in packets:
            try:
                body = resp.response.body
            except Exception:
                continue
            row_total += _process_one_json(body, writer, seen_skus)
            if max_rows is not None and row_total >= max_rows:
                hit_limit = True
                break
        if flush_every_page and csv_file is not None:
            csv_file.flush()
        if hit_limit:
            print(f"已达目标行数上限 {max_rows}（当前 {row_total} 行），停止本关键词。")
            break

        if pi >= pages_to_do:
            break
        try:
            _click_next_page(dp)
            time.sleep(after_next_page_sleep)
        except Exception as ex:
            print("翻页结束（可能已是最后一页或选择器失效）:", ex)
            break

    return packet_total, row_total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="京东搜索列表多页抓取（DrissionPage + 监听接口）"
    )
    parser.add_argument(
        "-k",
        "--keyword",
        default="cpu自营",
        help="搜索关键词（默认：cpu自营）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="jd_search_result.csv",
        help="输出 CSV 路径（默认：jd_search_result.csv）",
    )
    parser.add_argument(
        "-n",
        "--max-pages",
        type=int,
        default=100,
        help="最多翻页数，会与页面「共 N 页」取较小值（默认：100）",
    )
    parser.add_argument(
        "--listen-mask",
        default=LISTEN_MASK,
        help=f"监听 URL 子串（默认：{LISTEN_MASK}）",
    )
    parser.add_argument(
        "--scroll-steps",
        type=int,
        default=12,
        help="每页分段下滑次数（默认：12）",
    )
    parser.add_argument(
        "--scroll-delta",
        type=int,
        default=550,
        help="每次下滑像素（默认：550）",
    )
    parser.add_argument(
        "--scroll-pause",
        type=float,
        default=1.0,
        help="每次下滑后停顿秒数（默认：1.0）",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="最多写入多少条去重后的商品行，达到即停（默认不限制，仅按页数）",
    )
    parser.add_argument(
        "--chrome-path",
        default="",
        metavar="EXE",
        help="Chrome 或 Edge 可执行文件路径（勿填 Firefox）。也可用环境变量 JD_CHROME_PATH。",
    )
    args = parser.parse_args(argv)

    page = create_chromium_page(args.chrome_path.strip() or None)
    try:
        with open(
            args.output, "w", encoding="utf-8-sig", newline=""
        ) as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            packets, rows = run(
                page,
                w,
                keyword=args.keyword,
                max_pages=args.max_pages,
                max_rows=args.max_rows,
                listen_mask=args.listen_mask,
                scroll_steps=args.scroll_steps,
                scroll_delta=args.scroll_delta,
                scroll_pause=args.scroll_pause,
                csv_file=f,
            )
        print(
            "完成：数据包合计",
            packets,
            "，累计写入",
            rows,
            "行（已按 skuId 去重；无 sku 的仍按条写入）",
        )
        print("已保存:", args.output)
    except KeyboardInterrupt:
        print("用户中断", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
