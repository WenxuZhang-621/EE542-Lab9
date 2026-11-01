# 三人交接约定

- C → A：`rag.api.retrieve(question, k=4) -> list[SearchHit]`，读取仓库里的 `data/topic/index`（Part 4 F-1 学生知识库）。每次调用请求一次 OpenAI embedding，属于同步阻塞调用，FastAPI 里放到线程池执行；服务器 `.env` 需要 OpenAI key。`SearchHit.chunk.source` 是语料文件名，用 `data/topic/catalog.json` 换成标题和网址展示。需要 C 的完整问答时可调 `rag.api.answer(question, session_id)`。网页需显示 `data/topic/sources.json` 里的 notice：资料只作一般信息，不构成法律或税务建议。
- C → B：知识库正文在 `data/topic/index/chunks.jsonl`（字段见 `shared/contracts.py`，chunk ID 固定）；评估问题在 `data/topic/questions.jsonl`；OpenAI 基线在 `data/topic/baseline_openai.json`。用 `rag.evaluate.score(questions, rankings)` 按同一指标打分，见 `data/topic/README.md`。
- B：`fit(chunks, n, k)` 学习词向量/质心，`embed(text)` 返回 K 维向量。文档和查询共用已拟合参数，不能每次重新聚类。记录分词、未知词、空文本和归一化分母处理；基线遵循 PDF 的总词数归一化要求，改进方法另记。
- A: `answer_with_sources` returns `answer`, `sources`, `notice`, `citation_warning`, and `standalone_question`. Sources include their number, chunk ID, filename, page, title, URL, publisher, excerpt, context chunk IDs, and citation status. C's synchronous retrieval runs in a worker thread; memory is isolated by user/session. See `A-HANDOFF.md` for verification status.
- A -> B: the real public HTTPS website URL.
- B → A：包名、公开签名指纹、assetlinks 内容。私钥不共享到仓库。
- `data/examples` 只有虚构接口样例，不是正式知识库、检索结果或实验证据。
- C 的上传页面只实现一套，A 不重复开发。A 修改 Web，B 修改 Android/自定义 embedding，C 修改 RAG；共享结构变更先协调。知识库更新后 chunk ID 会变，C 重新生成 `questions.jsonl` 和基线并通知 A/B。
