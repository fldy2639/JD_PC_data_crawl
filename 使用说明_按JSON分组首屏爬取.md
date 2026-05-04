# 按 JSON 分组、首屏 30 条 — 使用说明

本文说明 **「关键词来自 `自营爬虫搜索字段_queries.json` + `jd_queries_group_crawl.py`」** 这一套流程。  
**原有的《使用说明.md》（翻页/滚动/九类大批量）未被替换**，两套可并存，按需选用。

---

## 与旧方案的区别

| 项目 | 旧方案（见 `使用说明.md`） | 本方案 |
|------|---------------------------|--------|
| 入口脚本 | `jd_search_crawl.py` / `jd_multi_category_crawl.py` | `jd_queries_group_crawl.py` |
| 关键词来源 | 手写或 `jd_category_jobs.py` 九类粗词 | `自营爬虫搜索字段_queries.json` 分组细词 |
| 翻页 / 滚动 | 有 | **无**：搜索后只收接口包 |
| 每关键词条数 | 可到数百（多页累加） | **默认最多 30 条**（首屏合并去重） |
| CSV 列 | 原 11 列 | 原列不变，**在「商品名称」前增加「搜索字段」** |
| 输出文件数 | 九类时为 9 个等 | **每个 JSON `group` 一个 CSV**（当前为 10 个） |

监听接口、字段解析逻辑与 `jd_search_crawl.py` 一致（`search-pc-java`、`wareList` 等）。

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `自营爬虫搜索字段_queries.json` | 定义 `groups`：每组 `id`、`label`、`keywords[]`；每条 `keyword` 即京东搜索框可用串（建议含「自营」）。 |
| `jd_queries_group_crawl.py` | 按组顺序：组内每条关键词搜索一次，每组写一个 CSV。 |
| `jd_chromium.py` | 统一创建 `ChromiumPage`：**仅支持 Chrome/Edge**，若路径指向 Firefox 会直接报错提示。 |
| `jd_search_crawl.py` | 被本脚本引用 `LISTEN_MASK`、`_unwrap_packets`、`_normalize_selling_point` 及列名常量。 |

---

## 环境要求

与原版相同：**Python 3.10+**、**DrissionPage**、本机 **Chrome 或 Edge** 可用（**不要用 Firefox**：DrissionPage 的 `ChromiumPage` 不支持）。全局浏览器路径可编辑 `config_address.py` 后执行一次 `python config_address.py` 保存；也可在命令行传 **`--chrome-path`** 或设置环境变量 **`JD_CHROME_PATH`** 指向 `chrome.exe` / `msedge.exe`。

```bash
pip install DrissionPage
```

---

## 快速开始

在**项目目录**下执行（路径按本机修改）：

```bash
cd d:\code\claude_code\self_support_crawl
python jd_queries_group_crawl.py --out-dir ./jd_query_csv
```

- 默认读取同目录下的 **`自营爬虫搜索字段_queries.json`**。  
- 默认输出目录 **`jd_query_csv`**（避免覆盖旧的 `jd_category_csv`）。  
- 每组生成一个 CSV，文件名与历史习惯对齐，例如：`jd_自营_CPU.csv`、`jd_自营_主板.csv`、…、`jd_自营_机箱风扇.csv`。

---

## 输出 CSV 列顺序

1. **搜索字段**（本次使用的完整搜索关键词）  
2. **商品名称**、**价格**、**店铺名称**、**颜色**、**评论数**、**图片**、**店铺ID**、**卖点**、**skuId**、**总销量**、**商品ID**  

与 `jd_search_crawl.py` 中 `CSV_FIELDS` 一致，仅多第一列。

---

## 命令行参数一览（`jd_queries_group_crawl.py`）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--queries-json` | 关键词分组 JSON 路径 | 脚本同目录 `自营爬虫搜索字段_queries.json` |
| `--out-dir` | CSV 输出目录 | `jd_query_csv` |
| `--max-rows-per-keyword` | 每个关键词最多写入条数 | `30` |
| `--extra-packet-waits` | 首包之后额外 `listen.wait` 次数（无滚动时多收几包） | `6` |
| `--packet-wait-timeout` | 每次额外 `wait` 超时（秒） | `4.0` |
| `--after-click-sleep` | 点击搜索后等待再收包（秒） | `2.5` |
| `--pause-between-keywords` | 同组内两条关键词间隔（秒） | `12.0` |
| `--pause-between-groups` | 两个分组 CSV 之间间隔（秒） | `20.0` |
| `--listen-mask` | 监听 URL 子串 | `search-pc-java` |
| `--only-group-id` | 只跑某一组，例如 `cpu` | 空（全跑） |
| `--skip-until-keyword-substr` | 每组内跳过关键词直到某条「完整关键词」包含该子串（与 `--start-from-keyword-substr` 二选一） | 空 |
| `--start-from-keyword-substr` | 在（`--only-group-id` 过滤后的）全部分组顺序中，定位**第一条**含该子串的关键词，从该条起跑完本组，再依次跑 JSON **后续所有分组**直至末尾；首组若跳过若干条且该组 CSV 已存在非空则**追加** | 空 |
| `--chrome-path` | Chrome/Edge 的 `.exe` 全路径（覆盖全局配置） | 空（读全局或 `JD_CHROME_PATH`） |

---

## 常用示例

```bash
# 指定 JSON 与输出目录
python jd_queries_group_crawl.py --queries-json ./自营爬虫搜索字段_queries.json --out-dir D:\data\jd_query_csv

# 只跑 CPU 分组（调试）
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id cpu

# 每关键词只保留 20 条
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --max-rows-per-keyword 20

# 从「电脑电源 850W 自营」起一条命令跑到 JSON 末尾（电源余下 + 散热 + 机箱 + 显示器 + 机箱风扇）
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --start-from-keyword-substr 850W

# 仅电源组内从 850W 起（不跑后面分组）：仍用 --only-group-id + --skip-until（勿与上一行同时加）
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id psu --skip-until-keyword-substr 850W
```

---

## 修改关键词

编辑 **`自营爬虫搜索字段_queries.json`**：

- 在对应 `group` 的 **`keywords`** 数组中增删改字符串即可。  
- 新增分组时：填写 **`id`**、**`label`**、**`keywords`**；若 `id` 未在脚本内 `GROUP_ID_TO_FILENAME` 映射表中，将自动生成 **`jd_自营_{id}.csv`**。若需固定中文文件名，可在 `jd_queries_group_crawl.py` 的 `GROUP_ID_TO_FILENAME` 中补一行映射。

---

## 注意事项

1. **首屏条数**：接口若单次不足 30 条，则实际行数会少于 30；脚本不会翻页补全。  
2. **风控**：关键词多、连续请求易触发验证。脚本默认已偏保守（关键词间隔 12s、分组间隔 20s）；若仍弹验证，可再加大上述两项或拆 `--only-group-id` 分多次跑。  
3. **`listen.wait`**：须使用关键字参数 `timeout=...`（与原版说明一致，第一个位置参数是包个数而非秒数）。  

更完整的单脚本/九类大批量说明仍以 **`使用说明.md`** 为准。
