# C：数据与 RAG

负责 Part 3（文档上传、入库、切块、OpenAI 向量库、带记忆问答、命令行）和 Part 4 主题知识库。`reference/` 是课程提供的旧版 Streamlit 示例，仅作参考。

从仓库根目录运行；先 `cp -n .env.example .env`，填 `DATABASE_URL`、`OPENAI_API_KEY`、`OPENAI_EMBEDDING_MODEL`、`OPENAI_CHAT_MODEL`（当前 gpt-6-luna，只接受默认 temperature，代码不传该参数）。依赖（Python 3.12+）：`python -m pip install -r rag/requirements.txt`。本地 MySQL：`docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait`（端口 13306）。

## 模块

| 文件 | 作用 | PDF 依据 |
|---|---|---|
| `documents.py` | 提取 PDF、TXT、Markdown、HTML 文本；HTML 只取正文；含换页符的文本按页拆分 | Part 3-I |
| `ingest.py` | 文件夹或单个文件存入 MySQL（文档版本 + 逐页原文），重复内容跳过 | II.1 |
| `chunking.py` | `CharacterTextSplitter`，500 字符、重叠 100、换行优先；`chunk_folder()` 入库后切块 | II.2 |
| `embeddings.py`、`vectorstore.py` | OpenAI embedding（官方地址）+ FAISS 余弦索引，与 chunks.jsonl、manifest 一起保存 | II.3 |
| `retrieval.py` | 用索引记录的同一模型把问题转成向量，取 top-k | III.2 |
| `chain.py` | 每个会话一份对话缓冲；追问先改写再检索；只依据检索段落回答并标注来源，冲突时指出 | II.4、III.3 |
| `cli.py` | driver：可从文件夹跑完整流程；循环提问，输入 `exit` 退出 | III.1 |
| `upload_app.py` | 上传页：侧边栏上传单个或多个文件 → 入库 → 切块 → 建索引 → 提问 | Part 3-I |
| `topic_data.py`、`evaluate.py` | Part 4 资料下载与整理；评估问题集与 OpenAI 检索基线 | Part 4 |
| `api.py` | 给 A 的接口：`retrieve()`、`answer()`，读取 `data/topic/index` | Part 4 |

## 常用命令

```sh
python -m rag.run_upload                       # 上传页 http://127.0.0.1:8501
python -m rag.cli --index data/topic/index     # 主题知识库命令行问答
python -m rag.cli                              # Part 3 样例：读 C 本机的 data/processed/chunks.jsonl（不进 Git，clone 后用 --index）
python -m rag.cli --input 文件夹               # 任意文件夹：入库 → 切块 → 建库 → 问答
python -m unittest discover -s tests           # 离线测试；加 LAB9_TEST_MYSQL=1 含数据库测试
```

主题资料、知识库文件和评估方法见 [data/topic/README.md](../data/topic/README.md)。运行记录见 `evidence/c-step1` 至 `c-step10`。
