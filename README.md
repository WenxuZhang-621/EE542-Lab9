# EE542 Lab9 — Custom Chatbot

主题问答 Android App：群聊网站 + 自托管 Llama 3 + RAG 知识库 + 自定义直方图 embedding。**C 已开始实现上传与文本预览；完整 RAG、网站集成与算法仍待完成。**

## 分工（建议，待全组确认）

| 成员 | 负责部分 | 代码贡献 |
|---|---|---|
| **A：网站与系统集成** | Part 1 + Part 4 网站端 | 修改后端 `ask_llm()`，加入检索上下文；编写 RAG 接入模块；修改前端交互和来源展示 |
| **B：Android 与自定义 Embedding** | Part 2 + Part 5 + Part 4 App 端 | 自写聚类、质心计算、直方图 embedding 和评估代码；修改 Android 配置 |
| **C：Wenxu，数据与 RAG 问答** | Part 3 + Part 4 主题知识库 | 编写数据导入、切块、向量检索、问答链及命令行模块；改造现有上传页面；准备评估问题集 |

### A：网站与系统集成（`webapp/`）

- 装 MySQL，跑通 FastAPI 后端；编译 llama.cpp，在 8001 端口运行 Llama 3 8B
- 实现 `webapp/backend/rag_service.py` 并接进 `ask_llm()`：先调用 C 的 `retrieve()`，再带上下文回答并附来源
- 前端显示回答来源和加载/失败状态，页面适配手机
- 部署成 HTTPS 网站，放上 B 提供的 `assetlinks.json`，配合 B 验证 App
- 收尾：做提交页，汇总全组 Git 日志
- **完成标准：** 两个浏览器窗口同步收到消息；主题问题的回答带来源

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
| A → B | 网站地址 | 先给局域网地址，部署后换 HTTPS |
| B → A | 包名和签名指纹 | 生成签名后 |
| A、B → C | 各自剪好的视频片段 | 录完后 |

函数签名、数据格式见 [docs/interfaces.md](docs/interfaces.md) 和 `shared/contracts.py`。

## 开工前

- 在仓库根目录执行 `cp -n .env.example .env`，填自己的数据库、JWT secret 和 API key
- Python 3.10+，所有模块从仓库根目录运行；各模块的运行步骤见该目录的 README
- 公共参数（端口、切块、top-k、路径）只在 `config/project.json` 修改，改它或 `shared/` 前先在群里说
- `webapp/`、`android/` 和 `rag/reference/` 来自课程模板，不算个人贡献；每人用自己的 Git 身份提交自己的改动
- 不提交 `.env`、签名私钥、模型文件和原始数据

## C 的逐步实现

学习入口：[tutorial.md](tutorial.md)。当前先做 Part 3-I 上传与文本预览；在根目录运行 `source .venv/bin/activate` 后执行 `python -m rag.run_upload`，访问 http://127.0.0.1:8501。已通过独立命令行完成 PDF 批量提取和 MySQL 原文入库；上传页仍只预览。尚未调用 OpenAI 或构建向量库。

C 的入库入口：`python -m rag.ingest --input data/raw/part3-demo`。本地独立 MySQL 配置见 `infra/compose.mysql.yml`，使用本机 13306 端口；详细运行、验证和停止方式见 tutorial.md 第 2 课。

C 已完成 Part 3-II.2：`rag/chunking.py` 从 MySQL 原文导出带来源/页码的 chunks.jsonl；学习代码见 tutorial.md 第 3 课。当前使用实验 PDF 作流程样例，正式主题数据尚未开始。

C 已用真实 OpenAI API 建好实验 PDF 的向量库，并完成 `retrieve()`、带记忆的问答链和 `exit` 命令行（`python -m rag.cli`），见 [rag/README.md](rag/README.md)。上传页接入和 Part 4 主题数据仍待完成。
