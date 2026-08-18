# 2026-08-17 LLM 配置增加 MiniMax + 计费模式 + 拉取模型列表

## 需求

LLM 配置：①增加 MiniMax 供应商；②区分每个供应商是按量计费还是 Coding Plan（对应接口端点不同，需可配置）；③支持从供应商拉取可用模型列表（API Key 不能为空）。

## 背景事实（外部）

- 同一供应商两种计费模式端点可能不同：智谱按量 `open.bigmodel.cn/api/paas/v4` vs Coding Plan `open.bigmodel.cn/api/coding/paas/v4`（**填错 Coding Plan key 会误扣按量余额**）；MiniMax 两种模式同域名 `api.minimaxi.com/v1`
- MiniMax 走 OpenAI 兼容 `/chat/completions`；模型列表接口 OpenAI 族为 `GET {base}/models`（Bearer），Anthropic 为 `GET {base}/v1/models`（x-api-key），响应均为 `{data: [{id}]}`

## 实现（迁移 0019）

- `aiproviderenum` 新增 `minimax`；`sys_ai_model` 新增 `billing_mode`（pay_as_you_go/coding_plan，server_default 按量）
- ORM：`AiProviderEnum.MINIMAX`；`AI_PROVIDER_DEFAULT_BASE_URL` 重构为 **(provider, billing_mode) 二级字典**（真源），前端抽屉有硬编码副本需同步
- schema：Create/Update/Response/查询参数加 billing_mode；新增 `AiModelFetchModelsRequest`（**api_key min_length=1 必填**，仅本次使用不落库）/`AiModelFetchModelsResult`
- 新端点 `POST /admin/sys/ai-model/models`（权限 `sys:ai_model:list`）：按计费模式取默认 base_url（可显式传），调供应商 models 接口，返回排序去重的模型 id 列表
- `stream_chat`/`_do_ping` 无需改：minimax 非 ANTHROPIC 自动落入 OpenAI 兼容 else 分支
- 前端：抽屉加计费模式下拉 + (provider,mode) 联动预填 base_url + `NAutoComplete` 模型标识（手输/下拉两用）+「获取模型列表」按钮（key 空时提示）；列表页/搜索加计费模式；i18n 双语 + app.d.ts Schema 同步

## 验证

迁移 0019 通过（enum 成员 + 列）；空 key/缺 key 被 Pydantic 拒绝；真实请求智谱 coding 端点返回 401 假 key 报错（URL 构造正确）；vue-tsc / eslint（改动文件）通过

## 坑

- **MappedAsDataclass 字段 default 位置限制再次触发**：新列 ORM 加 `default=` 后跟无默认值字段报 dataclasses TypeError，改用 `insert_default=`（仅 DB 层默认，不参与 dataclass）
- FastAPI query model 的 Enum/校验器问题沿用上次结论：查询参数用 `Annotated[Optional[T], BeforeValidator(...)]`，billing_mode 查询参数同样处理
- **查询参数解析器必须区分"空串=不过滤"与"写入字段非法值回退默认"两种语义**：billing_mode 查询参数初版把空串回退成 pay_as_you_go，导致未选筛选条件时 Coding Plan 记录从列表消失（后端 200 正常、纯过滤逻辑 bug）。查询参数用 `_parse_billing_mode_query`（空/非法→None），Create/Update 用 `_parse_billing_mode`（非法→默认）
- **`response_base.fail()` 的 data=None 与 `response_model=ResponseModel[X]` 必填 data 冲突 → ResponseValidationError 500（前端只见"服务器错误"）**：泛型响应模型的端点失败时也应走 `success(data=result)`，由 result 自身的 success/message 字段区分成败（同 test_ai_model 模式）；前端判断 `data.success` 并展示 `data.message`
- NAutoComplete 下拉仅在输入交互时出现，"拉取后自动展开"场景应改用 NSelect（filterable+tag 支持手输任意值）+ 拉取成功后 `nextTick` 调 `selectRef.focus()` 自动展开

## 迭代（同日反馈修复）

- 拉取模型列表"服务器错误"= fail 分支 ResponseValidationError（见上坑）
- 列表不显示 = billing_mode 查询参数空串被强制过滤（见上坑）
- **即时测试连接**：新端点 `POST /admin/sys/ai-model/test`（AiModelTestConnectionRequest：表单值 + api_key 留空且传 model_id 时用已保存 key 解密）；`_do_ping` 重构为参数化 (provider, base_url, model_name, api_key) 双调用点复用；抽屉 footer 加「测试连接」按钮（新增/编辑均可用）

## 后续扩展

- 各供应商"测试连通"可按 billing_mode 提示端点差异（当前 ping 用已存 base_url，语义不变）
- MiniMax 海外域名（api.minimax.io/v1）由用户在 base_url 自行填写
