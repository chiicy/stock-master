# stock-master TODO

本文件只记录当前 `stock-master` 明确缺失、但已被方法论或代码结构验证为有价值的数据能力。

原则：

- 缺口要写成 capability / 字段 / 口径，而不是泛泛的“数据不足”。
- 当前未接通的能力不应在 `README` / `SKILL.md` / 报告中伪装成已支持。
- 新增数据源时优先对齐 `datasource/schema.py` 的共享 contract。

## P0: 影响深度模式正确性的缺口

### 深度基本面

- `get_management_discussion(symbol, years=3)`
  - 目标：支撑 MD&A、管理层兑现度、客户/供应商集中度、会计政策变化判断。
- 三表标准化层
  - 目标：把 `income_statement / balance_sheet / cash_flow` 对齐到最近 3 年统一口径。
  - 需要字段：`fiscal_year / currency / unit / accounting_standard / restated`
- `get_peer_candidates(symbol)` / `get_peer_metrics(symbol, peers)`
  - 目标：支持同业 Top3 对比。
  - 至少要有：毛利率、净利率、ROE、ROIC、负债与现金流。
- 估值输入字段
  - 若要真正支持 `ROIC/WACC/DCF`，至少要补齐：
    - 税率
    - 有息负债成本 / 利息费用
    - Beta / 无风险利率 / ERP
    - 股本 / 市值 / 企业价值
    - CAPEX
    - 营运资本变动
    - 终值增长假设

### 深度技术面

- `get_intraday_bars(symbol, interval='1m', limit=240)`
  - 当前 `get_intraday()` 只是 quote alias，不满足分时分析。
- 更稳定的日线输入
  - 目标：支撑缺口、ADX、EMA50/EMA200、更长周期关键位。
  - 需要字段：`date/open/high/low/close/volume/amount`
- 缺口判定辅助字段
  - 最好补 `prev_close` 或完整前后日窗口，避免只能做保守描述。

## P1: 影响市场/板块分析完整性的缺口

- `get_index_quote(symbol)`
- `get_index_kline(symbol, period='daily')`
- `get_index_overview()`
  - 说明：当前市场概览主要依赖北向、板块资金和涨跌停广度，缺指数级数据。

- `get_limit_pool(date, side='up'|'down')`
  - 说明：当前只到涨跌榜，不足以支撑连板、炸板率、封单分析。
  - 需要字段：
    - 连板数
    - 首次封板时间
    - 最后封板时间
    - 封单额 / 封单量
    - 炸板标记

- `get_sector_snapshot(sector_type='industry'|'concept')`
- `get_sector_rotation(window=5)`
  - 说明：当前只有单次板块资金流，不足以支持轮动持续性判断。

- `get_lhb(date, symbol=None)`
- `get_margin_balance(symbol|date)`
  - 说明：融资融券 / 龙虎榜仍是缺口，只能在方法论里提醒，不能伪装支持。

## P2: 影响治理 / 法证 / ESG 的缺口

- `get_audit_opinion(symbol)`
- `get_executive_or_major_holder_trades(symbol)`
- `get_equity_incentive(symbol)`

- 法证稳定字段
  - 需要：
    - 应收 / 存货 / 应付
    - 商誉
    - 受限现金
    - 非经常性损益
    - 关联交易 / 其他应收 / 预付

- ESG / 披露事件层
  - 说明：当前只能提供方法论约束，缺少稳定事件或披露入口。

## P3: 结构级扩展

- `screen_stocks(criteria)`
  - 说明：选股能力应走专门 capability，不应继续挤占 `get_search()`。

- 港美股统一 contract 扩展
  - 当前只有部分 `quote/news` fallback。
  - 若要扩展，需要统一：
    - `kline`
    - `sector`
    - `fundamental`

- evidence metadata 容器
  - 目标：让深度基本面支持 `source note / table / page / formula inputs`
  - 当前 schema 只到 `meta / extensions / raw`，仍缺“可复核证据槽位”
