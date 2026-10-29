# C：数据与 RAG

先给 A/B 少量真实 chunks，再实现 `api.py` 的接口。`reference/` 保存课程提供的旧版 Streamlit 示例，仅作参考；未验证旧 LangChain API 在当前版本中可用。

建议依次新增：`ingest.py`（文件夹 PDF 提取、MySQL 入库）、`chunking.py`（CharacterTextSplitter，size=500）、`vectorstore.py`（OpenAI embedding）、`chain.py`（上下文问答及会话记忆）、`cli.py`（exit 退出）、`upload_app.py`（单/多 PDF、文本及其他选定格式）。以上均已实现，另有 `retrieval.py`（检索）；上传页尚未接入入库和建库。

从仓库根目录复制 `.env.example` 到根目录 `.env` 后自行配置；实现时使用 `load_dotenv(ROOT / ".env")`（ROOT 来自 shared.config），不另建模块级 .env。切块和检索参数从 `shared.config.CONFIG` 读取。依赖版本在实际实现、验证后写入本模块 requirements.txt，不照抄旧示例环境。

验收：数据库样例、切块参数、真实 embedding、检索上下文与回答、多轮问题及命令行退出。Part 3 使用 OpenAI；Part 4 数据须注明来源。

## 当前已实现：第 1 步

`documents.py` 提取 PDF/TXT/Markdown 文本，`upload_app.py` 提供侧边栏单/多文件上传与逐页预览；`run_upload.py` 从公共配置读取启动地址。运行 `python -m rag.run_upload`。依赖见 requirements.txt，学习路线见仓库根目录 tutorial.md。该页面仍只做预览；入库与切块通过后面的独立命令行运行，向量化和问答待实现。

## 当前已实现：第 2 步

`ingest.py` 批量扫描 PDF，`storage.py` 将文档版本和逐页原文写入 MySQL。已在本机独立 MySQL 8.4 验证；本机 .env 配置端口 13306。安装依赖：`python -m pip install -r rag/requirements.txt`。

```sh
docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait
python -m rag.ingest --input data/raw/part3-demo
LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v
```

`data/raw/part3-demo` 是当前机器复制的两份课程 PDF，不提交 Git；其他成员需自行准备输入目录。详细流程与字体警告见 tutorial.md 第 2 课。数据库测试只清理自身随机命名的测试记录。

## 当前已实现：第 3 步

`chunking.py` 从 MySQL 读取指定版本，使用 CharacterTextSplitter 按 500 字符切块，输出 chunks.jsonl 与 manifest。运行示例见 tutorial.md 第 3 课。当前样例 6 页 → 26 块（205–499 字符），保留来源和页码，重复输出一致；尚无向量。

## 当前已实现：第 4 步

`embeddings.py` 调用官方 OpenAI embeddings，`vectorstore.py` 保存 FAISS 索引和有序 chunk 映射。`python -m rag.vectorstore` 已用真实 API 建库：26 块，text-embedding-3-small，1536 维（evidence/c-step6）。详见 tutorial.md 第 4 课。

## 当前已实现：第 5 步（检索、带记忆问答、命令行）

- `retrieval.py::VectorStore.search`：用索引记录的同一模型把问题转成向量，归一化后取 top-k，返回 `SearchHit`（分数为余弦，越大越相关）。
- `chain.py::create_conversation_chain(llm, vectorstore)`：每个 session 一份完整对话缓冲；有历史时先把追问改写成完整问题，再检索，最后只依据检索段落回答并标注 [1] 等来源，找不到就说文档没有覆盖。
- `cli.py`：PDF Part 3-III 的 driver，循环提问，输入 `exit` 退出，显示答案和检索到的段落。
- `api.py`：`retrieve()` 和 `answer()` 已接通，供 A 调用。

```sh
python -m rag.cli                                   # 用 data/processed/chunks.jsonl 的索引
python -m rag.cli --input data/raw/part3-lab-only   # 从 PDF 文件夹开始跑完整流程
```

`.env` 需要 `OPENAI_API_KEY`、`OPENAI_EMBEDDING_MODEL`、`OPENAI_CHAT_MODEL`（当前 gpt-6-luna，它只接受默认 temperature，所以代码不传该参数）。真实运行记录见 evidence/c-step7。上传页仍只做预览，Part 4 主题数据还没开始。
