# AI 模型配置功能

## 需求描述

新增「AI 模型配置」后台管理模块，支持配置多个 AI 模型（主流厂商枚举 + 自定义 OpenAI 兼容）、设置唯一默认模型、并把固定枚举的业务场景绑定到指定模型。模型 API Key 用 Fernet 加密存储、列表脱敏显示、支持「测试连通性」。本期不接入真实业务调用，仅做配置管理 + 连接测试。

## 状态

已完成

## 涉及范围

### 后端

- 数据模型：`database/models/sys/ai_model.py`（SysAiModel、SysAiModelBinding + AiProviderEnum、AiFunctionEnum）
- Schema：`modules/admin/schemas/sys/ai_model.py`
- Service：`modules/admin/services/sys/ai_model_service.py`
- Endpoint：`modules/admin/endpoints/sys/ai_model.py`（路由前缀 `/admin/sys/ai-model`）
- 错误码：`core/response/response_code.py` 新增 AI 模型段 10801-10806
- i18n：`backend/core/i18n/locales/zh-CN.yaml` 与 `en-US.yaml` 新增 `error.ai_model.*`
- i18n：`backend/core/i18n/locales/zh-CN.yaml` 与 `en-US.yaml` 新增 `error.ai_model.*`（错误码映射）与顶级 `ai_model.*`（service t() 调用）

### 前端

- 类型：`src/typings/api/system-manage.d.ts` 新增 AiModel/AiProvider/AiFunction/AiModelBinding 等类型
- API：`src/service/api/system-manage.ts` 新增 11 个 fetch 函数
- 页面：`src/views/ai/model/`（index.vue + modules/ai-model-search.vue + modules/ai-model-operate-drawer.vue），双 Tab（模型管理 / 场景绑定）
- 路由：一级目录「AI配置」（route name `ai`，path `/ai`），AI模型配置为其子菜单（route name `ai_model`，path `/ai/model`）
- i18n：`src/locales/langs/zh-cn.ts` 与 `en-us.ts` 新增 `route.ai`、`route.ai_model` 与 `page.manage.aiModel.*`
- 路由：elegant-router 自动生成 `ai`（CATALOG）与 `ai_model`（MENU）路由

### 数据库

- 迁移 `0008_add_ai_model_module`：创建 sys_ai_model、sys_ai_model_binding 两张表 + 枚举 + 外键 + 唯一约束
- 迁移 `0009_seed_ai_model_menu`：菜单种子（顶级 ai CATALOG id=...8001 + ai_model MENU id=...8002 + list/add/edit/delete BUTTON）

## 约束与备注

- API Key 复用 `core/security/openapi/crypto.py` 的 encrypt_secret/decrypt_secret（同一 OPEN_API__SECRET_ENCRYPT_KEY）
- 响应不回传明文 API Key，通过 `SysAiModelResponseData` 的 model_validator(before) 自动把加密字段转为脱敏值
- 模型解析规则：某场景 → 启用的场景绑定优先，否则回退到默认模型
- 功能场景固定 5 个（智能选股/舆情分析/新闻摘要/对话问答/趋势预测），扩展只需加 AiFunctionEnum 枚举成员 + 迁移 + i18n
- 连接测试按 provider 分派：Anthropic 走 x-api-key header，其余走 Bearer token，超时 15s
- 迁移链：0001 → 0002 → 0003 → 0004 → e7ac2bb48021 → 0005 → 0006(stock_hot) → 0008 → 0009，单一 head `0009`

## 相关文件

- `backend/database/models/sys/ai_model.py`
- `backend/modules/admin/schemas/sys/ai_model.py`
- `backend/modules/admin/services/sys/ai_model_service.py`
- `backend/modules/admin/endpoints/sys/ai_model.py`
- `frontend/src/views/ai/model/`
 `backend/alembic/versions/0008_add_ai_model_module.py`
 `backend/alembic/versions/0009_seed_ai_model_menu.py`

## 记录日期

2026-08-10
