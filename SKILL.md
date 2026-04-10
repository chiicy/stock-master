---
name: stock-master
description: 面向 A 股单股、板块、指数和市场分析的总控 Skill。统一调度技术面、基本面、资金面、情绪面、板块面、消息面、预判面等 reference。适用于“分析某股票”“全面分析某股票”“多角度分析”“技术面/基本面/资金面怎么看”“板块怎么看”“综合判断后市”等请求。主 skill 负责路由、选视角、组织输出；统一数据获取走 `datasource` 包。
---

# Stock Master

这是一个主控 / 编排 skill，不是单一分析器。

当前覆盖以 **A 股** 为主。若用户给的是港股、美股或其他市场，要先明确当前链路的覆盖边界，避免假装支持。

## 核心原则

- 证据优先：先列事实，再给判断
- 明确区分“工具直接返回的事实”和“基于方法论的推断”
- 深度技术面重点覆盖：支撑位、压力位、缺口观察、未来 3 个交易日的条件化判断
- 深度基本面重点覆盖：数据完整性、三表联动、关键比率、估值口径、风险排雷、同业对比
- 多视角分析要结合大盘、板块、资金与个股自身信号，不孤立看单一指标
- 未来判断只做条件化推演，不做伪精确预测
- 数据不足时必须降级，不把缺失信息伪装成结论
- 技术与实现层保持分层：Router -> DataSource -> Analyzer -> Formatter

固定分工：
- `SKILL.md`：识别意图、决定读取哪些 reference、约束输出结构
- `references/*.md`：定义某一分析维度该看什么、怎么判断、怎么写结论
- `scripts/data_source.py`：统一数据源诊断 wrapper，优先复用项目 `.venv` 并转到包内入口
- `scripts/analyze_stock.py`：分析 wrapper，优先复用项目 `.venv` 并转到包内入口
- `src/stock_master/datasource/interface.py`：统一数据接口签名，provider 成功返回 dict，失败统一返回 `False`
- `src/stock_master/datasource/schema.py`：provider 共用数据结构 contract，统一约束 `status/capability/items|rows/meta/extensions/raw`
- `src/stock_master/datasource/backend.py`：负责环境探测、venv 执行、opencli 调用
- `src/stock_master/datasource/runtime.py`：负责 provider router、优先级 fallback、`first_success/aggregate` dispatch、超时与 source 打标
- `src/stock_master/datasource/service.py`：负责缓存和 `DataSource` 门面聚合
- `src/stock_master/datasource/providers/*.py`：provider 导出层与 provider map
- `src/stock_master/datasource/providers/opencli_family/*.py`：opencli family 按 source family 拆分后的 provider 实现
- `src/stock_master/datasource/__init__.py`：数据层公共包入口，统一导出 `DataSource`
- `src/stock_master/analysis/cli.py`：分析层 CLI 参数与输出编排
- `src/stock_master/analysis/intents.py`：task-first 路由，区分 `market_overview / stock_report / deep_technical / deep_fundamental`
- `src/stock_master/analysis/report.py`：分析报告编排入口
- `src/stock_master/analysis/summaries.py`：技术面/资金面/基本面/消息面/预判的汇总逻辑
- `src/stock_master/analysis/extractors.py`：字段提取和行归一化 helper
- `src/stock_master/analysis/indicators.py`：技术指标纯函数
- `src/stock_master/analysis/fundamentals.py`：基本面计算纯函数
- `src/stock_master/analysis/render.py`：文本渲染
- `todo.md`：当前未满足的数据 capability / 字段缺口清单
- `src/stock_master/common/cache.py`：缓存读写
- `src/stock_master/common/symbols.py`：代码规范化
- `src/stock_master/common/system.py`：系统工具
- `tests/test_*.py`：单元测试与 live smoke/contract 测试

## 何时使用

当用户要求以下任一任务时，优先使用本 skill：
- 全面分析某只股票
- 从不同角度分析某只股票
- 只看技术面 / 基本面 / 资金面 / 情绪面 / 板块面 / 消息面
- 给出综合结论、后市判断、操作建议

以下请求默认也走本 skill，但会进入特定方法论模式：
- `看看支撑压力` `有没有缺口` `未来三天怎么看`
  - 进入深度技术面模式，重点读取 `references/technical.md` + `references/prediction.md`
- `按价值投资看` `做个估值` `ROIC/WACC/DCF`
  - 进入深度基本面模式，重点读取 `references/fundamental.md`、`references/value-detective.md`、`references/financial-metrics.md`、`references/forensics-esg.md`
- `A股大盘怎么样` `板块轮动怎么看` `情绪面怎么样`
  - 进入市场/板块/情绪模式，补充对应 reference

## 主流程

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
7. 输出时始终区分：
   - 事实层：价格、涨跌幅、指标、财务数据、资金流、已知事件
   - 推断层：偏多 / 偏空 / 震荡、估值判断、未来 3 日基准判断
8. 数据不足时要明确降级，而不是硬把所有视角填满
9. 深度模式只面向 A 股；若标的是港股 / 美股 / 其他市场，要直接降级说明，不要假装进入同一深度框架
10. 当用户明确要深度价值分析时，默认按下面的顺序组织：
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

当前数据源分层：
- 第一层：`AkShare`
- 第二层：`adata`
- 第三层：`BaoStock`
- 第四层：`opencli family`
  - `opencli-dc`
  - `opencli-xq`
  - `opencli-xueqiu`
  - `opencli-sinafinance`
  - `opencli-bloomberg`
  - `opencli-yahoo-finance`
  - `opencli-iwc`
- 注意：`opencli` 不再只是单一 provider 名称，而是多个 source family 的统称；不同 capability 的路由顺序不同。

新增数据源时：
- 优先在 `src/stock_master/datasource/providers/<source>.py` 或 `src/stock_master/datasource/providers/opencli_family/<source>.py` 中新增 provider
- 一个数据源一个文件，便于后续独立扩充和测试
- provider 只重写自己支持的方法；不支持、报错、超时都返回 `False`
- 由 `src/stock_master/datasource/runtime.py` 按优先级统一 fallback
- `fallback_path` 只记录真实尝试过的已启用 provider
- 保持输出字段与 AkShare 风格兼容，并保留 `source` / `fallback_path`

输出要求：
- 优先返回 AkShare 风格中文字段
- 同时保留少量稳定英文别名供脚本聚合
- 返回中应保留 `source` 和 `fallback_path`
- 新增 contract 要求：
  - 顶层统一保留 `status`、`capability`、`meta`
  - provider 独特但稳定的字段优先放 `extensions`
  - 需要回溯原始记录时再保留 `raw`
  - `analysis` 默认只消费公共字段，不再依赖某家 provider 的私有命名

### Capability matrix（当前代码事实）

| capability | 策略 | 当前主路由 | 说明 |
| --- | --- | --- | --- |
| `get_search` | `first_success` | 代码/标的检索优先 `opencli-dc -> opencli-xq -> opencli-xueqiu`；自然语言/主题问句优先 `opencli-iwc` | query-aware routing 已落到 datasource 主路由 |
| `get_quote` / `get_snapshot` / `get_intraday` | `first_success` + `sufficient_fields` | A 股优先 `akshare/adata/baostock`，再到 `opencli-xq -> opencli-dc -> opencli-xueqiu -> opencli-sinafinance`；全球优先 `opencli-yahoo-finance -> opencli-xq -> opencli-xueqiu` | 命中真实价格字段后才允许 short-circuit；`snapshot` 共享 quote contract |
| `get_kline` | `first_success` | 本地 Python providers；opencli fallback 为 `dc -> xq -> xueqiu` | 仍以 A 股为主 |
| `get_money_flow` / `get_north_flow` / `get_sector_money_flow` | `first_success` | `akshare/adata/baostock` 优先，`opencli-dc` 兜底 | `dc` 提供 stock/north/sector flow |
| `get_sector_list` / `get_sector_members` | `first_success` | 本地 Python providers；`opencli-dc` 兜底 | `sector-members` 已接线 |
| `get_limit_up` / `get_limit_down` | `first_success` | 本地 Python providers；`opencli-dc` 兜底 | 对应 `top-gainers/top-losers` |
| `get_news` | `aggregate` | A 股优先 `opencli-sinafinance + opencli-xueqiu + opencli-bloomberg`；全球优先 `opencli-bloomberg + opencli-xueqiu` | 对外返回 `source="merged"` |
| `get_research` | `aggregate` | A 股优先 `akshare/adata/baostock`，再补 `opencli-xueqiu/opencli-iwc`；全球主要依赖 `opencli-xueqiu` | 统一补齐 `title/date/url/source_channel/kind` |
| `get_announcements` | `aggregate` | A 股优先官方/结构化源，再补 `opencli-xueqiu/opencli-iwc`；全球保留 opencli 事件线索 | 当前是事件线索聚合，不伪装成官方公告源 |

### OpenCLI source family（已接入）

已确认接入并在 diagnostics 中可见：
- `opencli-dc`：`search` / `quote` / `history` / `stock-flow` / `north-flow` / `sector-flow` / `sector-members` / `top-gainers` / `top-losers`
- `opencli-xq`：`search` / `quote` / `history`
- `opencli-xueqiu`：`search` / `stock` / `kline` / `comments` / `earnings-date`
- `opencli-sinafinance`：`stock` / `news` / `rolling-news`
- `opencli-bloomberg`：`markets`
- `opencli-yahoo-finance`：`quote`
- `opencli-iwc`：`query`

统一通过 `stock_master.datasource.DataSource` 思考数据需求：
- 行情：`get_quote`, `get_kline`, `get_intraday`
- 资金：`get_money_flow`, `get_north_flow`, `get_sector_money_flow`
- 基本面：`get_financial`, `get_report`, `get_income_statement`, `get_balance_sheet`, `get_cash_flow`
- 治理 / 分红：`get_main_holders`, `get_shareholder_changes`, `get_dividend`
- 板块：`get_sector_list`, `get_sector_members`
- 情绪：`get_limit_up`, `get_limit_down`
- 消息：`get_news`, `get_research`, `get_announcements`

如果某类数据缺失：
- 明确说缺什么
- 不要假装该视角已经完成
- 允许降级输出
- 需要缺口、ADX、EMA50/EMA200、WACC、DCF、同业对比等字段时，只能在数据真的足够时使用
- 当前数据链路未直接返回的指标或事件，不要编造精确数值
- 深度基本面优先使用：
  - `get_deep_fundamental_bundle`
  - 或按需分别调用三张表、公告、新闻、研报、股东、分红接口

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
必须区分：
- 一致性信号
- 矛盾信号
- 时间维度：短线 / 中线 / 长线
- 风险提示：什么条件出现后需要推翻当前判断

若是深度技术面：
- 必须覆盖趋势、关键位、缺口观察、未来 3 个交易日判断、操作建议
- 缺口数据不够时，要直接写“当前工具未直接返回缺口明细”

若是深度基本面：
- 先写数据完整性和分析模式（轻量 / 深度侦探）
- 至少覆盖生意模式、盈利质量、现金流质量、财务健康、估值口径、主要风险
- 有条件时加入杜邦、ROIC/WACC、DCF、同业对比；没条件时明确说明缺口
- 若用户要“完整价投报告”，优先按 `references/value-detective.md` 的骨架和 1→22 清单组织

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

### 执行路径约定（很重要）
- 本 skill 可能来自 Hermes 的 `external_dirs`，不一定物理位于 `~/.hermes/skills/<skill-name>`。
- 当前机器若已在 `~/.hermes/config.yaml` 中配置：
  - `skills.external_dirs: ["/Users/cychi/.agents/skills"]`
  - 则 `stock-master` 的实际根目录应优先按 external dir 解析，例如：`/Users/cychi/.agents/skills/stock-master`
- 不要把 `skill_view` 返回的逻辑路径（如 `stock-master/SKILL.md`、`scripts/analyze_stock.py`）误当作绝对磁盘路径；那只是 skill 内部相对路径。
- 调用脚本前必须先做路径解析与存在性检查：
  1. 先读取 `~/.hermes/config.yaml` 的 `skills.external_dirs`
  2. 按 `<external_dir>/<skill_name>` 查找真实 skill 根目录
  3. 若 external dirs 未命中，再回退检查 `~/.hermes/skills/<skill_name>`
  4. 找到 skill 根目录后，以该目录作为 `workdir`
  5. 若包入口位于 `scripts/` 下，优先使用 `PYTHONPATH=scripts` 或直接在 skill 根目录执行
- 推荐执行方式（优先级从高到低）：
  - 已安装 package + venv：`cd <skill_root> && .venv/bin/python scripts/data_source.py`
  - 已安装 package + venv：`cd <skill_root> && .venv/bin/python scripts/analyze_stock.py 603966 --format text`
  - 显式模块路径：`cd <skill_root> && PYTHONPATH=src .venv/bin/python -m stock_master.cli`
  - 显式模块路径：`cd <skill_root> && PYTHONPATH=src .venv/bin/python -m stock_master.analysis.cli 603966 --format text`
  - 兼容 wrapper 直跑：`cd <skill_root> && python3 scripts/data_source.py`
  - 兼容 wrapper 直跑：`cd <skill_root> && python3 scripts/analyze_stock.py 603966 --format text`
- 在当前机器上，已确认 `stock-master` 的真实目录是：`/Users/cychi/.agents/skills/stock-master`
- 因此当前机器上应优先使用：
  - `cd /Users/cychi/.agents/skills/stock-master && .venv/bin/python scripts/data_source.py`
  - `cd /Users/cychi/.agents/skills/stock-master && .venv/bin/python scripts/analyze_stock.py 603966 --format text`

### 运行前注意
- 当前工程已改为标准 Python src-layout 包，`akshare`、`adata`、`baostock` 都是必需依赖；provider fallback 只负责数据源切换，不再负责缺失依赖降级。
- `src/stock_master/datasource/providers/baostock.py` 保持运行时导入 `baostock`，避免 provider 模块导入阶段过早炸掉；但从工程语义上它仍是必需依赖，若缺少 `baostock`，应修复环境安装。
- 当前 skill 根目录已补充标准 `pyproject.toml`，依赖声明为必需安装的 `akshare`、`adata`、`baostock`。
- 本机 `python3` 来自 Nix 且默认**没有 pip**；不要优先用 `python3 -m pip` 做安装验证。应优先检查 skill 自带 `.venv`，或用 `uv` 管理虚拟环境。
- 当前机器上更可靠的安装/修复顺序：
  1. `cd /Users/cychi/.agents/skills/stock-master`
  2. `uv venv .venv`（若已存在则直接复用，必要时 `uv venv --clear .venv` 重建）
  3. `.venv/bin/pip install -e .`
- wrapper 脚本 `scripts/data_source.py` / `scripts/analyze_stock.py` 已补充两层兜底：
  1. 自动把 `src/` 注入 `sys.path`
  2. 当当前解释器缺少 `akshare` / `adata` / `baostock` 且本地 `.venv/bin/python` 存在时，自动 re-exec 到项目 `.venv`
  因此“最快路径”应优先测试 `python3 scripts/data_source.py` 与 `python3 scripts/analyze_stock.py ...` 是否能直接跑通。
- `DataSource` 默认 venv 路径必须指向项目根目录 `.venv/bin/python`（当前实现位于 `src/stock_master/datasource/service.py`，通过 `Path(__file__).resolve().parents[3] / '.venv' / 'bin' / 'python'` 解析）。如果 diagnostics 与真实安装状态不一致，先检查这个默认路径是否回退错层级。
- 若出现 `ModuleNotFoundError: stock_master`，优先检查是否忘了安装 package，或是否在错误 Python/venv 下运行；若 wrapper 仍失败，先检查 `src/` 注入逻辑是否被改坏。
- 单测全绿基线：`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'` 应得到 `OK (skipped=5)`；这 5 个 skip 来自 `test_datasource_live_smoke.py` 与 `test_provider_live_contract.py`，默认通过 `STOCK_MASTER_RUN_LIVE` 关闭，因为它们依赖网络、第三方数据源与实时市场环境。
- 若出现 `ModuleNotFoundError: baostock`，按环境故障处理，先安装/修复依赖，再运行脚本或测试。
- `src/stock_master/datasource/service.py` 的 `DEFAULT_PYTHON_VENV` 必须指向项目根目录 `.venv/bin/python`；若层级写错，`diagnostics()` 会误报 `akshare/adata/baostock` unavailable，即使脚本本身可运行。
- `scripts/data_source.py` 与 `scripts/analyze_stock.py` 应保留轻量 bootstrap：先把 `src/` 注入 `sys.path`，再检查当前解释器是否已有 `akshare`、`adata`、`baostock`；若没有且本地 `.venv/bin/python` 存在，则自动 re-exec 到该 venv。这样 `python3 scripts/...` 这条最快路径也能跑通，而不必要求用户先手动切解释器。
- `src/stock_master/datasource/providers/baostock.py` 虽然 `baostock` 是必需依赖，但仍应把 `import baostock as bs` 放到 session wrapper 内部，避免模块导入阶段因为外层解释器环境不对而过早崩溃；缺依赖时应在运行/环境层明确失败，而不是在包 import 阶段把整个 skill 入口炸掉。
- 若 diagnostics 显示 `akshare_available=false` / `adata_available=false` / `baostock_available=false`，先优先检查 `DEFAULT_PYTHON_VENV` 和 wrapper 是否把命令切到了项目 `.venv`；修正后再判断是否真的是依赖缺失。
- 工程化重构后，provider 单测里若断言 `backend.run_module_json()` 的模块名，必须同步使用新路径 `stock_master.datasource.providers.*`，不要再保留旧路径 `datasource.providers.*`。
- 手工降级分析模式（已验证可用，但仅限明确降级时使用）：
  1. 只有在本地脚本/包入口已实际验证失败后，才能进入浏览器降级；不能一边声称在走统一数据层，一边直接混入网页抓数结果。
  2. 进入降级前，必须先在最终答复中明确：哪条脚本命令失败、报错摘要是什么、现在切换为“浏览器降级分析”。
  3. 用 `browser_navigate` 打开东方财富千股千评页 `https://data.eastmoney.com/stockcomment/stock/<code>.html`，再用 `browser_console` 抓取页面文本，提取综合评价、主力控盘、趋势研判里的 RSI / 资金 / 市场热度等可见结论。
  4. 用 `browser_navigate` 打开搜狐历史行情页 `https://q.stock.sohu.com/cn/<code>/lshq.shtml`，再用 `browser_console` 直接在页面里解析历史表格 `tr`，拿到最近 60 个交易日 OHLCV。
  5. 在 `browser_console` 里原地计算 MA5/10/20/60、MACD、RSI14、KDJ、BOLL、近 20/60 日高低点、5/20 日均量，避免额外依赖本地 Python 包。
  6. 输出时必须在开头显式标注结果模式：`脚本直出` 或 `浏览器降级分析（脚本失败后）`；缺口明细、ADX 等没有直接数据就不要编造。
- 如果只是临时聊天分析、脚本环境又不完整，可退回 reference + 外部行情/公告数据做手工降级分析，但必须把“脚本失败 → 已切换降级”的链路说清楚。
- 工程化排障时，优先按下面顺序判断真实状态，而不是只看 diagnostics：
  1. `read_file(pyproject.toml)` 确认依赖是否声明为必需。
  2. 先检查 `.venv/bin/python` 和 `.venv/bin/pip` 是否存在可用；若存在，优先用它们。
  3. 运行 `.venv/bin/pip install -e .` 做实际安装验证。
  4. 运行 `.venv/bin/python scripts/data_source.py` 与 `.venv/bin/python scripts/analyze_stock.py <code> --format text` 验证最快路径是否真的跑通。
  5. 再运行 `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'` 看是否还有重构遗留问题。
  6. 若脚本能跑但测试失败，优先检查测试是否仍引用旧模块名（如 `datasource.providers.*`）而非新路径 `stock_master.datasource.providers.*`。
- 重要：`skill_view` 返回的 `scripts/*` 可能只是 skill 附带的引用文件内容，不保证这些脚本已实际落盘到当前机器可执行路径。调用前应先验证脚本是否真实存在于文件系统并且其依赖完整；若脚本路径不存在，就不要假设可以直接 `python3 scripts/analyze_stock.py ...` 运行。
- 若发现 skill 引用了脚本入口，但当前环境没有对应落盘文件或 package（如 `stock_analysis`、`datasource`、`stock_master`），应明确说明 skill 为“文档/引用已存在，但运行时未部署完成”，不要隐式退回到大量网页抓取后还声称在走统一数据层。

- `analyze_stock.py` 会输出：
- `data_snapshot`
- `technical`
- `fundamental`
- `capital_flow`
- `news`
- `prediction`
- `raw_bundle`

若使用 `--format text`，则直接生成适合聊天场景的中文摘要报告。
- 重要：当前 `news` 字段不是纯占位。若 `DataSource.get_bundle()` 已拿到 `news/research`，则 `src/stock_master/analysis/summaries.py:summarize_news()` 应该：
  - 用 `extract_rows()` 真实统计新闻条数与研报条数
  - 提取最新新闻标题/时间
  - 提取最新研报标题/机构/评级
  - 根据 news/research 是否存在，动态输出 `status` 与 `conclusion`
- 重要：`src/stock_master/analysis/render.py` 的文本报告必须显式渲染“消息面”章节；不要只把 `news` 放进 JSON 而漏掉 text 输出，否则会造成“脚本看起来没消息面”的假象。
- 当前文本报告章节顺序应为：基础数据快照 → 技术面 → 资金面 → 基本面 → 消息面 → 综合预判。
- 若用户反馈“消息面没出来”或看起来像手工网页补的，先按下面顺序排查，而不是先假设数据源坏了：
  1. 运行 `.venv/bin/python scripts/analyze_stock.py <code> --pretty` 确认 JSON 里的 `news` / `research` 是否已有真实 `items`
  2. 若 JSON 有数据，再检查 `summarize_news()` 是否仍写死占位文案
  3. 再检查 `render_text()` 是否缺少消息面章节
  4. 补回归测试，至少覆盖：bundle 内有 news/research 时，文本报告中必须出现“消息面”章节和最新新闻/研报字段
- 当用户问“opencli 是否可升级、External CLI Hub 是否有金融/股票相关、能否并入 stock-master”时，执行顺序应固定为：
  1. `opencli --version` 检查本机版本；再用 `npm view @jackwener/opencli version` 对比最新版本。
  2. 用 `opencli xq --help`、`opencli dc --help`、`opencli iwc --help`、`opencli xueqiu --help`、`opencli sinafinance --help`、`opencli yahoo-finance --help` 和 `opencli list` 确认本机已可见/已注册的金融命令族，而不是先凭文档猜测。
  3. 用 `opencli plugin list` 与 `opencli plugin --help` / `opencli install --help` 区分“External CLI / 已注册命令”和“插件”两个概念；若 `plugin list` 为空但 `opencli list` 里已有相关命令，说明这些金融命令当前是内建或已注册 external CLI，不必误判成缺插件。
  4. 读取 `src/stock_master/datasource/providers/opencli.py`、`src/stock_master/datasource/interface.py`、`src/stock_master/datasource/service.py`，以代码事实确认 stock-master 已接入和未接入的能力边界。
  5. 当前已确认：`OpenCliProvider` 已接 `dc/xq` 的 search、quote、history、stock-flow、north-flow、sector-flow、sector-members、top-gainers、top-losers；并且消息相关能力已开始扩展到 `sinafinance` / `xueqiu` / `iwc` / `bloomberg` / `yahoo-finance`。其中应区分两类 capability：
     - `quote` / `snapshot` / `intraday` / `kline` / `money_flow` 这类“单点事实型”数据，命中一个可信源即可，路由策略应为 first-success。
     - `news` / `research` / `announcements` 这类“信息聚合型”数据，天然需要多源收集与去重，路由策略应为 aggregate/merge。
  6. `stock_master.datasource` 的能力路由应优先做成**接口契约驱动**，不要把策略散落在 `service.py` 的 map 里：
     - 在 `src/stock_master/datasource/interface.py` 为 capability 定义 `CapabilitySpec`
     - 用 `@capability(...)` 注解每个 `get_*` 方法的调度语义
     - `get_quote/get_snapshot/get_intraday/get_kline/get_money_flow/get_north_flow/get_sector_money_flow/get_financial/get_report/get_income_statement/get_balance_sheet/get_cash_flow/get_main_holders/get_shareholder_changes/get_dividend/get_sector_list/get_sector_members/get_limit_up/get_limit_down` 维持 `first_success`
     - `get_news/get_research/get_announcements` 标为 `aggregate`，并设置 `merge_keys=('items','rows')`
     - 在 `runtime.py` 由 `ProviderRouter.dispatch(..., spec=...)` 按 spec 执行 `first_success` 或 `aggregate`
     - `aggregate` 必须遍历所有可用 provider、收集成功 payload、返回 `source='merged'`、`sources=[...]`、`fallback_path=[...]`
     - `service.py` 只负责读取 spec 并转发，不再维护平行的 `CAPABILITY_STRATEGIES`
     - 内部可以把 merge 语义命名为 aggregate，但**对外 contract 要保持兼容**：返回 payload 的 `source` 仍用 `merged`，旧测试里 `strategy='merge'` 的调用也应继续可用
     - 对 `quote/snapshot` 这类 single-hit capability，除了 provider success 之外，还应加 `sufficient_fields` 约束；至少要求命中一组真实价格字段（如 `price/close/current/current_price/trade/last_price/latestPrice/regularMarketPrice`）后才允许 short-circuit，避免第一个 provider 只返回半空壳 payload 就过早截停后续更优来源
     - runtime 聚合层目前的去重已经退化为基于整条 record 的稳定 identity（JSON dump / repr），因为早期设想的 `url/link/title/date/symbol` 组合键在多站点字段差异下容易漏判或误杀；后续若要增强，应在统一 item schema 之后再做按字段语义去重
  7. OpenCLI provider 扩展时，优先按“能力类型”设计 adapter 分工，而不是按站点堆 if/else：
     - 搜索：`dc search` → `xq search` → `xueqiu search`，自然语言问题再兜底 `iwc query --question ...`
     - 报价：`xq quote` → `dc quote` → `xueqiu stock`；A 股再补 `sinafinance stock`，非 A 股再补 `yahoo-finance quote`
     - K 线：`dc history` → `xq history` → `xueqiu kline`
     - 资讯：`sinafinance news`、`sinafinance rolling-news`、`xueqiu comments <symbol>`、`bloomberg markets`
     - 研究/事件：`xueqiu comments` + `xueqiu earnings-date`
     - 公告/公司动态：若没有正式公告 adapter，不要伪装成官方公告；可返回 event/company-update 型真实条目，并在 item 上标 `kind`
     - provider 内部要做轻量标准化，尽量补齐 `title/date/url/source_channel/kind`，同时保留原始字段
  8. 因而给用户的更新建议应优先级明确：
     - 第一优先级：升级 opencli 到最新小版本并验证 `xq/dc/iwc/ths` 兼容性
     - 第二优先级：把 `sinafinance` / `xueqiu` 的 news、comments、hot-stock、earnings-date 等能力映射进 `OpenCliProvider`
     - 第三优先级：为 `iwc query` 增加筛股/条件选股入口，而不是继续把它当成独立工具散用
  7. 汇报时要明确区分：
     - “本机已可见/已注册的命令”
     - “stock-master 已实际接入的 provider 能力”
     - “适合下一步并入但尚未接线的 opencli 金融数据源”

内部实现约束：
- `scripts/analyze_stock.py` 只作为 CLI 入口存在，不应继续承载可复用 API
- `scripts/data_source.py` 只作为诊断入口存在，不应继续承载可复用 API
- `scripts/` 目录不再保留镜像实现树，只保留 skill-facing wrappers 与最小 bootstrap
- 可复用逻辑统一沉到 `src/stock_master/*`

## 风格约束
- 先证据，后结论
- 不把预测说成事实
- 数据不够时明确降级
- 对短线和长线的判断不要混写
- 当基本面数据缺失时，不要强行做深度价值判断
- 明确区分“工具直接返回”与“基于方法论推断”
- 尽量用条件化语言写预判：如果……则……；跌破 / 站回哪些位置会失效
- 避免堆术语，优先给少量高价值结论
