# Stock Master capability-aware + market/query-aware routing 改造计划

> 阶段 1 输出：基于现有 `datasource/interface/runtime/service/providers/opencli/common/symbols/tests/README/SKILL` 的代码与文档审视，给后续实现提供可执行的改造蓝图，而不是仅做现状总结。

## 0. 实施结果回填（2026-04-10）

本轮已完成并验证的收敛项：

1. `DataSource` 增加 `_providers_for(capability, first_arg)`，主路由每次 dispatch 都会实际调用 `preferred_provider_groups()` + `reorder_provider_sequence()`，不再只是“规则存在但未显式固化在 service contract 中”。
2. `OpenCliProvider._ordered_providers()` 不再手写另一套顺序，而是复用 `preferred_provider_groups()` 的 family contract，只在 composite 兼容层过滤出 opencli family。
3. quote / snapshot 继续走 `first_success + sufficient_fields`；测试已补上 `snapshot` 共享 quote short-circuit 的断言。
4. `get_news/get_research/get_announcements` 继续走 aggregate；补上 research 聚合顺序与 merged contract 断言。
5. opencli family 测试已对齐为：
   - 自然语言 search 优先 `opencli-iwc`
   - 全球 quote 优先 `opencli-yahoo-finance`
   - global news 优先 `bloomberg/xueqiu` 栈
6. README 已同步 capability-aware、market-aware、query-aware contract，避免文档仍停留在旧顺序。
7. 当前单元测试复核已通过：`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'` => `OK (skipped=5)`。

## 1. 目标与范围

### 1.1 改造目标
把当前 datasource 层从“**接口层声明能力** + **service 层重排 provider 顺序** + **runtime 层按 spec 执行 first_success / aggregate**”的基本形态，进一步收敛成一套更稳定、可验证、可扩展的路由体系：

1. **capability-aware routing**
   - 每个 `get_*` capability 在 `interface.py` 上声明自己的调度语义。
   - `runtime.py` 只负责执行 `first_success` / `aggregate` 与 sufficiency、dedupe、sort。
   - `service.py` 不再内嵌平行策略表，只透传 capability spec 与 provider 顺序。

2. **market-aware routing**
   - A 股、港股/美股、自然语言问句三类请求在 provider 排序上有显式差异。
   - `common/symbols.py` 负责把 symbol/query 归类成 market/query hint，并给出 provider group 偏好。

3. **query-aware routing**
   - `get_search()` 不再把代码检索、自然语言筛股、资讯问句混为一谈。
   - 纯 symbol / ticker 查询优先结构化搜索源；自然语言问题优先 `opencli-iwc` 或至少在排序上前置。

4. **opencli family 职责清晰化**
   - 不是“opencli 一个 provider 包打天下”，而是把 `dc/xq/xueqiu/sinafinance/bloomberg/yahoo-finance/iwc` 视为同一家族下的不同子 provider。
   - composite `OpenCliProvider` 仅保留兼容层职责，不承载真实跨能力策略中心。

5. **测试与文档同步**
   - 将 routing contract、family 分工、live smoke 预期、README/SKILL 使用说明同步更新，避免代码与 skill 文档漂移。

### 1.2 本阶段涉及文件
- `src/stock_master/datasource/interface.py`
- `src/stock_master/datasource/runtime.py`
- `src/stock_master/datasource/service.py`
- `src/stock_master/datasource/providers/__init__.py`
- `src/stock_master/datasource/providers/opencli.py`
- `src/stock_master/common/symbols.py`
- `tests/test_datasource_interface.py`
- `tests/test_datasource_runtime.py`
- `tests/test_datasource_service.py`
- `tests/test_provider_opencli.py`
- `tests/test_datasource_live_smoke.py`
- `README.md`
- `SKILL.md`

---

## 2. 审视结论：当前代码已具备的基础与未完成的地方

## 2.1 已具备的基础能力

### A. capability spec 已进入接口层
`src/stock_master/datasource/interface.py` 已定义：
- `CapabilitySpec`
- `@capability(...)`
- `get_capability_spec(capability_name)`

并且已把：
- `get_news/get_research/get_announcements` 标成 `strategy='aggregate'`
- `get_quote/get_snapshot` 增加 `sufficient_fields`

这意味着“能力驱动路由”的接口契约基础已经存在。

### B. runtime 已支持 aggregate / first_success
`src/stock_master/datasource/runtime.py` 已支持：
- `dispatch(..., spec=...)`
- `_dispatch_first_success()`
- `_dispatch_aggregate()`
- `aggregate_payloads()`
- 记录 `fallback_path`
- 返回 `source='merged'` 与 `sources=[...]`
- 基于 `record_identity` 去重
- `date_desc` 排序
- `sufficient_fields` 判定

说明 runtime 核心执行框架已经到位，不需要推倒重写。

### C. service 已开始按 query/symbol 选择 preferred groups
`src/stock_master/datasource/service.py` 已依赖 `common.symbols.preferred_provider_groups()`，再调用 `reorder_provider_sequence()`。

`src/stock_master/common/symbols.py` 已具备：
- `preferred_provider_groups(capability, first_arg)`
- A 股/全球市场/自然语言/资讯/基本面等偏好栈划分

这表示 market/query-aware 排序逻辑也已初步接线。

### D. opencli family 已拆成多个 provider 类
`src/stock_master/datasource/providers/opencli.py` 已拆出：
- `OpenCliDcProvider`
- `OpenCliXqProvider`
- `OpenCliXueqiuProvider`
- `OpenCliSinaFinanceProvider`
- `OpenCliBloombergProvider`
- `OpenCliYahooFinanceProvider`
- `OpenCliIwcProvider`
- 兼容层 `OpenCliProvider`

这为“family 分工明确化”提供了良好基础。

## 2.2 仍需收敛和补强的问题

### A. service 当前实现还没有真正按 capability/query 重排 provider
虽然 `service.py` 引入了 `preferred_provider_groups`、`reorder_provider_sequence`，但当前 `DataSource.__init__()` 里 `self.providers = list(providers or order_providers(...))`，`_dispatch()` 直接使用固定 `self.router`，没有在每次 capability 调度时依据 `capability + first_arg` 动态重排。

**影响：**
- `common/symbols.py` 里的 market/query-aware routing 规则目前没有完整落地。
- 路由策略“写在 symbols.py 中，但 dispatch 时未实际生效”。

### B. composite OpenCliProvider 与 family provider 存在职责重叠
当前既有：
- family provider 在 datasource provider map 中独立参与路由
- 也有 legacy `OpenCliProvider` 在内部自己做 `_ordered_providers()` + `_first_supported()`

**风险：**
- 同一 capability 的路由逻辑在两个层级重复：service/runtime 层一套，composite provider 内部又一套。
- 后续如果 family 顺序调整，容易出现“direct import 的 OpenCliProvider 行为”和实际 DataSource 行为不一致。

### C. search 的 query-aware 仍偏粗糙
`_looks_like_question()` 目前主要依赖：
- 长度
- 是否包含问句关键词
- 中文字符数量

**风险：**
- “新能源龙头”“高股息银行股”这类自然语言筛股/主题词，未必带问号，但应该偏向 `iwc`。
- 港美股 ticker、指数、板块代码、纯数字股票代码，需要更精确的 query 类型识别。

### D. aggregate 的 contract 已有，但 provider item schema 仍需统一
目前 opencli family 虽然开始统一：
- `title`
- `date`
- `url`
- `source_channel`
- `kind`

但不同子源返回 `items/rows/单对象` 的形态仍比较分散，聚合层虽然能 merge，但“结果可消费性”仍不够稳定。

### E. 文档已提出原则，但 README 仍未完整说明 routing contract
`SKILL.md` 中已有更先进的设计约束，但 `README.md` 仍偏安装/测试说明，尚未把：
- capability strategy
- market-aware priority
- opencli family capability map
- live smoke 如何解读 `merged/sources/fallback_path`
说明清楚。

---

## 3. 目标架构：后续实现应收敛成什么样

## 3.1 分层职责

### interface.py
负责定义“某个 capability 的调度契约”：
- strategy: `first_success` / `aggregate`
- merge_keys
- dedupe_by
- sort_by
- sufficient_fields

### common/symbols.py
负责生成“该 capability + 输入参数”的 routing hints：
- 请求属于 A 股 / 全球 / 自然语言 / 主题筛选 / 资讯聚合
- 对应的 preferred provider groups

### service.py
负责：
1. 读取 capability spec
2. 基于 `preferred_provider_groups(capability, first_arg)` 生成本次调用的 provider 顺序
3. 为本次调用创建临时 router 或临时 provider sequence
4. 调 runtime dispatch
5. 处理 cache / placeholder / facade 兼容

### runtime.py
只负责执行，不负责编排 provider 业务排序：
- first_success
- aggregate
- timeout
- sufficiency
- dedupe
- sort
- tagging / merged payload

### providers/opencli.py
负责 opencli family 子 provider 的真实适配：
- family provider 做单站点适配和轻量标准化
- legacy `OpenCliProvider` 只保留兼容，不再成为主路由中心

---

## 4. 实施计划

## Task 1：让 service 真正按 capability + first_arg 动态重排 provider

### 目标
把 `common/symbols.py` 中已经存在的 market/query-aware routing 规则，真正落到每次调用中。

### 改动点
- 修改：`src/stock_master/datasource/service.py`
- 复核：`src/stock_master/datasource/providers/__init__.py`
- 复核：`src/stock_master/common/symbols.py`
- 测试：`tests/test_datasource_service.py`

### 实施要求
1. 在 `DataSource` 中新增一个内部方法，例如：
   - `_providers_for(capability, *args)`
   - 从 `self.providers` 或 `self.provider_map` 生成本次调用的 provider 序列
2. 调用：
   - `preferred_provider_groups(capability, first_arg)`
   - `reorder_provider_sequence(...)`
3. `first_arg` 约定：
   - symbol 型 capability 用 normalized symbol
   - search 用原 query
   - 无参能力传 `None`
4. `_dispatch()` 不再固定调用一个永久 `self.router`，而是按本次 provider 序列构造 router，或给 router 传入 providers。
5. 保持对 `providers=` 注入测试桩的兼容：
   - 当外部传入自定义 providers 时，也要允许对其按 name 重排。
6. `fallback_path` 必须继续只记录真实尝试过的 provider。

### 完成判定
- A 股 quote 优先本地结构化源，再到 opencli A 股源。
- 全球 quote 优先 yahoo / xq / xueqiu 一类全球栈。
- 自然语言 search 时 `opencli-iwc` 顺序前置或至少进入首组。
- `tests/test_datasource_service.py` 增加顺序断言。

---

## Task 2：明确并固化 capability → provider family 的职责映射

### 目标
把“opencli family 分工”从隐式实现变成显式 contract，减少后续改动时的分层混乱。

### 改动点
- 修改：`src/stock_master/common/symbols.py`
- 修改：`src/stock_master/datasource/providers/opencli.py`
- 测试：`tests/test_provider_opencli.py`
- 文档：`README.md`、`SKILL.md`

### 目标分工

| 能力 | 主 family | 次 family | 说明 |
|---|---|---|---|
| `get_search` 代码/标的检索 | `opencli-dc`, `opencli-xq`, `opencli-xueqiu` | `akshare/adata/baostock` | 结构化搜索优先 |
| `get_search` 自然语言/筛股 | `opencli-iwc` | `opencli-dc/xq/xueqiu` | query-aware |
| `get_quote/get_snapshot/get_intraday` A股 | `akshare/adata/baostock` | `opencli-xq/dc/xueqiu/sinafinance` | 单点事实型 |
| `get_quote/get_snapshot/get_intraday` 全球 | `opencli-yahoo-finance`, `opencli-xq`, `opencli-xueqiu` | `opencli-bloomberg`, `opencli-dc` | 全球行情优先 |
| `get_kline` A股 | `akshare/adata/baostock` | `opencli-dc/xq/xueqiu` | 历史行情 |
| `get_money_flow/get_north_flow/get_sector*` | `akshare/adata/baostock` | `opencli-dc` | 结构化板块/资金数据 |
| `get_news` A股 | `opencli-sinafinance`, `opencli-xueqiu` | `opencli-bloomberg`, `opencli-iwc` | 聚合型 |
| `get_news` 全球 | `opencli-bloomberg`, `opencli-yahoo-finance`, `opencli-xueqiu` | `opencli-sinafinance` | 聚合型 |
| `get_research/get_announcements` | `akshare/adata/baostock` + `opencli-xueqiu` | `opencli-iwc` | 正式财务/公告优先，事件线索补充 |

### 实施要求
1. 以上映射先固化到 `preferred_provider_groups()` 的返回规则中。
2. `OpenCliProvider` 的 `_ordered_providers()` 仅作为兼容 direct tests 的内部排序，不应与 `preferred_provider_groups()` 背离。
3. 若发现两处顺序定义冲突，以 datasource 主路由为准，并收敛 composite provider 的顺序。

### 完成判定
- family 分工在代码、测试、README/SKILL 中一致。
- 不再出现“service 认为 A 股 quote 优先一套，OpenCliProvider 自己优先另一套”的分裂。

---

## Task 3：加强 query 分类规则，避免 iwc 与结构化搜索误用

### 目标
让 `get_search()` 的 query-aware routing 更可控，避免仅凭“长度大于 10”来前置 `iwc`。

### 改动点
- 修改：`src/stock_master/common/symbols.py`
- 可选修改：`src/stock_master/datasource/providers/opencli.py`
- 测试：`tests/test_provider_opencli.py`、`tests/test_datasource_service.py`

### 实施要求
1. 新增统一 query 分类函数，例如：
   - `classify_query_input(query) -> {'kind': 'symbol'|'ticker'|'numeric_code'|'board_code'|'theme'|'natural_language'}`
2. 规则至少区分：
   - A 股代码：`603966` / `SH603966`
   - 美股 ticker：`AAPL` / `MSFT`
   - 板块代码：`BK0428`
   - 自然语言问句：带问句特征
   - 自然语言主题/筛股词：如“高股息银行股”“AI 算力龙头”
3. `preferred_provider_groups()` 和 `OpenCliIwcProvider.get_search()` 共用这套分类，不要各自猜测。
4. 设计上允许：
   - `theme` / `natural_language` => `iwc` 前置
   - `symbol/ticker/numeric_code/board_code` => 结构化搜索前置

### 完成判定
- 针对“603966”“AAPL”“BK0428”“高股息银行股”“现在市场情绪怎么样？”分别有明确测试断言。

---

## Task 4：收敛 aggregate 结果 schema，让聚合结果稳定可消费

### 目标
让 `news/research/announcements` 的 merged payload 不只是“能拼起来”，而是“下游分析/报告稳定可用”。

### 改动点
- 修改：`src/stock_master/datasource/providers/opencli.py`
- 复核：`src/stock_master/datasource/runtime.py`
- 测试：`tests/test_provider_opencli.py`、`tests/test_datasource_runtime.py`、`tests/test_datasource_service.py`

### 实施要求
1. 对所有 opencli 资讯类条目，尽量补齐：
   - `title`
   - `date`
   - `url`
   - `source_channel`
   - `kind`
2. provider 级别负责轻量标准化；runtime 不做字段猜测，只做 merge/dedupe/sort。
3. `aggregate_payloads()` 继续兼容：
   - `items`
   - `rows`
4. 若 provider 返回单 dict，适配层尽量先 wrap 成 `items=[...]`。
5. 去重继续维持 `record_identity`，不要在本次改造中引入更激进的字段语义去重。
6. 对 `research/announcements` 中的“事件线索型”条目显式标 `kind`，避免被误解为正式公告全文。

### 完成判定
- merged news/research/announcements 至少在 tests 中都能稳定读取 `items`。
- analysis/report 层无需再为不同 provider 特判字段名。

---

## Task 5：弱化 legacy OpenCliProvider 的策略中心角色

### 目标
保留兼容，但避免双重路由中心。

### 改动点
- 修改：`src/stock_master/datasource/providers/opencli.py`
- 测试：`tests/test_provider_opencli.py`
- 测试：`tests/test_datasource_interface.py`

### 实施要求
1. `build_provider_map()` 仍保留 `opencli` 兼容入口，但在主 priority 中继续优先 family provider。
2. direct import `OpenCliProvider` 的测试继续保留，确保 wrapper 不坏。
3. 文档中明确：
   - 运行时主路由单位是 family provider
   - `OpenCliProvider` 是 backwards-compatible composite adapter
4. 若后续实现允许，可把 `OpenCliProvider` 简化为：
   - 对 family provider 的 thin composite
   - 不再扩展独立业务分叉

### 完成判定
- `tests/test_provider_opencli.py` 仍通过。
- `tests/test_datasource_interface.py` 仍验证 `opencli` 与 family provider 同时存在，但主流程不依赖 legacy provider。

---

## Task 6：补齐测试矩阵，覆盖“能力策略 × 市场类型 × 查询类型 × provider family”

## 6.1 现有测试基础
已存在：
- `test_datasource_runtime.py`：dispatch / merge / fallback / dedupe / timeout
- `test_datasource_service.py`：cache / placeholder / bundle / merged service 行为
- `test_datasource_interface.py`：provider map / ordering
- `test_provider_opencli.py`：opencli family 路径与标准化
- `test_datasource_live_smoke.py`：live 输出 contract

## 6.2 需要新增或补强的矩阵

| 维度 | 场景 | 目标测试文件 | 断言重点 |
|---|---|---|---|
| 能力策略 | `quote` first_success | `test_datasource_runtime.py` | 首个满足 sufficient_fields 的 provider 才 short-circuit |
| 能力策略 | `news/research/announcements` aggregate | `test_datasource_runtime.py` | merged/sources/fallback_path 正确 |
| sufficiency | 首个 provider 仅返回壳 payload | `test_datasource_runtime.py` | 不应过早停止，需继续 fallback |
| 市场类型 | A股 quote | `test_datasource_service.py` | 顺序偏向 akshare/adata/baostock，再 opencli A 股源 |
| 市场类型 | 全球 quote | `test_datasource_service.py` | 顺序偏向 yahoo/xq/xueqiu |
| 查询类型 | 纯代码 search | `test_datasource_service.py` | 结构化搜索前置 |
| 查询类型 | 自然语言问句 search | `test_datasource_service.py` | `opencli-iwc` 前置或命中首组 |
| 查询类型 | 主题/筛股词 search | `test_datasource_service.py` | 不再被误判为纯结构化 symbol 搜索 |
| family 适配 | `dc/xq/xueqiu/sinafinance/yahoo-finance/iwc` | `test_provider_opencli.py` | 命令调用链正确 |
| 资讯标准化 | news/research/announcements item schema | `test_provider_opencli.py` | `title/date/url/source_channel/kind` 存在 |
| 文档契约 | diagnostics 暴露 opencli family | `test_datasource_service.py` | `diagnostics()['opencli_family']` 完整 |
| live smoke | merged payload contract | `test_datasource_live_smoke.py` | `merged` / `sources` / `fallback_path` 可解释 |

## 6.3 测试实施顺序
1. 先补 runtime/service 单元测试，锁定主路由 contract。
2. 再补 opencli provider family 单测，锁定 adapter 行为。
3. 最后根据新 contract 调整 live smoke 容忍条件。

---

## Task 7：更新 README / SKILL / 计划文档，形成一致对外说明

### README.md 需要新增的内容
1. **Datasource routing model**
   - first_success vs aggregate
   - `source / sources / fallback_path` 含义
2. **Market-aware examples**
   - A 股 quote
   - 美股 quote
   - 自然语言 search
3. **OpenCLI family capability map**
   - 各子 provider 负责什么能力
4. **Testing guidance**
   - unit tests
   - live smoke 如何开启
   - 如何理解 placeholder/empty/merged

### SKILL.md 需要同步的内容
1. 把现有原则与真实代码状态对齐：
   - capability spec 已落在 `interface.py`
   - runtime 已支持 aggregate
   - 下一步重点是 service 动态重排真正生效
2. 更新 opencli family 分工与 query-aware 规则。
3. 增加“当用户问为什么某能力走某 provider”时的排查顺序：
   - 看 capability spec
   - 看 query/market classification
   - 看 preferred provider groups
   - 看 fallback_path / sources

### 文档完成判定
- README 读者无需阅读源码，也能理解为何 `quote` 与 `news` 路由不同。
- SKILL 中的实现约束与现状代码不再矛盾。

---

## 5. 建议的实施顺序

### 第一步：锁定主路由 contract
先做 `service.py` 动态 provider 重排落地 + 新增测试。

### 第二步：统一 query 分类
把 symbols/query 分类函数收敛，避免 service 与 opencli provider 各自判断。

### 第三步：收敛 opencli family 行为
调整 `opencli.py`，确保 family provider 与 composite provider 行为一致。

### 第四步：补 schema/merge 稳定性
完善资讯类 item 标准化与聚合结果 contract。

### 第五步：补文档与 live smoke
在单元测试稳定后再更新 README/SKILL/live smoke 断言，避免文档先于代码漂移。

---

## 6. 风险与注意事项

1. **不要在 service 和 OpenCliProvider 同时维护两套主排序逻辑。**
2. **不要把 query-aware 仅实现为 provider 内部 fallback。** 主路由应由 service + symbols 决定。
3. **不要让 aggregate 变成“所有 dict 生拼硬凑”。** 资讯类 provider 应先尽量标准化。
4. **不要把事件线索伪装成正式公告。** 用 `kind` 明确标识。
5. **不要破坏 direct import 的兼容路径。** `OpenCliProvider` 和 `opencli` provider key 仍需保留。
6. **不要过早复杂化 dedupe。** 当前 `record_identity` 足够支撑本轮改造。

---

## 7. 阶段 1 输出结论

后续实现的主线应是：
- **不是再发明一套 routing 框架，** 因为 capability spec、aggregate runtime、opencli family 拆分都已经存在；
- **而是把尚未彻底打通的“service 动态重排 + query 分类收敛 + family 职责一致化 + 文档/测试对齐”补完整。**

换句话说，下一阶段不是从 0 到 1，而是从“设计已大半落地但关键链路未完全闭环”推进到“代码、测试、文档、skill 约束一致”。
