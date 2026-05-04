"""
九类 PC 配件 +「自营」：输出文件名与搜索关键词对应关系。
关键词格式：「品类 + 自营」，与京东搜索栏一致。
"""

from __future__ import annotations

# (输出 CSV 文件名, 搜索关键词)
CATEGORY_JOBS: list[tuple[str, str]] = [
    ("jd_自营_CPU.csv", "CPU自营"),
    ("jd_自营_主板.csv", "主板自营"),
    ("jd_自营_显卡.csv", "显卡自营"),
    ("jd_自营_内存.csv", "内存自营"),
    ("jd_自营_硬盘.csv", "硬盘自营"),
    ("jd_自营_电源.csv", "电源自营"),
    ("jd_自营_散热.csv", "散热自营"),
    ("jd_自营_机箱.csv", "机箱自营"),
    ("jd_自营_显示器.csv", "显示器自营"),
]
