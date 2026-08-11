# 业务需求记忆

存放每次用户提出的业务需求记录。

## 规则

- 用户提出业务需求时，**必须**新增或更新一条记录
- 使用 `TEMPLATE.md` 作为新记录的模板
- 记录完成后在 `project-memory.md` 中更新索引

## 需求索引

- [2026-08-11 A股行情同步兜底扩展](./2026-08-11_astock_sync_fallback_extend.md) — 东财 push2 对本机 IP 拒连致大盘/板块/热榜为空：板块加腾讯行情兜底（行业 t=01/概念 t=02）、东财人气榜改 emappdata+新浪批量行情自研两步、指数降级链插入新浪实时层（东财→新浪→baostock→新浪日线）、东财/新浪指数结果不满 7 个视为失败继续降级、板块入库按 board_code 同批去重修 CardinalityViolation；行业链后补同花顺层（东财→同花顺→腾讯，含成交额/净流入/涨跌家数，取 td data-value 原始值避中文单位坑）、同日重同步先删后插防多源混杂；换手率仅东财有，限流期间仍显示空；本机两个后端实例并行跑调度致任务双倍执行
- [2026-08-11 A股大盘指数多源降级（akshare+Baostock+新浪）](./2026-08-11_astock_multi_source_fallback.md) — 大盘指数抓取三级降级链（东财→baostock→sina），baostock 不覆盖科创50由 sina 补齐；baostock 日线盘后更新盘中取不到当日；历史查询行数不足 min(days,20) 时自动回补入库（查询后本地存储）；板块/涨停池仍仅东财源
- [2026-08-10 A股行情模块](./2026-08-10_astock_market_module.md) — 新增「A股」一级目录：大盘概览（今日/历史双 Tab + 指数卡片 + ECharts）、行业板块（行业/概念 + 日期快捷范围 + 涨跌幅/资金流排序）、热门个股（涨停股池 + 主板/创业板/科创板筛选 + 统计栏）；股票热榜从资讯迁入，API 前缀 /admin/stock/；3 张快照表 + akshare 定时同步（收盘后 cron）+ 手动 sync；东财高频请求有 IP 级临时限流，种子菜单 ID 需先查库占段
- [2026-08-02 deploy.sh 日志链修复 + 多模式部署](./2026-08-02_deploy_logging_fix_and_multi_mode.md) — 修生产日志链：Gunicorn error 日志改 `gunicorn-error.log`（避免与 app `error.log` 同文件滚动竞态）、`cmd_setup` 把 `deploy.env LOG_DIR` 同步进 `.env.prod LOG__DIR`、修 `.env.prod` 自拷贝死代码；`deploy.sh` 增 `pull`/`deps`/`migrate`/`restart`/`reload` 原子子命令 + 智能 `deploy`（按 `git diff` 跳过未变更的 deps/migrate，`--full` 强制）；仅后端，无 `start_prod.sh`（生产启动 = systemd 服务）
- [2026-08-10 股票热榜 + 资讯菜单重组](./2026-08-10_stock_hot_rank.md) — 新增「资讯」一级目录，资讯聚合降为子菜单，新增「股票热榜」（东财/雪球/同花顺热榜抓取，快照入库，每日排名变化跟踪）；akshare 无同花顺热榜故自研 httpx 抓取
- [2026-08-10 股票热榜跳转与雪球/同花顺加载修复](./2026-08-10_stock_hot_rank_fix.md) — 雪球代码带 SH/SZ 前缀导致前端拼出 `SZSH600519` 跳转 404（统一 stock_code 契约为纯数字）；雪球全量 5000+ 截断为 Top100；同花顺原抓龙虎榜页 JS 渲染解析必失败，改用富贵 hot_list JSON 接口；sync 入库前清理当天带前缀脏数据；前端 openStockPage 加北交所 BJ 支持
- [2026-08-10 AI 助手目录 + LLM 配置菜单调整](./2026-08-10_ai_assistant_menu.md) — 将「AI 配置」一级目录改名为「AI 助手」，子菜单「AI 模型配置」改名为「LLM 配置」；运行库 alembic 停在 0004 致 AI 菜单不可见，直接修复 sys_menu 数据 + 调整前端 i18n 文案；路由名 ai/ai_model 不变
- [2026-08-10 AI 模型配置功能](./2026-08-10_ai_model_config.md) — 新增「AI 模型配置」后台管理模块：多厂商模型 CRUD（OpenAI/Anthropic/DeepSeek/通义千问/智谱/自定义 OpenAI 兼容）+ 唯一默认模型 + 固定枚举场景绑定（智能选股/舆情分析/新闻摘要/对话问答/趋势预测）+ API Key Fernet 加密存储与脱敏显示 + httpx 连接测试（OpenAI 兼容族 Bearer token / Anthropic x-api-key）；两张新表 sys_ai_model/sys_ai_model_binding + 菜单种子迁移；前端 views/manage/ai-model 双 Tab 页面；错误码 10801-10806
- [2026-07-29 后端响应消息 i18n](./2026-07-29_backend_response_i18n.md) — 新增 `core/i18n/`（YAML key 目录 + `t()` + `Accept-Language` 解析 + 语言 ContextVar），`CustomResponseCode`/`CustomErrorCode` 的 `.msg` 按 key 懒翻译，异常类 `default_msg_key`，全量迁移约 350 条 inline 中文为 `t()`；前端 `onRequest` 注入 `Accept-Language: getLocale()`；仅 zh-CN/en-US，新增语言加 yaml 即可；日志/描述/基础设施错误不翻译
- [2026-07-28 应用用户（AppUser）后台管理](./2026-07-28_app_user_admin_manage.md) — AppUser 加 status/avatar/last_login_* 字段 + admin 模块 CRUD（`/admin/sys/app-user/*`，权限码 `sys:app_user:*`）+ C 端 `login_by_phone`/`current_user` 检查 status（禁用真正生效）+ 禁用/改密/删除复用 `OnlineUserService.kick_all_sessions` 吊销 session；前端 `views/business/app-user/` 整页（归"业务管理"顶级目录）+ i18n + 菜单种子（不分配角色，运维勾选）；password 选填（留空仅短信登录）；不新建应用模型、不修 C 端历史字段偏差
- [2026-07-28 后端 Web 安全加固](./2026-07-28_security_hardening.md) — 5 项：①文件上传引入 filetype 做 magic number + 扩展名 + 声明 MIME 三方交叉校验（挡 .exe 伪装），.env.prod 补白名单（原回退 None=任意可传）、移除 exe/msi/apk；②预览改用短期(5min)绑定 file_id 的 scoped token（POST /preview-token 换取），不再把 access token 放进 URL；③admin/app 补 logout 端点 + 修 App session key 格式 Bug（verify/logout 都用 build_session_key）；④JWT 注入 jti + Redis 黑名单（单 token 精细吊销，批量仍用 kick_all_sessions）；⑤HSTS 仅写部署 checklist（生产无 HTTPS，当前关闭正确）
- [2026-07-27 NaiveUI 组件级主题配置](./2026-07-27_naiveui_component_theme_config.md) — 主题抽屉新增「组件」Tab：codegen 从 GlobalThemeOverrides 生成全部 92 组件 × 2217 属性表，每组件单独启用 + 表单/JSON5 混合编辑，localStorage 持久化（dev 也生效），合并优先级 用户组件配置 > 预设 > 自动；zh/en i18n；顺带修 setup-store $reset 对独立 ref 无效问题
- [2026-07-23 首页仪表盘](./2026-07-23_homepage_dashboard.md) — 修复空白首页：新增聚合接口 `/admin/sys/dashboard/summary`（Redis 缓存 60s）+ 业务统计卡片（用户/角色/在线/今日登录）+ 最近登录时间线 + 最新公告列表
- [2026-05-24 API 限流 / IP 黑名单](./2026-05-24_rate_limit_blacklist.md) — Redis 多维度限流 + DB 持久化 IP 黑名单 + 自动拉黑
- [2026-05-31 多租户插件](./2026-05-31_multi_tenant_plugin.md) — 可选多租户插件，行级隔离，JWT 识别租户
- [2026-05-31 租户表隔离与权限设计](./2026-05-31_tenant_table_permissions.md) — strict/optional/全局三级隔离 + 权限分级
- [2026-06-01 租户 JWT 配置 + 登录自动选择租户](./2026-06-01_tenant_jwt_config_and_auto_select.md) — 混合模式 JWT 签名 + 登录自动选租户 + Redis/DB 双写
- [2026-06-01 插件安装自动更新 PLUGINS__ENABLED](./2026-06-01_auto_update_plugins_enabled.md) — 安装/卸载插件时自动更新 .env 中的启用列表
- [2026-06-03 数据库模块迁移](./2026-06-03_database_migration.md) — ORM 模型、连接管理、工具函数统一迁移到 database/ 包
- [2026-06-03 字典通用组件](./2026-06-03_dict_components.md) — useDict composable + DictSelect/DictTag/DictText 通用组件 + gender 种子数据
- [2026-06-17 登录 redirect 不生效修复](./2026-06-17_login_redirect_fix.md) — checkTabClear 在首次登录会吞掉 redirect 参数，登录后误回首页
- [2026-06-25 登录默认页改为权限列表第一项](./2026-06-25_login_home_from_first_permission.md) — 后端按菜单顺序 DFS 取首个有 component 的叶子作为 home
- [2026-06-25 数据权限（行级可见性）](./2026-06-25_data_scope_permission.md) — 角色配置 data_scope（ALL/DEPT_AND_SUB/DEPT_ONLY/SELF）+ 部门树 + Service 层注入过滤；含用户管理示范
- [2026-06-27 登录与菜单三件套修复](./2026-06-27_login_misc_fixes.md) — 菜单 iconType 持久化 + 侧边栏本地 icon 渲染；确认黑名单自动拉黑 IP 来源；记住密码本地缓存回填；在线用户列表去重（同 IP+UA 顶掉旧 session）；补全部门管理菜单种子 + 多租户插件支持 sys_dept 隔离
- [2026-07-04 用户/角色管理缺陷修复 + 提交类型约束加固](./2026-07-04_user_role_manage_hardening.md) — 角色重名查重(create+update)、create_user 加载 roles 修复 422、前端 flat-request 错误处理改 {error} 解构、User/Role 专用请求类型、Dict is_system 对齐、各模块 schema 校验加固
- [2026-07-11 本地 .log 日志按日期目录滚动](./2026-07-11_rolling_logs_by_date.md) — Python 应用日志与 Gunicorn access/error 日志统一按 `YYYY-MM-DD/` 目录滚动，完善 deploy/deploy.sh 与 systemd 服务
- [2026-07-05 商户管理 + 开放API HMAC 签名鉴权](./2026-07-05_merchant_openapi_auth.md) — sys_merchant 表（app_secret Fernet 加密）+ 后台 CRUD/重置密钥 + /open/* HMAC-SHA256 签名校验（时间戳窗口 + Redis nonce 防重放）+ /open/demo/ping 示例 +（迭代）商户开放管理目录 + sys_openapi_log 调用日志中间件
- [2026-07-07 异步导出、全局校验、角色表单与登录禁用优化](./2026-07-07_export_validation_login_disable.md) — 头部导出记录入口 + 操作日志异步导出 + APScheduler 每分钟执行/超时清理、WebSocket+轮询状态同步、BaseReqEntity 全局 trim + BaseRespEntity 类型安全、PageRequest int 防御 + 中文错误、角色 name/desc 长度前后端校验、禁用用户登录拦截、操作日志 total 修复 + 导出轮询白名单
- [2026-07-13 导出记录弹窗状态标识优化 + 查看全部路由修复](./2026-07-13_export_record_ui_and_constant_route.md) — 弹窗状态由图标改为 NTag（绿成功/红失败/黄生成中/灰排队）+ 下载按钮补 i18n 文本；export-record 路由纳入 constant 列表（dynamic 模式下后端菜单不返回 hideInMenu 路由）
- [2026-07-13 新建商户「数据校验错误」修复](./2026-07-13_merchant_create_validation_fix.md) — SysMerchantWithSecret.app_secret 原必填，model_validate(ORM) 缺字段抛 ValidationError；改 default=""，端点既有逻辑随后赋真实明文
- [2026-07-13 开放API测试页 crypto.subtle 报错修复](./2026-07-13_openapi_test_crypto_subtle_fallback.md) — HTTP/局域网下 crypto.subtle 为 undefined 导致 importKey 崩溃；新增 hmac-sha256 util（原生优先 + 纯 JS 回退，已用标准向量验证）
- [2026-07-13 启动时打印日志文件落地位置](./2026-07-13_print_log_location_on_startup.md) — setup_logging() 在 fileConfig 后动态读取 root logger 的文件 handler，打印日志目录/文件/归档子目录
- [2026-07-13 i18n Schema 补全 + 类型清理](./2026-07-13_i18n_schema_and_type_cleanup.md) — app.d.ts 补 exportTask/notification.tooltip/role.form.maxLength；修 dict Ref 导入、export blob 直传、角色选择 value 改 name（潜在 Bug）、number[] 转换、bordered 布尔；typecheck 38→0
- [2026-07-13 操作日志白名单补充高频轮询接口](./2026-07-13_operation_log_whitelist_polling.md) — 据近 3h 日志 Top，白名单追加 /admin/sys/route、notice/my/unread-count、notice/my/list；写操作与业务列表保留
- [2026-07-13 表格空字段统一显示为 "-"](./2026-07-13_table_empty_cell_placeholder.md) — 在共享 table hook 的 getColumns 注入默认 render（tableCellText），16 表自动生效；menu 内联表 routeName/routePath 手工补
- [2026-07-14 用户编辑保存角色不生效修复](./2026-07-14_user_list_roles_for_edit.md) — 列表响应 `SysUserListResponse` 缺 `roles`，编辑抽屉无法回填 → 保存提交 `role_ids:[]` 清空角色；补 `roles` 字段（selectinload 已有，零额外查询）
- [2026-07-14 密码复杂度策略：6-20 位且至少含字母+数字](./2026-07-14_password_complexity_policy.md) — 收紧 REG_PWD 用于写入侧（新建/修改/注册/重置），登录改仅非空避免拦截旧密码；后端 SysUserCreate/SysUserPasswordUpdate 加 validator（修 new_password max 100→20）
- [2026-07-14 调度器时区修复 + create_superuser naive 时间](./2026-07-14_scheduler_timezone_fix.md) — APScheduler/CronTrigger.from_crontab 默认按服务器本地时区，UTC 服务器 cron 偏移 8h；三处显式固定 Asia/Shanghai；create_superuser 改 aware
- [2026-07-15 关于我们页面（前端常驻路由 + 构建时 Git 历史）](./2026-07-15_about_page.md) — 左右布局「关于」页：左项目介绍（定位/技术栈/特性），右 NTimeline 展示 Git 提交；about 经 `onRouteMetaGen` 标 constant 进侧边栏固定菜单（不走动态菜单）；Git 历史由自研 vite 插件 buildStart 采集、经 virtual module 暴露，无 git 空态；纯前端不动后端
- [2026-05-27 运维 P0 修复：健康探针 + 启动硬终止](./2026-05-27_ops_p0_health_probe.md) — 新增无鉴权顶级探针 `/health`（liveness）与 `/ready`（readiness，检查 DB+Redis）；`deploy.env` 健康检查从 `/openapi.json` 改为 `/ready`（修复生产环境 openapi 被禁用导致健康检查恒 404）；`main.py` lifespan 调度器同步失败改为硬阻止启动，IP 黑名单预热失败加结构化降级日志，种子数据降 WARNING；**采用顶级路由方案（B 方案）**——澄清 `/open/*` 是商户 HMAC 签名接口（探针恒 401），`/admin/sys/*` 需额外维护操作日志白名单，顶级路径天然不受任何业务中间件约束，无需维护白名单
