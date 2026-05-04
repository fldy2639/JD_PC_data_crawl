"""
DrissionPage 的 ChromiumPage 仅支持 Chrome / Edge / Chromium 等内核，不支持 Firefox。

统一在此创建浏览器实例：可传路径或环境变量 JD_CHROME_PATH；否则使用已保存的全局配置
（由 config_address.py 或 ChromiumOptions().set_browser_path(...).save() 写入）。
"""

from __future__ import annotations

import os

from DrissionPage import ChromiumOptions, ChromiumPage


def create_chromium_page(browser_path: str | None = None) -> ChromiumPage:
    path = (browser_path or "").strip() or os.environ.get("JD_CHROME_PATH", "").strip()
    if path:
        lower = path.lower()
        if "firefox" in lower or "waterfox" in lower or "librewolf" in lower:
            raise ValueError(
                "当前路径是 Firefox 系浏览器，但 DrissionPage 的 ChromiumPage 只支持 "
                "Chrome / Edge 等 Chromium 内核。请把 config_address.py 改为 chrome.exe "
                "或 msedge.exe，或使用 --chrome-path / 环境变量 JD_CHROME_PATH 指向 Chrome。"
            )
        co = ChromiumOptions()
        co.set_browser_path(path)
        return ChromiumPage(co)
    return ChromiumPage()
