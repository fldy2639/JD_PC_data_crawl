from DrissionPage import ChromiumOptions

# 必须指向 Chrome 或 Edge 的可执行文件（Chromium 内核）。不要用 Firefox —— 会报错。
# 常见路径示例（按本机实际二选一，改好后在本目录执行: python config_address.py）
path = r'"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'#请改为你电脑内chrome可执行文件路径
# path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

ChromiumOptions().set_browser_path(path).save()
