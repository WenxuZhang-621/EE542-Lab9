# A：网站与集成

`backend/app.py`、前端和 SQL 来自本次提供的群聊模板，不代表成员新增贡献；当前 ask_llm 仍是普通聊天，未接入 RAG。

从仓库根目录执行（Python 3.10+）：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r webapp/backend/requirements.txt
cp -n .env.example .env
# 编辑真实数据库连接、JWT secret 和 LLM 配置，然后启动：
python -m webapp.backend.run
```

前提：自己安装并运行 MySQL，按 `sql/schema.sql` 创建库和最小权限用户（先替换示例密码）；配置可用的 Llama 端点。骨架未创建数据库或模型。

待做：跑通基础服务；实现 `backend/rag_service.py` 并接入 ask_llm；前端来源/状态展示；HTTPS 部署；按 B 提供的信息替换 assetlinks。当前依赖沿用模板，兼容版本待实际安装验证后固定。
