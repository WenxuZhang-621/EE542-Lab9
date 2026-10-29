# 三人交接约定

- C → A：`rag.api.retrieve(question, k=4) -> list[SearchHit]`，正文、chunk ID、来源、页码和分数；较大分数代表更相关。已实现，读取 `artifacts/indexes/openai`；每次调用会请求一次 OpenAI embedding，属同步阻塞调用。需要 C 的完整问答时可调 `rag.api.answer(question, session_id)`。
- C → B：UTF-8 `chunks.jsonl`，字段见 `shared/contracts.py`；另交问题和相关 chunk ID。文档与查询使用同一索引版本，固定 chunk ID。
- B：`fit(chunks, n, k)` 学习词向量/质心，`embed(text)` 返回 K 维向量。文档和查询共用已拟合参数，不能每次重新聚类。记录分词、未知词、空文本和归一化分母处理；基线遵循 PDF 的总词数归一化要求，改进方法另记。
- A：`answer_with_sources` 计划返回 `{"answer": str, "sources": [{"chunk_id": str, "source": str, "page": int|null}]}`；内部如何调用 C 的同步接口由 A 决定，避免阻塞 FastAPI 事件循环。会话记忆按用户/会话隔离。
- A → B：真实 HTTPS 网站 URL；B → A：包名、公开签名指纹、assetlinks 内容。私钥不共享到仓库。
- `data/examples` 只有虚构接口样例，不是正式知识库、检索结果或实验证据。
- C 的上传页面只实现一套，A 不重复开发。A 修改 Web，B 修改 Android/自定义 embedding，C 修改 RAG；共享结构变更先协调。
