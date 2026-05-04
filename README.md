# 补爬与后续分组抓取说明

本文档约定：在 **`self_support_crawl` 项目根目录** 下执行命令；CSV 默认输出到 **`jd_query_csv`**。  
依赖与浏览器配置见 **`使用说明_按JSON分组首屏爬取.md`**、**`config_address.py`**。

关键词列表以仓库内 **`自营爬虫搜索字段_queries.json`** 为准；若 JSON 有改动，请同步更新本文档中的命令。

---

## 命令格式说明

| 场景 | 参数要点 |
|------|-----------|
| **补爬**（已有 CSV，只补若干条搜索词） | `--only-group-id <分组id>` + `--supplement-keywords` + 多个完整搜索词（与 JSON 中字符串一致） |
| **整组新开爬**（尚无该组 CSV，或要整文件重跑） | `--only-group-id <分组id>`（不加 supplement） |

**分组 id 与文件名对照**

| `id` | 输出 CSV |
|------|-----------|
| `cpu` | `jd_自营_CPU.csv` |
| `motherboard` | `jd_自营_主板.csv` |
| `gpu` | `jd_自营_显卡.csv` |
| `ram` | `jd_自营_内存.csv` |
| `ssd` | `jd_自营_硬盘.csv` |
| `psu` | `jd_自营_电源.csv` |
| `cooler` | `jd_自营_散热.csv` |
| `case` | `jd_自营_机箱.csv` |
| `monitor` | `jd_自营_显示器.csv` |
| `case_fan` | `jd_自营_机箱风扇.csv` |

**说明**

- 补爬时：若目标 CSV **已存在且非空**，新结果会 **追加在文件末尾**（不写表头）；若文件不存在则新建并写表头。
- 若出现「收包有、写入 0 条」，多为风控或接口无 `wareList`；可先手动过验证，并加大等待，例如追加：`--after-click-sleep 4 --extra-packet-waits 10`。

---

## 一、补爬指令（当前 JSON 下缺数据的搜索词）

以下命令均假设当前目录为项目根，且 `--out-dir ./jd_query_csv`；若你实际输出目录不同，请改掉该参数。

### 1. CPU（缺 2 条）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id cpu --supplement-keywords "英特尔酷睿i7 CPU 自营" "英特尔酷睿i5 CPU 自营"
```

### 2. 显卡（缺 2 条）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id gpu --supplement-keywords "RTX 5080 自营" "RTX 5070 Ti 自营"
```

### 3. 内存（缺 1 条）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id ram --supplement-keywords "DDR4 16G 内存 自营"
```

### 4. 电源（缺 4 条）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id psu --supplement-keywords "电脑电源 550W 自营" "电脑电源 650W 自营" "电脑电源 850W 自营" "电脑电源 1200W 自营"
```

### 5. 散热（缺 4 条）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id cooler --supplement-keywords "风冷散热器 6热管 自营" "一体式水冷 280冷排 自营" "一体式水冷 360冷排 自营" "一体式水冷 420冷排 自营"
```

### 6. 一键顺序补爬（按上表顺序依次执行）

在 PowerShell 中可逐段复制执行；也可保存为 `补爬全部缺口.ps1` 后运行：

```powershell
cd d:\code\claude_code\self_support_crawl

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id cpu --supplement-keywords "英特尔酷睿i7 CPU 自营" "英特尔酷睿i5 CPU 自营"

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id gpu --supplement-keywords "RTX 5080 自营" "RTX 5070 Ti 自营"

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id ram --supplement-keywords "DDR4 16G 内存 自营"

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id psu --supplement-keywords "电脑电源 550W 自营" "电脑电源 650W 自营" "电脑电源 850W 自营" "电脑电源 1200W 自营"

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id cooler --supplement-keywords "风冷散热器 6热管 自营" "一体式水冷 280冷排 自营" "一体式水冷 360冷排 自营" "一体式水冷 420冷排 自营"
```

（请将 `cd` 路径改为本机实际项目路径。）

---

## 二、尚未开始爬的分组（整组抓取）

当前 `jd_query_csv` 下 **还没有** 对应 CSV 的分组为：**机箱**、**显示器**、**机箱风扇**。每条命令会跑完该组 JSON 内全部关键词，生成/覆盖该组 CSV。

### 1. 机箱（`case`）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id case
```

### 2. 显示器（`monitor`）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id monitor
```

### 3. 机箱风扇（`case_fan`）

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id case_fan
```

### 4. 三个分组顺序执行（机箱 → 显示器 → 机箱风扇）

```powershell
cd d:\code\claude_code\self_support_crawl

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id case

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id monitor

python jd_queries_group_crawl.py --out-dir ./jd_query_csv --only-group-id case_fan
```

---

## 三、可选：从某一关键词起「一条命令跑到 JSON 末尾」

若希望从某个搜索词开始，**连续爬完后续所有分组**（例如从电源 850W 起直到机箱风扇结束），可使用（与 `--supplement-keywords` 不要混用）：

```powershell
python jd_queries_group_crawl.py --out-dir ./jd_query_csv --start-from-keyword-substr 850W
```

子串需在「过滤后的分组顺序」里**唯一命中第一条**要开始的词；详见 **`使用说明_按JSON分组首屏爬取.md`**。

---

## 四、缺口清单（便于对照 JSON 核对）

| 分组 id | 类型 | 说明 |
|---------|------|------|
| `cpu` | 补爬 | 缺：`英特尔酷睿i7 CPU 自营`、`英特尔酷睿i5 CPU 自营` |
| `gpu` | 补爬 | 缺：`RTX 5080 自营`、`RTX 5070 Ti 自营` |
| `ram` | 补爬 | 缺：`DDR4 16G 内存 自营` |
| `psu` | 补爬 | 缺：`电脑电源 550W/650W/850W/1200W 自营`（各一条完整词，见第一节） |
| `cooler` | 补爬 | 缺：`风冷散热器 6热管 自营`，`一体式水冷 280/360/420冷排 自营` |
| `motherboard` | 无缺口 | 当前数据完整，无需补爬 |
| `ssd` | 无缺口 | 当前数据完整，无需补爬 |
| `case` | 未开始 | 见第二节 |
| `monitor` | 未开始 | 见第二节 |
| `case_fan` | 未开始 | 见第二节 |

> 若你本地 CSV 与上表不一致，请以 `自营爬虫搜索字段_queries.json` 为准，用脚本或 Excel 按「搜索字段」列做一次透视核对。
