# C：数据与 RAG

先给 A/B 少量真实 chunks，再实现 `api.py` 的接口。`reference/` 保存课程提供的旧版 Streamlit 示例，仅作参考；未验证旧 LangChain API 在当前版本中可用。

建议依次新增：`ingest.py`（文件夹 PDF 提取、MySQL 入库）、`chunking.py`（CharacterTextSplitter，size=500）、`vectorstore.py`（OpenAI embedding）、`chain.py`（上下文问答及会话记忆）、`cli.py`（exit 退出）、`upload_app.py`（单/多 PDF、文本及其他选定格式）。这些文件尚未实现。

从仓库根目录复制 `.env.example` 到根目录 `.env` 后自行配置；实现时使用 `load_dotenv(ROOT / ".env")`（ROOT 来自 shared.config），不另建模块级 .env。切块和检索参数从 `shared.config.CONFIG` 读取。依赖版本在实际实现、验证后写入本模块 requirements.txt，不照抄旧示例环境。

验收：数据库样例、切块参数、真实 embedding、检索上下文与回答、多轮问题及命令行退出。Part 3 使用 OpenAI；Part 4 数据须注明来源。
