# wgg_study Lotto Toolkit

本仓库提供一个用于抓取、规范化、分析与生成中国福利彩票双色球（Double Chromosphere）号码的 Python 工具集。

> **免责声明**：本项目仅用于数据研究与娱乐，生成号码**不保证中奖**。请理性看待彩票游戏。

## 环境要求

- Python 3.11 或更高版本

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install --upgrade pip
pip install -e .
```

## 使用方法

命令入口位于 `python -m lotto`，包含 `fetch`、`analyze`、`generate` 三个子命令。

### 抓取历史开奖数据

```bash
python -m lotto fetch --years 15 --source 500 --out data/draws.csv
```

- `--years`：抓取近多少年的数据，默认 15。
- `--source`：数据源，`official` 为福利彩票官网，`500` 为 500.com 备份源。若官方源抓取失败会自动切换。
- `--out`：规范化 CSV 输出路径，默认 `data/draws.csv`。

### 分析开奖数据

```bash
python -m lotto analyze --in data/draws.csv --report out/report.md --json out/metrics.json
```

分析结果将输出 Markdown 报告与 JSON 指标，涵盖频次、遗漏、和值、奇偶、连号、同尾、跨度等统计。

### 生成推荐号码

```bash
python -m lotto generate --in data/draws.csv --count 5 --strategy weighted --seed 123 --out out/picks.txt
```

- `--count`：生成注数，默认 5。
- `--strategy`：`uniform`（均匀随机）或 `weighted`（基于频次加权）。
- `--seed`：随机种子，保证结果可复现。
- `--out`：输出文件，默认 `out/picks.txt`。

输出格式示例：

```
01 05 10 18 21 30 | 06
```

## 测试

```bash
pytest
```

## 数据输出

- `data/draws.csv`：抓取并规范化后的历史开奖数据。
- `out/report.md`：分析报告。
- `out/metrics.json`：分析指标 JSON。
- `out/picks.txt`：推荐号码列表。

## 注意事项

- 抓取数据时请遵守数据源网站的使用条款，合理设置请求间隔。
- 若网络访问受限，可使用已抓取的数据文件进行分析与号码生成。
