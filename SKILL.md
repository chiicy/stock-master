---
name: stock-master
description: 面向 A 股单股、板块、指数和市场分析的 Skill。负责在技术面、基本面、资金面、情绪面、板块面、消息面、预判面之间路由，并组织输出。适用于“分析某股票”“全面分析某股票”“多角度分析”“技术面/基本面/资金面怎么看”“板块怎么看”“综合判断后市”等请求；统一数据获取走 `datasource` 包。
---

# Stock Master

当前覆盖以 **A 股** 为主。若用户给的是港股、美股或其他市场，要先明确当前链路的覆盖边界，避免假装支持。

## 核心原则

- 证据优先：先列事实，再给判断
- 明确区分“工具直接返回的事实”和“基于方法论的推断”
- 多视角分析要结合大盘、板块、资金与个股自身信号，不孤立看单一指标
- 未来判断只做条件化推演，不做伪精确预测
- 数据不足时必须降级，不把缺失信息伪装成结论
- 深度技术面重点覆盖：支撑位、压力位、缺口观察、未来 3 个交易日的条件化判断
- 深度基本面重点覆盖：数据完整性、三表联动、关键比率、估值口径、风险排雷、同业对比

## 何时使用

当用户要求以下任一任务时，使用本 skill：
- 全面分析某只股票
- 从不同角度分析某只股票
- 只看技术面 / 基本面 / 资金面 / 情绪面 / 板块面 / 消息面
- 给出综合结论、后市判断、操作建议
- 查看大盘、板块轮动、情绪、北向、涨跌停等市场概览

以下请求也走本 skill，但会进入特定模式：
- `看看支撑压力` `有没有缺口` `未来三天怎么看`
  - 进入深度技术面模式，重点读取 `references/technical.md` + `references/prediction.md`
- `按价值投资看` `做个估值` `ROIC/WACC/DCF`
  - 进入深度基本面模式，重点读取 `references/fundamental.md`、`references/value-detective.md`、`references/financial-metrics.md`、`references/forensics-esg.md`
- `A股大盘怎么样` `板块轮动怎么看` `情绪面怎么样`
  - 进入市场概览模式，补充对应 reference

## 使用流程

1. 先识别分析对象：股票、板块、指数、市场
2. 再识别分析模式：单视角 or 多视角
3. 判断是轻量分析还是深度分析：
   - 深度技术面：用户明确要支撑位 / 压力位 / 缺口 / 未来三天
   - 深度基本面：用户明确要估值 / DCF / ROIC / 杜邦，且数据较完整
   - 市场概览：用户问大盘 / 市场情绪 / 北向 / 板块 / 涨跌停 / 连板时，优先走 `market_overview`
   - 默认多视角：技术 + 资金 + 板块 + 预判；需要时再加基本面 / 情绪 / 消息
4. 使用 `stock_master.datasource.DataSource` 统一取数；如需一键汇总，优先用 `scripts/analyze_stock.py`
5. 只读取所需的 reference：
   - 技术面 → `references/technical.md`
   - 基本面 → `references/fundamental.md`
   - 深度价值主框架 → `references/value-detective.md`
   - 深度价值公式口径 → `references/financial-metrics.md`
   - 法证排雷 / ESG → `references/forensics-esg.md`
   - 资金面 → `references/capital-flow.md`
   - 情绪面 → `references/sentiment.md`
   - 板块面 → `references/sector.md`
   - 消息面 → `references/news.md`
   - 综合预判 → `references/prediction.md`
6. 先给每个视角独立结论，再给综合结论
7. 输出时区分：
   - 事实层：价格、涨跌幅、指标、财务数据、资金流、已知事件
   - 推断层：偏多 / 偏空 / 震荡、估值判断、未来 3 日基准判断
8. 数据不足时要明确降级，不要硬把所有视角填满
9. 深度模式只面向 A 股；若标的是港股 / 美股 / 其他市场，要直接降级说明，不进入同一深度框架
10. 当用户明确要深度价值分析时，按下面的顺序组织：
   - 数据完整性与口径
   - 生意本质
   - 三表联动与关键比率
   - 估值与隐含预期
   - 风险排雷 / ESG
   - 同业对比
   - 情景化介入计划

## 视角路由规则

### 单视角触发词
- 技术面：`技术分析` `图形` `走势` `均线` `RSI` `MACD` `KDJ` `支撑位` `压力位`
- 基本面：`基本面` `财报` `估值` `ROE` `ROIC` `毛利率` `现金流` `护城河`
- 资金面：`资金流` `主力` `北向` `融资融券` `龙虎榜`
- 情绪面：`情绪` `涨停` `跌停` `换手率` `热度` `赚钱效应`
- 板块面：`板块` `行业` `概念` `轮动` `龙头` `同板块`
- 消息面：`新闻` `公告` `研报` `政策` `消息`
- 预判面：`后市` `明天怎么看` `未来三天` `操作建议` `预判`

### 多视角触发词
- `全面分析`
- `综合分析`
- `多角度分析`
- `从不同角度看看`
- `这股票怎么样`
- `帮我完整判断`

### 默认组合
- `X 怎么样` / `分析 X` → 技术面 + 资金面 + 板块面 + 预判面
- `全面分析 X` → 技术面 + 基本面 + 资金面 + 情绪面 + 板块面 + 消息面 + 预判面
- `短线怎么看` → 技术面 + 资金面 + 情绪面 + 预判面
- `长线怎么看` → 基本面 + 板块面 + 消息面
- `分析 X 的支撑压力/缺口/未来三天` → 技术面 + 预判面，按深度技术面结构输出
- `帮我做个价投报告` → 基本面优先；若财报不完整，要先声明只能做轻量版

## 数据获取约束

统一通过 `stock_master.datasource.DataSource` 思考数据需求。

当前主数据源：
- `AkShare`
- `adata`
- `BaoStock`
- `opencli family`

当前已接入的 opencli family：
- `opencli-dc`
- `opencli-xq`
- `opencli-xueqiu`
- `opencli-sinafinance`
- `opencli-bloomberg`
- `opencli-yahoo-finance`
- `opencli-iwc`

统一按能力思考数据需求：
- 行情：`get_quote`, `get_kline`, `get_intraday`
- 资金：`get_money_flow`, `get_north_flow`, `get_sector_money_flow`
- 基本面：`get_financial`, `get_report`, `get_income_statement`, `get_balance_sheet`, `get_cash_flow`
- 治理 / 分红：`get_main_holders`, `get_shareholder_changes`, `get_dividend`
- 板块：`get_sector_list`, `get_sector_members`
- 情绪：`get_limit_up`, `get_limit_down`
- 消息：`get_news`, `get_research`, `get_announcements`

如果某类数据缺失：
- 明确说缺什么
- 不要把该视角写成已完成
- 允许降级输出
- 缺口、ADX、EMA50/EMA200、WACC、DCF、同业对比等字段，只能在数据足够时使用
- 数据链路未直接返回的指标或事件，不要编造精确数值
- 深度基本面优先使用 `get_deep_fundamental_bundle`；若不可用，再按需分别调用三张表、公告、新闻、研报、股东、分红接口

## 输出结构

### 单视角输出
1. 一行结论
2. 关键证据 3~6 条
3. 风险 / 失效条件

### 多视角输出
1. 基础数据快照
2. 技术面
3. 基本面
4. 资金面
5. 情绪面
6. 板块面
7. 消息面
8. 综合判断 / 预判

### 综合结论要求
区分：
- 一致性信号
- 矛盾信号
- 时间维度：短线 / 中线 / 长线
- 风险提示：什么条件出现后需要推翻当前判断

若是深度技术面：
- 必须覆盖趋势、关键位、缺口观察、未来 3 个交易日判断、操作建议
- 缺口数据不够时，要直接写“当前工具未直接返回缺口明细”

若是深度基本面：
- 先写数据完整性和分析模式（轻量 / 深度）
- 至少覆盖生意模式、盈利质量、现金流质量、财务健康、估值口径、主要风险
- 有条件时加入杜邦、ROIC/WACC、DCF、同业对比；没条件时明确说明缺口
- 若用户要“完整价投报告”，优先按 `references/value-detective.md` 的骨架组织

## Reference 读取提示
- 做技术分析前，读 `references/technical.md`
- 做基本面分析前，读 `references/fundamental.md`
- 做深度价值分析前，补读 `references/value-detective.md`
- 算深度价值指标前，读 `references/financial-metrics.md`
- 做财务排雷或 ESG 风险时，读 `references/forensics-esg.md`
- 做资金面分析前，读 `references/capital-flow.md`
- 做情绪面分析前，读 `references/sentiment.md`
- 做板块面分析前，读 `references/sector.md`
- 做消息面分析前，读 `references/news.md`
- 做综合预判前，读 `references/prediction.md`

## 可执行入口
- 一键汇总 JSON：`python3 scripts/analyze_stock.py 603966 --pretty`
- 一键输出文本报告：`python3 scripts/analyze_stock.py 603966 --format text`
- 统一数据检测：`python3 scripts/data_source.py`

更详细的维护、扩展、测试与排障说明见 `docs/maintenance.md`。

## 风格约束
- 先证据，后结论
- 不把预测说成事实
- 数据不够时明确降级
- 对短线和长线的判断不要混写
- 当基本面数据缺失时，不要强行做深度价值判断
- 明确区分“工具直接返回”与“基于方法论推断”
- 尽量用条件化语言写预判：如果……则……；跌破 / 站回哪些位置会失效
- 避免堆术语，优先给少量高价值结论
