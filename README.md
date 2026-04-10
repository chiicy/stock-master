# stock-master

`stock-master` 是一个 skill-first、package-first 的股票分析工程。

它的目标不是“再包一层 CLI”，而是把多数据源、多分析视角、多 skill 方法论收束成一套可复用的基础设施：

- `scripts/` 只保留 skill-facing wrapper
- `src/stock_master/` 是唯一实现源
- `datasource` 负责取数、清洗、fallback、contract
- `analysis` 只消费公共结构，不直接猜测某个 provider 的原始字段

当前覆盖仍以 **A 股** 为主，但 opencli family 已承担一部分跨市场 quote / news / event 兜底能力。

## Install

推荐在仓库内使用项目虚拟环境：

```bash
uv venv .venv
.venv/bin/pip install -e .
```

如果已有可用 Python / pip：

```bash
python3 -m pip install -e .
```

主要运行依赖：

- `akshare`
- `adata`
- `baostock`

## Quick Start

Skill wrapper：

```bash
python3 scripts/data_source.py
python3 scripts/analyze_stock.py 603966 --format text
```

安装后的入口：

```bash
stock-master-datasource
stock-master-analyze 603966 --format text
stock-master-install-opencli --quiet
```

安装随仓库分发的 opencli 自定义命令：

```bash
stock-master-install-opencli --target-dir ~/.opencli/clis
```

## Design Goals

这个仓库围绕 4 个目标设计：

1. 一个能力只保留一个实现源。`scripts/` 不再复制 `src/` 的逻辑。
2. 所有 provider 都输出同一套 datasource contract，而不是“每家自己返回一坨 dict”。
3. provider 边界完成数据清洗和字段映射，`analysis` 不负责猜源字段。
4. README 解释项目结构与使用入口；更细的维护与排障说明收敛到 `docs/maintenance.md`。

## Project Layout

```text
stock-master/
├── SKILL.md
├── todo.md
├── references/
├── scripts/
│   ├── _bootstrap.py
│   ├── analyze_stock.py
│   └── data_source.py
├── src/stock_master/
│   ├── analysis/
│   │   ├── intents.py
│   ├── common/
│   ├── datasource/
│   │   ├── backend.py
│   │   ├── interface.py
│   │   ├── runtime.py
│   │   ├── schema.py
│   │   ├── service.py
│   │   └── providers/
│   │       ├── akshare.py
│   │       ├── adata.py
│   │       ├── baostock.py
│   │       ├── opencli.py
│   │       └── opencli_family/
│   └── opencli_clis/
└── tests/
```

目录分工：

- `SKILL.md`
  - 定义 skill 级别的意图识别、分析模式、输出约束。
- `references/*.md`
  - 定义具体分析维度的方法论，不承载运行时代码。
- `scripts/*.py`
  - 只做 wrapper / bootstrap / CLI 跳转。
- `src/stock_master/datasource/schema.py`
  - 定义 provider 共用的数据结构契约。
- `src/stock_master/datasource/providers/*.py`
  - 各 provider 的真实取数与字段映射实现。
- `src/stock_master/datasource/runtime.py`
  - 负责 `first_success` / `aggregate` dispatch。
- `src/stock_master/datasource/service.py`
  - 负责缓存、provider 排序和 `DataSource` facade。
- `src/stock_master/analysis/intents.py`
  - 负责 task-first 路由：区分市场概览、单股综合、深度技术面、深度基本面。
- `src/stock_master/analysis/*.py`
  - 只消费公共 contract，生成结论与渲染输出。
- `todo.md`
  - 记录当前未满足的数据 capability / 字段缺口，避免在报告里假装支持。

## Report Modes

`stock-master` 当前支持两类主报告 + 两类深度模式：

- `market_overview`
  - 面向大盘、板块、情绪、北向、涨跌停等问句
  - 当前主要基于北向资金、板块资金、涨跌停广度
- `stock_report`
  - 默认单股综合分析
- `deep_technical`
  - 重点是 `EMA50/EMA200`、`ADX`、支撑/压力、缺口保守表达、未来 3 日判断
- `deep_fundamental`
  - 重点是 gate、证据质量、估值准备度、法证/ESG 风险与数据缺口透明

约束：

- 深度技术面 / 深度基本面当前只面向 A 股。
- 非 A 股不会伪装进入同一套深度模式，只会保留通用报告或边界说明。

## Shared Data Contract

所有 provider 都必须返回 `stock_master.datasource.schema` 约束的共享 envelope。

### Top-level envelope

所有 capability 至少共享这些顶层字段：

- `status`
  - `ok` / `empty` / `placeholder`
- `capability`
  - 例如 `quote`、`kline`、`news`
- `symbol` 或 `query`
  - 按上下文保留
- `market`
  - `a_share` / `hk` / `global` / `unknown`
- `source`
  - runtime 标记的 provider 名称
- `source_channel`
  - provider 内部的真实子来源，如 `xq.quote`、`dc.stock-flow`
- `fallback_path`
  - 真实尝试过的 provider 路径
- `items` 或 `rows`
  - 列表能力的主容器
- `meta`
  - 通用元信息，如 `schema_version`、`primary_container`
- `extensions`
  - provider 独有但暂未标准化的稳定字段
- `raw`
  - 需要保留原始/半原始 payload 时使用

说明：

- 为了兼容旧分析代码，provider 自定义字段仍可保留在原位置。
- 新代码应优先读取公共字段，其次读 `extensions`，最后才回退到 provider 自定义字段。

### Record-level contract

`items` / `rows` 里的每一条记录也按同样原则标准化。

公共记录字段按能力分组如下：

- 搜索类
  - `symbol` `code` `name` `title` `url`
- 行情类
  - `price` `percent` `change` `open` `high` `low` `prevClose` `volume` `amount` `turnoverRate`
- K 线类
  - `date` `open` `high` `low` `close` `volume` `amount`
- 资讯/事件类
  - `title` `content` `summary` `date` `publish_time` `url` `author` `kind`

兼容性策略：

- 英文 canonical 字段始终优先。
- 必要的中文别名会保留，例如 `最新价`、`涨跌幅`、`公告标题`、`报告名称`。
- provider 独有字段会进入 `extensions`，必要时再保留 `raw`。

### Contract examples

`quote`：

```python
{
    "status": "ok",
    "capability": "quote",
    "symbol": "SH603966",
    "market": "a_share",
    "source_channel": "xq.quote",
    "price": 13.9,
    "percent": 0.58,
    "最新价": 13.9,
    "涨跌幅": 0.58,
    "meta": {
        "schema_version": 1,
        "capability": "quote",
        "market": "a_share",
    },
}
```

`news`：

```python
{
    "status": "ok",
    "capability": "news",
    "items": [
        {
            "title": "新浪财经头条",
            "date": "2026-04-10",
            "url": "https://...",
            "kind": "news",
            "source_channel": "sinafinance.news",
            "meta": {
                "schema_version": 1,
                "capability": "news",
                "kind": "news",
            },
        }
    ],
    "meta": {
        "schema_version": 1,
        "capability": "news",
        "primary_container": "items",
        "items_count": 1,
    },
}
```

## Provider Architecture

### Layers

数据层分 4 层：

1. `backend.py`
   - 检测依赖、调用模块 worker、调用 opencli。
2. `providers/*.py`
   - 执行真实取数，把源字段映射到共享 contract。
3. `runtime.py`
   - 按 capability contract 做 `first_success` 或 `aggregate`。
4. `service.py`
   - 负责缓存、路由 hint、provider 优先级和 facade。

### Runtime strategies

- `first_success`
  - 适用于 `quote`、`kline`、资金流、板块成员等。
  - 只有命中足够字段时才 short-circuit。
- `aggregate`
  - 适用于 `news`、`research`、`announcements`。
  - 结果对外保持 `source="merged"`，同时保留 `sources=[...]`。

### Capability matrix

| capability | 策略 | 主路由 |
| --- | --- | --- |
| `get_search` | `first_success` | 代码/标的检索优先 `opencli-dc -> opencli-xq -> opencli-xueqiu`；自然语言/主题问句优先 `opencli-iwc` |
| `get_quote` / `get_snapshot` / `get_intraday` | `first_success` + sufficient fields | A 股优先 `akshare -> adata -> baostock`，全球优先 `opencli-yahoo-finance` |
| `get_kline` | `first_success` | 本地 Python providers 为主，opencli fallback 为 `dc -> xq -> xueqiu` |
| `get_money_flow` / `get_north_flow` / `get_sector_money_flow` | `first_success` | 本地 Python providers 优先，`opencli-dc` 兜底 |
| `get_sector_list` / `get_sector_members` | `first_success` | 本地 Python providers 优先，`opencli-dc` 兜底 |
| `get_limit_up` / `get_limit_down` | `first_success` | 本地 Python providers 优先，`opencli-dc` 兜底 |
| `get_news` | `aggregate` | A 股优先 `sinafinance + xueqiu + bloomberg`；全球优先 `bloomberg + xueqiu` |
| `get_research` | `aggregate` | A 股优先结构化 provider，再补 `xueqiu / iwc` |
| `get_announcements` | `aggregate` | A 股优先官方/结构化 provider，再补 `xueqiu / iwc` |

## OpenCLI Family

`opencli` 不再是一个巨大 provider 文件，而是一组 family provider：

- `opencli-dc`
- `opencli-xq`
- `opencli-xueqiu`
- `opencli-sinafinance`
- `opencli-bloomberg`
- `opencli-yahoo-finance`
- `opencli-iwc`

兼容层：

- `src/stock_master/datasource/providers/opencli.py`
  - 仅作为旧导入路径的兼容导出层
- `src/stock_master/datasource/providers/opencli_family/composite.py`
  - 保留 legacy composite provider，供旧测试/直连使用

拆分原则：

- 一个 opencli source family 一个文件
- 一个 family 只管自己的 CLI 命令和字段映射
- 通用清洗逻辑放 `opencli_family/base.py`
- family 之间的组合与顺序交给 runtime / routing hint

## How To Add A Provider

新增 provider 时按下面顺序做：

1. 在 `src/stock_master/datasource/providers/` 新增一个文件。
2. 继承 `ModuleProvider` 或 `BaseProvider`。
3. 只实现自己真正支持的 `get_*` 方法。
4. 在 provider 内完成字段映射，并输出共享 contract。
5. 在 `tests/` 中补 provider contract 测试。
6. 在 `providers/__init__.py` 注册 provider map。
7. 视情况更新 `preferred_provider_groups()`。

### Provider rules

- 成功返回 dict envelope，失败返回 `False`
- 空数据返回 `False` 或 `status="empty"`，不要伪造占位数据
- 清洗和格式化要在 provider 边界完成
- 需要保留源差异时，优先放进 `extensions`
- 需要保留原始记录时，再补 `raw`

## How To Add An OpenCLI Family Provider

1. 在 `src/stock_master/datasource/providers/opencli_family/` 新增 family 文件。
2. 继承 `OpenCliFamilyProvider`。
3. 调用 `_opencli_json(...)` 获取原始结果。
4. 通过：
   - `_normalize_search_payload`
   - `_normalize_quote_payload`
   - `_normalize_kline_payload`
   - `_fetch_standardized_items`
   进入共享 contract。
5. 在 `tests/test_provider_opencli.py` 增补真实字段映射断言。

## Testing Strategy

测试分三层：

- schema / runtime contract test
  - 保证 envelope、fallback、aggregate 和映射结构稳定
- provider unit test
  - 校验每个 provider 的字段映射与 routing
- live smoke test
  - 仅在显式开启时验证第三方依赖和网络环境

常用命令：

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'
```

live smoke：

```bash
STOCK_MASTER_RUN_LIVE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'
```

最终验收建议：

```bash
.venv/bin/python scripts/data_source.py
.venv/bin/python scripts/analyze_stock.py 603966 --format text
.venv/bin/python -m stock_master 603966 --format text
```

## Current Completion Status

当前仓库已经完成以下基础重构：

- 删除 `scripts/` 下重复实现，只保留 wrapper
- `src/` 成为唯一实现源
- `opencli` provider 拆为 family package
- 引入共享 `datasource/schema.py`
- provider / runtime / service 全部接入共享 contract
- 关键映射已补注释，并由单测校验
- 新增 task-first intent 层与 `market_overview` report builder
- 技术面已补 `EMA50/EMA200`、`ADX`、综合评分与市场环境联读
- 基本面已补深度 gate、证据质量、估值准备度与法证风险槽位
- 明确缺口已沉到 [todo.md](/Users/cychi/.agents/skills/stock-master/todo.md)

如果后续要继续扩展，这份 README 应该足够回答下面几个问题：

- 代码应该放在哪一层
- provider 应该返回什么结构
- 哪里做字段清洗
- 哪里做 fallback / aggregate
- 新测试该写在哪一类
