修复持仓跟踪列表接口 500 错误：

1. `backend/modules/strategy/services/position_service.py`
   - 第 10 行 import 改为：`from sqlalchemy import select, func, case`
   - 第 126 行 `func.case((BusinessStrategyPosition.status == "holding", 0), else_=1)` 改为 `case((BusinessStrategyPosition.status == "holding", 0), else_=1)`（SQLAlchemy 2.0 的 tuple-whens + else_ 写法）

验证：调用/启动后端，请求 GET /admin/strategy/positions 确认返回 200。