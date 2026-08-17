# 2026-08-17 AI 分析预置策略 + 策略分类 + 成分股数据

## 需求

AI 分析模块增加策略分类与预置策略：早盘竞价、午盘、尾盘、蓝筹白马等，先设计 10 种；蓝筹白马先用固定股票池，后续演进为 AI 全市场筛选（需同步数据，可从 BaoStock 获取）。

## 决策记录（用户确认）

- 预置策略**默认停用**（避免 10 策略 × 每日多时段立即消耗大量 LLM token），用户在管理页自行启用
- 预置策略**允许编辑/删除**，`is_preset` 仅作展示标记；删除走软删，不重新植入
- 蓝筹股票池：核心资产 30 只（沪深300核心）+ 红利 20 只（银行/公用事业/能源/运营商）固定池起步

## 实现

### 策略分类（迁移 0016）

- `business_ai_strategy` 加 `category VARCHAR(30) DEFAULT 'general'`（pre_market_auction/noon/tail/blue_chip/general）+ `is_preset BOOLEAN DEFAULT FALSE`
- schema 常量 `STRATEGY_CATEGORIES/STRATEGY_CATEGORY_NAMES`；列表接口 `category` 过滤；create/update 校验落库
- 前端：分类下拉筛选 + 表格分类列（NTag 着色）+ 预置标记 + 抽屉分类选择；i18n `page.aiStrategy.category*`

### 10 条预置策略种子（id 段 2942406616009101+，按 name 幂等）

竞价高开抢筹 / 竞价超跌低吸（pre_market）；午盘强势回踩低吸 / 午盘补涨轮动（noon）；尾盘资金抢筹 / 尾盘趋势确认（tail）；核心资产价值投资（tail+post_close，30只固定池）/ 高股息红利防御（post_close，20只固定池）（blue_chip）；涨停题材龙头打板（morning+noon+tail）/ 大盘共振波段（morning+tail）（general）。每条含完整 prompt_template（选股逻辑+买卖纪律+风控）。

### 成分股数据链（为"AI 全市场筛选"打基础）

- 新表 `business_index_constituent`（(record_date, index_code, stock_code) 唯一 + weight）
- `_baostock.py` 新增 `fetch_index_constituents()`（query_hs300_stocks/query_zz500_stocks，login→query→logout 同线程串行 + to_thread）
- `ConstituentService.sync_all/get_list` + 调度任务 `stock.constituent_sync`（cron `10 17 * * mon-fri`，main.py 注册）
- Agent 工具新增 `get_index_constituents`（成分股查询）+ `get_index_history`（注册已有 MarketService.get_history 指数K线）

### 风控参数生效

`_build_user_prompt` 注入 `stop_loss_pct/take_profit_pct`，约束 AI 按比例设置价格位（此前两字段只存不用）。

## 验证结果

- 迁移 downgrade→upgrade 双向通过；10 条种子字段/池正确（8 全市场 SQL NULL + 30/20 固定池）
- 成分股同步实测 800 只（300+500）入库；两新工具注册调用正常
- 前端 vue-tsc 通过

## 坑

- **0015 遗留：id 引用列建成 Integer(int32)**（run.strategy_id / position.strategy_id / track_log.position_id），雪花 id 为 64 位量级，参数绑定即 `asyncpg: value out of int32 range`，策略执行必然失败（run 表一直为空的根因）。迁移 0017 改 BigInteger
- **0008 遗留：ORM `Enum(PyEnum)` 默认按 name(大写) 序列化 vs PG enum 成员是小写 value**（aifunctionenum/aiproviderenum），绑定参数报 `invalid input value for enum`。修：模型列加 `values_callable=lambda obj: [e.value for e in obj]`（sys/ai_model.py 的 provider/function_code 两列）。因 sys_ai_model 0 行（从未配过模型）从未暴露
- **休眠 bug：`CustomError(err_code=...)` 参数名错误**（正确为 `error=`），构造即 TypeError。13 处（llm_client 4 + strategy 三 service 9）批量修正
- **异步 rollback 后访问 ORM 实例属性触发同步 lazy load（MissingGreenlet）**：except 分支须在 `await db.rollback()` 前缓存 `strategy.id/name`；项目异常消息在 `.msg` 属性（`str(exc)` 为空），留痕用 `getattr(exc, 'msg', None) or exc`
- **alembic bulk_insert 多行 INSERT 按首行键集合编译列**：行字典键不一致时，缺失键的值会被静默丢弃（无池行不带 stock_pool 键 → 有池行的池丢失）。所有行必须带相同键；JSON 列 None 会落成 JSON `null` 而非 SQL NULL，需插入后 `UPDATE ... WHERE stock_pool::text = 'null'` 清理
- BaoStock `query_hs300_stocks()` 当前**不返回权重**（weight 空），排序需 `weight desc nullslast, stock_code` 兜底；工具描述勿承诺权重排序
- 前端 i18n key 类型在 `src/typings/app.d.ts` 的 Schema 手工维护（此前已知的坑，本次再踩：加 key 必须同步 app.d.ts）
- **服务运行中勿对业务表做 downgrade 验证**：迁移中间态（列被删）会被在线请求命中报错；验证 downgrade 应停服务或在空库演练
- **使用前置条件**：`sys_ai_model` 需至少配置一个默认模型（「AI 助手 → LLM 配置」），否则策略执行报"场景未绑定模型且无可用默认模型"（预期行为，run 记录留痕）

## 后续扩展

- 全市场个股财务数据同步（股息率/ROE/PE，BaoStock query_profit_data 等，逐股查询慢需批量任务设计）
- 策略股票池支持动态引用成分股（如 `{index: "000300"}`），替代手工固定池
