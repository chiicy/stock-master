# Stock Master Provider Routing + OpenCLI 扩展 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. 先做 provider 路由策略重构，再做 OpenCLI 扩展接线，最后做 review/test。

**Goal:** 把 `stock-master` 的 provider 路由从“所有能力统一 first-success fallback”升级成“按能力选择 short-circuit 或 multi-source merge”，并把 opencli 的 `sinafinance / xueqiu / iwc / bloomberg / yahoo-finance` 实际接入到 `stock-master` 数据层。

**Architecture:** 在 `datasource/runtime.py` 引入 capability-aware 路由策略：`first_success` 适用于价格、K 线、资金流等单一快照型能力；`merge` 适用于新闻、研报/事件、公告/情报等信息聚合型能力。`OpenCliProvider` 继续作为统一 opencli 适配层，但对不同能力按站点职责分流：`dc/xq/xueqiu/sinafinance/yahoo-finance` 负责行情/搜索/历史，`sinafinance/xueqiu/bloomberg` 负责资讯，`iwc` 负责自然语言问财检索/筛选入口。

**Tech Stack:** Python 3.11+, src-layout package, unittest/pytest, opencli adapters (`dc`, `xq`, `xueqiu`, `sinafinance`, `iwc`, `bloomberg`, `yahoo-finance`).

---

## Findings / 现状结论

1. 当前 `ProviderRouter.dispatch()` 固定是串行 first-success；一旦某 provider 返回有效 payload，后续 provider 永远不会执行。
2. 这对 `get_quote/get_kline/get_money_flow` 合适，但对 `get_news/get_research/get_announcements` 不合适，因为这些能力天然需要多源补充。
3. 当前 `OpenCliProvider` 只接了：
   - `dc`: `search/quote/history/stock-flow/north-flow/sector-flow/sector-members/top-gainers/top-losers`
   - `xq`: `search/quote/history`
4. 当前尚未接线：
   - `sinafinance`: `news/rolling-news/stock/stock-rank`
   - `xueqiu`: `stock/kline/search/comments/hot-stock/earnings-date`
   - `iwc`: `query`
   - `bloomberg`: `markets`/其他 RSS feed，`news`
   - `yahoo-finance`: `quote`
5. 因而当前 skill 的 provider 层对“实时价格”还行，但对“信息面/事件面/消息面”明显过窄。

---

### Task 1: 引入 capability-aware 路由策略

**Objective:** 让 runtime 支持按能力选择 `first_success` 或 `merge`。

**Files:**
- Modify: `src/stock_master/datasource/runtime.py`
- Modify: `src/stock_master/datasource/service.py`
- Test: `tests/test_datasource_runtime.py`
- Test: `tests/test_datasource_service.py`

**Implementation notes:**
1. 在 `runtime.py` 新增公开的策略常量或字面量类型，例如：`first_success`, `merge`。
2. 新增 `dispatch_merge()` 或让 `dispatch()` 接受 `strategy=` 参数。
3. `merge` 模式下：
   - 遍历所有可用 provider，不在首个成功后停止。
   - 收集所有成功 payload。
   - 结果中保留：`items`、`sources`、`source='merged'`、`fallback_path`。
   - 允许没有 `items` 的 dict payload 也参与 merge，但最终需要有 meaningful 内容。
4. 增加基础去重逻辑：当前实际实现按 record-level stable identity（JSON dump / repr）去重，避免相同新闻重复；不再依赖固定 `url/link/title/name/date/symbol` 组合键。
5. `first_success` 维持现有行为，不破坏 quote/kline/flow。
6. `service.py` 中增加 capability->strategy 映射：
   - `get_quote/get_snapshot/get_intraday/get_kline/get_money_flow/get_north_flow/get_sector_money_flow/get_financial/get_report/get_income_statement/get_balance_sheet/get_cash_flow/get_main_holders/get_shareholder_changes/get_dividend/get_sector_list/get_sector_members/get_limit_up/get_limit_down` → `first_success`
   - `get_news/get_research/get_announcements` → `merge`

**Verification:**
- 新增/修改单测覆盖：
  - `first_success` 在首个成功后停止。
  - `merge` 会调用多个 provider 并合并结果。
  - `merge` 在部分 provider 失败时仍返回成功 provider 的聚合结果。
  - `merge` 去重逻辑生效。

---

### Task 2: 扩展 OpenCliProvider 的行情/搜索路由

**Objective:** 把 `sinafinance / xueqiu / iwc / yahoo-finance` 真正接入搜索、报价、历史能力链路。

**Files:**
- Modify: `src/stock_master/datasource/providers/opencli.py`
- Test: `tests/test_provider_opencli.py`

**Implementation notes:**
1. `get_search(query)`:
   - 保留 `dc search`、`xq search`。
   - 增加 `xueqiu search <query>`。
   - 对明显自然语言问句增加 `iwc query --question <query>` 路径（至少在 `dc/xq/xueqiu` 全失败时兜底；更好是 query 非纯代码/纯 ticker 时优先尝试 iwc）。
2. `get_quote(symbol)`:
   - 保留 `xq quote`、`dc quote`。
   - 增加 `xueqiu stock <symbol>`。
   - 增加 `sinafinance stock <symbol>`。
   - 对美股/非 A 股 ticker 增加 `yahoo-finance quote <symbol>` 兜底。
3. `get_kline(symbol, days)`:
   - 保留 `dc history`、`xq history`。
   - 增加 `xueqiu kline <symbol>`。
   - 若 `yahoo-finance` 无 history 子命令，不要伪接入。
4. 所有新增调用都要保持 `_normalize_payload()` 兼容，必要时 wrap/reshape 成 `items`。

**Verification:**
- 新增单测覆盖：
  - search 从 `dc -> xq -> xueqiu -> iwc` 的 fallback / 分流。
  - quote 会尝试多条 opencli 路径，并支持 yahoo-finance 兜底。
  - kline 增加 xueqiu 路径。

---

### Task 3: 扩展 OpenCliProvider 的资讯/事件聚合能力

**Objective:** 让 `get_news/get_research/get_announcements` 不再只是 placeholder，而是能从多 opencli 源拿到真实信息。

**Files:**
- Modify: `src/stock_master/datasource/providers/opencli.py`
- Modify: `src/stock_master/datasource/interface.py`（如需补充 provider 方法注释即可）
- Modify: `src/stock_master/datasource/service.py`
- Test: `tests/test_provider_opencli.py`
- Test: `tests/test_datasource_service.py`

**Implementation notes:**
1. `get_news(symbol)`:
   - 接 `sinafinance news`
   - 接 `sinafinance rolling-news`
   - 接 `xueqiu comments <symbol>`
   - 接 `bloomberg markets`（至少作为宏观/市场资讯补充）
   - 可按 provider 内做轻度标准化：统一 title/date/url/source_channel 字段，同时保留原始字段。
2. `get_research(symbol)`:
   - 没有严格“研报”命令时，可把 `xueqiu earnings-date <symbol>` 作为事件/研究线索型 payload；必要时标记 `category='event'`。
   - `xueqiu comments` 中若含作者/讨论热度，也可作为 `opinion/commentary` 条目纳入 research-like 聚合，但需要字段上标注类型。
3. `get_announcements(symbol)`:
   - opencli 当前没有标准公告 adapter 时，不要伪装成正式公告；可以返回事件/公司动态线索型 items（如 earnings-date），并在 item 级字段上注明 `kind='event'` / `kind='company_update'`。
   - 真正聚合策略由 runtime `merge` 完成；provider 只负责尽量产出真实条目。
4. 统一 item 结构建议至少包含：`title`, `date`, `url`, `source_channel`, `kind`。

**Verification:**
- 新增单测覆盖：
  - `get_news()` 能整合新浪/雪球/彭博结果。
  - `get_research()` / `get_announcements()` 能返回真实 items，而非仅 False。
  - item 标准化字段存在。

---

### Task 4: review / test / diagnostics

**Objective:** 在真实仓库里完成实现后做代码审查与回归验证。

**Files:**
- Run only

**Steps:**
1. 运行 `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test*.py'`
2. 运行 `.venv/bin/python scripts/data_source.py`
3. 运行 `.venv/bin/python scripts/analyze_stock.py 603966 --pretty`
4. 检查输出里：
   - `quote` 仍是单源 short-circuit 结果
   - `news/research/announcements` 具备多源 merge 痕迹（`source='merged'` 或 `sources=[...]`）
   - `fallback_path` 只记录真实尝试 provider
5. 做最终 code review：
   - 路由策略是否清晰
   - `OpenCliProvider` 是否没有把站点特例散落到 service 层
   - 测试是否覆盖新增策略与接线

---

## Execution notes for subagents

- 先做 Task 1（runtime/service），因为它定义后续接口语义。
- 再做 Task 2 + Task 3（opencli provider/tests），可以同一实现子代理完成，但 review 要分开检查“规格符合”和“代码质量”。
- 最后做 Task 4 的测试/诊断与最终 review。
- 若实现中发现 `bloomberg` / `yahoo-finance` 某些命令在本机 opencli 不存在，必须按实际 `opencli --help` 结果降级，不得虚构命令。
