# stock-master

A standard Python package for stock datasource aggregation and stock analysis, extracted from the Hermes `stock-master` skill.

当前工程已经完成 provider 路由重构：
- **single-hit / first-success**：适用于 quote、kline、资金流、板块成员等“命中一个可信源即可”的能力。
- **aggregate / merged**：适用于 news、research、announcements 这类“需要多源补充”的能力；对外返回 `source="merged"`、`sources=[...]`、`fallback_path=[...]`。

当前覆盖仍以 **A 股** 为主；但 opencli family 已补入一部分跨市场能力，尤其是非 A 股 quote 的 `yahoo-finance` 兜底，以及资讯/事件聚合所需的 `sinafinance / xueqiu / bloomberg / iwc`。

## Install

Preferred on this machine:

```bash
uv venv .venv
.venv/bin/pip install -e .
```

Fallback if your Python already has pip available:

```bash
python3 -m pip install -e .
```

Required runtime dependencies:
- akshare
- adata
- baostock

## CLI usage

Fast path wrappers:

```bash
python3 scripts/data_source.py
python3 scripts/analyze_stock.py 603966 --format text
```

Standard installed entry points:

```bash
stock-master-datasource
stock-master-analyze 603966 --format text
stock-master-install-opencli --quiet
```

安装自带的 OpenCLI 自定义命令软链到本机：

```bash
stock-master-install-opencli --target-dir ~/.opencli/clis
```

它会把打包随仓库分发的 `dc/`、`xq/`、`iwc/` YAML 命令以软链方式安装到目标目录，方便随项目一并分发和复用。

## Capability matrix

| Capability family | Dispatch strategy | Primary provider families | Notes |
| --- | --- | --- | --- |
| `get_search` | `first_success` | 代码/标的检索：`opencli-dc -> opencli-xq -> opencli-xueqiu -> akshare/adata/baostock`；自然语言/主题问句：`opencli-iwc` 前置 | `iwc` 不再只是最后兜底；自然语言 query 会优先命中 |
| `get_quote` / `get_snapshot` / `get_intraday` | `first_success` + `sufficient_fields` | A 股优先 `akshare -> adata -> baostock`，再到 `opencli-xq -> opencli-dc -> opencli-xueqiu -> opencli-sinafinance`；全球优先 `opencli-yahoo-finance -> opencli-xq -> opencli-xueqiu` | quote/snapshot 属于 short-circuit 能力，只有命中真实价格字段才允许停止 |
| `get_kline` | `first_success` | 本地 Python providers；opencli fallback 为 `dc -> xq -> xueqiu` | 当前未接 `yahoo-finance history`，因为本机 opencli 无此命令 |
| `get_money_flow` / `get_north_flow` / `get_sector_money_flow` | `first_success` | `akshare/adata/baostock` 优先，`opencli-dc` 兜底 | `dc` 提供 stock/north/sector flow |
| `get_sector_list` / `get_sector_members` | `first_success` | 本地 Python providers；`opencli-dc` 兜底 | `sector-members` 已接入 |
| `get_limit_up` / `get_limit_down` | `first_success` | 本地 Python providers；`opencli-dc` 兜底 | 对应 `top-gainers/top-losers` |
| `get_news` | `aggregate` | A 股优先 `opencli-sinafinance + opencli-xueqiu + opencli-bloomberg`；全球优先 `opencli-bloomberg + opencli-yahoo-finance + opencli-xueqiu` | news 是聚合能力，对外返回 `source="merged"`、`sources=[...]` |
| `get_research` | `aggregate` | A 股优先 `akshare/adata/baostock`，再补 `opencli-xueqiu/opencli-iwc`；全球主要依赖 `opencli-xueqiu` | 真实条目统一补齐 `title/date/url/source_channel/kind` |
| `get_announcements` | `aggregate` | A 股优先官方/结构化源，再补 `opencli-xueqiu/opencli-iwc`；全球保留 opencli 事件线索 | announcements 同样聚合，不伪装成单一官方源 |

## OpenCLI provider family actually wired

当前 `stock_master.datasource.providers.opencli` 已实际接线的 opencli source family：

- `opencli-dc`
  - `search`
  - `quote`
  - `history`
  - `stock-flow`
  - `north-flow`
  - `sector-flow`
  - `sector-members`
  - `top-gainers`
  - `top-losers`
- `opencli-xq`
  - `search`
  - `quote`
  - `history`
- `opencli-xueqiu`
  - `search`
  - `stock`
  - `kline`
  - `comments`
  - `earnings-date`
- `opencli-sinafinance`
  - `stock`
  - `news`
  - `rolling-news`
- `opencli-bloomberg`
  - `markets`
- `opencli-yahoo-finance`
  - `quote`
- `opencli-iwc`
  - `query`

本机核验到的 opencli 版本：`1.6.9`。

## Provider routing rules

- 路由契约定义在 `src/stock_master/datasource/interface.py` 的 `CapabilitySpec` / `@capability(...)`。
- `src/stock_master/datasource/service.py` 只读取 capability spec，并结合 `capability_routing_hint()` 与 `preferred_provider_groups()` 重排 provider 顺序。
- `src/stock_master/datasource/runtime.py` 中：
  - `first_success`：命中首个“成功且字段充分”的 provider 即返回。
  - `aggregate`：遍历所有可用 provider，合并 `items/rows`，结果对外保持 `source="merged"`。
- `DataSource.get_snapshot()` 直接走 quote contract，因此与 `get_quote()` 共享 sufficiency / routing / short-circuit 规则。
- `fallback_path` 只记录真实尝试过的已启用 provider。
- 当前 aggregate 去重策略是 **record-level stable identity**（JSON dump / repr），不是早期设想的 `url/title/date/symbol` 组合键。

## Tests

Unit tests:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'
```

常用最终验收命令：

```bash
.venv/bin/python scripts/data_source.py
.venv/bin/python scripts/analyze_stock.py 603966 --pretty
.venv/bin/python scripts/analyze_stock.py 603966 --format text
opencli --version
opencli list
opencli xq --help
opencli dc --help
opencli xueqiu --help
opencli sinafinance --help
opencli iwc --help
opencli bloomberg --help
opencli yahoo-finance --help
```

### Latest acceptance snapshot

基于本次 capability-aware + market/query-aware routing 收敛复核：

- `DataSource` 已新增 `_providers_for(capability, first_arg)`，每次 dispatch 都会实际执行 `preferred_provider_groups()` + `reorder_provider_sequence()`。
- `get_quote/get_snapshot` 继续使用 short-circuit contract；A 股优先本地结构化 provider，全球优先 `opencli-yahoo-finance`。
- `get_news/get_research/get_announcements` 保持 aggregate contract，对外返回 `source="merged"` 与 `sources=[...]`。
- `OpenCliProvider` 兼容层已与 family routing contract 对齐：
  - 自然语言 `get_search` 优先 `opencli-iwc`
  - 全球 `get_quote` 优先 `opencli-yahoo-finance`
  - family `get_news` 会按 market-aware 顺序聚合 `bloomberg/xueqiu/sinafinance`
- `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'`：**通过，80 tests / skipped=5**。

Live tests are opt-in because they depend on network, third-party data providers, and current market availability:

```bash
STOCK_MASTER_RUN_LIVE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'
```
