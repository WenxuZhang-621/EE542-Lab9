# A：网站与系统集成

实现和验证说明见 [A-HANDOFF](../docs/A-HANDOFF.md)，部署见 [DEPLOY-A](../docs/DEPLOY-A.md)。Python **3.12+**。所有命令从仓库根目录执行。

## 本地启动

```powershell
# Windows（已安装 Python 3.12+）
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-a.txt
.\.venv\Scripts\python.exe -m scripts.setup_a
```

macOS/Linux 用 `python3.12 -m venv .venv`，激活后使用 `python` 运行后续命令。

`setup_a` 只在 `.env` 不存在时创建，并生成随机 JWT 与数据库密码，不覆盖已有配置、不显示密码。

1. 在本地 `.env` 中填写自己的 `OPENAI_API_KEY`。Windows 也可运行 `powershell -STA -ExecutionPolicy Bypass -File scripts/configure_key.ps1`，使用密码输入框保存，不会打印 key；保存后重启网站。A 使用 C 已建好的索引，但**每次检索仍要通过 OpenAI API 为问题生成向量**。不能用 Llama 的 API key 代替。
2. 启动 MySQL。已安装 Docker 时可使用现有的隔离数据库配置：

   ```sh
   docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait
   ```

   `setup_a` 默认的 DSN 指向 `127.0.0.1:13306/groupchat`，密码与 `.env` 的 `LAB9_MYSQL_PASSWORD` 一致。使用已有 MySQL 时自行创建 `groupchat` 库和有该库权限的 `chatuser`，修改 DSN。不要直接使用模板 SQL 的 `chatpass` 作为公网密码。
3. 运行自己的 Llama 3 Instruct 模型服务，见部署文档。默认地址为 `http://127.0.0.1:8001/v1`，模型别名为 `llama-3-8b-instruct`。
4. 启动网站：

   ```sh
   python -X utf8 -m webapp.backend.run
   ```

5. 打开 `http://127.0.0.1:8000`，注册、登录。两个窗口请使用两个账号（登录信息按浏览器标签页隔离）。取消“Ask the assistant”且消息不含问号时，只发送群聊消息。

Windows 后续也可使用 `powershell -ExecutionPolicy Bypass -File scripts/start_web.ps1`；`-Install` 会重新检查依赖。此处进程级 ExecutionPolicy 参数只用于运行本仓库脚本，不修改系统策略。

仅想先看界面、而本机没有 MySQL 时，在**新目录且没有 `.env`** 的情况下可运行 `python -m scripts.setup_a --sqlite-preview`，再启动网站。这不是老师要求的 MySQL 验收环境，不会假装完成 RAG，也不支持 C 的 MySQL 文档导入流程。

## 检查

```sh
python -m scripts.check_setup
python -m scripts.check_setup --live
python -m scripts.smoke_web_live
```

第一条不调用付费模型：检查索引、配置、数据库和模型 `/v1/models`。第二条仅在前置条件全部通过后发出一个真实问题，会调用 OpenAI embedding 和自托管 Llama。第三条创建本地 QA 账号，向运行中的网站发送两轮真实问题，检查加载事件、回答广播和来源数据库回读，会产生两次 OpenAI embedding 请求。失败退出码为 1；不把缺 key、缺模型服务伪装成通过。

如果返回 `embedding_credit_exhausted`，表示 OpenAI embedding 账户额度不足；到官方 API Billing 检查余额或可领取额度，获得额度后重试。这个错误不需要重新创建 key。只通过普通 preflight 不代表 API 额度已验证。

```sh
python -m pip install -r tests/requirements.txt
python -m pytest tests -q
node --check webapp/frontend/app.js
```

如果要包含 C 的真实 MySQL 测试，在 shell 设置 `LAB9_TEST_MYSQL=1`。测试只清理自己创建的随机 source 记录。`tests/browser_fixture.py` 是明确标记的界面测试替身，不能用于最终问答演示。

## 数据与运行约定

- 原有 `users/messages` 表保留。启动时补建 `message_details` 存来源、被回复消息 ID 和错误状态。不会自动创建数据库。
- 单一共享聊天室：所有登录用户都能看消息和回答。不要输入护照、SSN 等个人标识；每人用于模型追问的记忆独立。
- 仅启动 **一个 Uvicorn worker**。WebSocket 连接和会话锁在内存中，多 worker / 多副本部署前需引入共享消息总线与会话存储。
- 从 `sources.json` 显示知识库 notice；来源链接来自 `catalog.json`，正文使用 `textContent` 展示。
- 健康接口报告数据库连接与配置状态，`llm_configured` 只说明填了地址，不证明模型服务在线；使用 preflight 验证在线状态。
- 原始 C 知识库可能含来源日期差异。模型会被要求明确指出冲突，展示原文供核对，不把检索排名当作法律规则的优先级。

## 接口

- `POST /api/signup`、`POST /api/login` → token、username、user_id。
- `GET /api/me`、`GET /api/messages` → Bearer token 必需。
- `POST /api/messages` → `{content, ask_bot, session_id}`；session_id 是 UUID；返回原消息和可选回复。
- `POST /api/messages/{id}/retry` → 只允许原发送者重试助手问题。
- WebSocket `/ws` → 连接后 10 秒内发送 `{token}`；收到 `ready` 后接收 `message`、`bot_status`。token 不放入 URL；无认证连接无法收消息。

A 的新实现集中在 `webapp/`、`scripts/`、`infra/`、测试与交接文档。老师原始模板、C 的原实现和 A 的修改需在讲解及 Git 记录中明确区分。
