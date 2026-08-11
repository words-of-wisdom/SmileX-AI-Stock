# AI 助手一级目录 + LLM 配置菜单调整

## 需求描述

将原有「AI 配置」一级目录改名为「AI 助手」，并把其下的「AI 模型配置」子菜单改名为「LLM 配置」。实际背景：该菜单在迁移 0009 中已设计为 `ai`(CATALOG) > `ai_model`(MENU) 结构，但当前运行库 alembic 停在 `0004`（0005-0009 未应用），导致 AI 菜单在 dynamic 路由模式下不可见。本次同时修复运行库数据 + 调整 i18n 文案。

## 状态

已完成

## 涉及范围

### 后端

- 运行库 `sys_menu`：直接插入 `ai` CATALOG（sort=7, icon=mdi:robot-outline, is_system=True）+ `ai_model` MENU（component=view.ai_model）+ 4 个按钮权限（sys:ai_model:list/add/edit/delete）
- 迁移 `0009_seed_ai_model_menu.py`：已有种子，结构无需修改（路由名 `ai`/`ai_model` 不变，文案走前端 i18n）

### 前端

- i18n：`src/locales/langs/zh-cn.ts` `route.ai` 改为 'AI助手'、`route.ai_model` 改为 'LLM配置'
- i18n：`src/locales/langs/en-us.ts` `route.ai` 改为 'AI Assistant'、`route.ai_model` 改为 'LLM Config'
- 路由名、组件、elegant-router 类型均无变更（`ai` / `ai_model` 保持不变）

## 约束与备注

- dynamic 路由模式下菜单完全由 `sys_menu` 表驱动，前端 static routes.ts 仅用于类型生成
- 路由名（`ai`、`ai_model`）是菜单 name 与 i18n key 与组件注册的桥梁，不可随意改名
- 超级用户自动获得所有启用菜单 + 所有按钮权限，无需手动分配角色
- 运行库 alembic 当前停在 `0004`，`0005`-`0009` 未应用（news/stock_hot/ai_model 表 + 菜单种子均缺失）；新环境 `alembic upgrade head` 后种子自动生效

## 相关文件

- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `backend/alembic/versions/0009_seed_ai_model_menu.py`（未改动，结构已正确）

## 记录日期

2026-08-10
