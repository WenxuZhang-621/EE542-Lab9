# 第 7 步：带记忆的对话链与 exit 命令行

2026-10-28 PDT，Wenxu 本机。embedding：text-embedding-3-small；对话：gpt-6-luna（默认 temperature，见 c-step5）；top-k=4。

| 文件 | 内容 |
|---|---|
| offline-tests.txt | 全部离线测试 27 个通过（3 个 MySQL 测试默认跳过），DeprecationWarning 视为错误 |
| cli-transcript.txt | `python -m rag.cli` 真实 5 轮问答，问题由 stdin 输入 |
| cli-full-pipeline.txt | `python -m rag.cli --input data/raw/part3-lab-only`：PDF 文件夹 → MySQL → 切块 → 建索引 → 问答 → exit |

cli-transcript 验证：

- 追问 "How should that vector be normalized?" 被改写为完整问题，第 1 名为 p.6 直方图段（0.679），回答"除以 chunk 总词数"。
- 再追问 "What should we try after building it?" 继续正确指代，回答"尝试不同方法改进"。
- 无关问题 "What is the capital of France?"：检索分数仅 0.05–0.06，回答 "The documents do not cover…"，没有编造。
- 中文问题用中文回答（CharacterTextSplitter，500）。
- 输入 exit 后程序退出（退出码 0），其后的一行没有被提问。

cli-full-pipeline：同一 PDF 已在库中，所以显示 skipped（按来源+内容哈希去重）；26 块重新建在 artifacts/indexes/openai-ef717012a5ba，内容与默认索引相同。
未做：上传页还没接入入库/建库；Part 4 主题数据未开始；网页端到端和 A 的接入未测。
