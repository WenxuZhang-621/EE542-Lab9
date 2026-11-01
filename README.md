# EE542 Lab9 — Custom Chatbot

主题问答 Android App：群聊网站 + 自托管 Llama 3 + RAG 知识库 + 自定义直方图 embedding。主题：**F-1 International Student Assistant**（F-1 身份、CPT/OPT 实习、报税）。

**Part A status:** Real OpenAI embeddings, local Llama, FastAPI, and MySQL are integrated and verified through public HTTPS. The website now serves Asset Links matching B's release package and certificate; signed-APK device validation remains pending. See the [Part A technical report](docs/PART-A-REPORT.md), [implementation handoff](docs/A-HANDOFF.md), [32-question evaluation and known issues](docs/A-EVALUATION.md), and [A-to-B handoff](docs/A-TO-B.md). B's Android and custom-embedding implementation and C's data/RAG work remain separate contributions.

## 分工

| 成员 | 负责部分 | 代码贡献 |
|---|---|---|
| **A: Website and system integration** | Part 1 + Part 4 website | Connect `ask_llm()` to retrieved context; implement the RAG integration module, frontend interactions, and source display |
| **B：Android 与自定义 Embedding** | Part 2 + Part 5 + Part 4 App 端 | 自写聚类、质心计算、直方图 embedding 和评估代码；修改 Android 配置 |
| **C：Wenxu，数据与 RAG 问答** | Part 3 + Part 4 主题知识库 | 编写数据导入、切块、向量检索、问答链及命令行模块；改造现有上传页面；准备评估问题集 |

### A: Website and system integration (`webapp/`)

- Set up MySQL and FastAPI; verify a llama.cpp CPU source build and run the official CUDA Llama 3.1 8B server on port 8001.
- Implement `webapp/backend/rag_service.py` and connect it to `ask_llm()`: call C's `retrieve()`, assemble context, and return answers with sources.
- Display sources, loading/failure states, and a mobile layout.
- Deploy HTTPS, publish Asset Links matching B's signing details, and support joint app verification.
- Submission coordination: prepare the submission page and collect the team's actual Git logs.
- **Acceptance criteria:** two browser sessions receive the same messages; topic answers include inspectable sources. See A's evidence for verification limits.

### B：Android 与自定义 Embedding（`android/`、`custom_embedding/`）

- 用 Android Studio 打开 `android/`，改包名和网址（填 A 的 HTTPS 网站，不是 LLM 的 8001 端口）
- 生成签名，把包名和 SHA-256 指纹交给 A；在模拟器或真机上安装签名 APK 测试
- Part 5：Word2Vec 生成 N 维词向量 → 自己写聚类分成 K 类并求质心 → 每个 chunk 生成按词数归一化的 K 维直方图
- 尝试改进方法，和原始方法、OpenAI embedding 对比
- 收尾：检查最终视频是否覆盖 PDF p.6 的四项
- **完成标准：** App 无地址栏，能登录、提问并收到回答；Part 5 有对比结果

### C：数据与 RAG 问答（`rag/`）

- 脚本遍历文件夹中的 PDF，提取文本存进 MySQL
- 用 `CharacterTextSplitter` 按 500 切块，OpenAI embedding 建向量库，实现 `rag/api.py`
- 带记忆的问答链和命令行问答（输入 `exit` 退出），只依据检索到的上下文回答
- Streamlit 上传页：侧边栏上传单个或多个 PDF，也支持文本等格式（全组只做这一套）
- 收集、清洗 Part 4 主题数据并建库；写评估问题集给 B
- 收尾：剪辑全组视频
- **完成标准：** 命令行问答能依据 PDF 回答，并显示检索到的段落

## 交接

| 谁 → 谁 | 内容 | 时间 |
|---|---|---|
| C → A、B | 少量样例 `chunks.jsonl` | 开工第一步；A、B 先用它开发 |
| C → A | 可用的 `retrieve()` | Part 3 跑通后 |
| C → B | 正式 chunks 和评估问题集 | 主题数据完成后 |
| A -> B | Website URL | https://desktop-jdferfe.taile24d30.ts.net/ |
| B → A | 包名和签名指纹 | 生成签名后 |
| A、B → C | 各自剪好的视频片段 | 录完后 |

函数签名、数据格式见 [docs/interfaces.md](docs/interfaces.md) 和 `shared/contracts.py`。

## 开工前

- 在仓库根目录执行 `cp -n .env.example .env`，填自己的数据库、JWT secret 和 API key
- Python 3.12+（`rag/requirements.txt` 锁定的 numpy 2.5.4 需要 3.12+；已在 3.12.13 验证），所有模块从仓库根目录运行；各模块的运行步骤见该目录的 README
- 公共参数（端口、切块、top-k、路径）只在 `config/project.json` 修改，改它或 `shared/` 前先在群里说
- The starting `webapp/`, `android/`, and `rag/reference/` came from course templates. Git diffs identify A's additions to `webapp/`. Each member should commit their actual contribution under their own Git identity.
- 不提交 `.env`、签名私钥、模型文件和原始数据

## C 的进度

- **已完成**：上传页（上传 → MySQL → 切块 → OpenAI 向量库 → 提问）、文件夹批量入库、500 字符切块、带记忆的问答链、`exit` 命令行，以及给 A 的 `retrieve()`。用法见 [rag/README.md](rag/README.md)。
- **Part 4 知识库**：17 份联邦政府官方资料（eCFR、IRS、USCIS、Study in the States），1694 块，在 `data/topic/`；同目录有给 B 的 32 题评估集和 OpenAI 检索基线。见 [data/topic/README.md](data/topic/README.md)。
