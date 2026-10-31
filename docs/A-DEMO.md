# A 的讲解与本地演示提纲

讲义没有独立编号的问答题。需要讲清实现方法，并按 Deliverables 展示源代码、实际上下文与 embedding、RAG 用法以及网站和 Android。下列说明用于理解和录制自己的真实工作，不是已完成的视频或个人贡献日志。

## 需要能够解释的内容

**1. 网站如何调用模型？** 登录后通过 REST 发送消息；普通消息保存到 MySQL 并用 WebSocket 广播。勾选 Ask the assistant 或消息包含问号时，`ask_llm()` 调用 A 的 `answer_with_sources()`。

**2. RAG 的实际数据流是什么？** C 的 `rag.api.retrieve()` 用同一个 OpenAI embedding 模型把问题转换成向量，在 FAISS 中找相似片段。A 加上适当的同页上下文与明确类别的章节，作为编号原文发送给本机 Llama，随后保存回答、来源、页码和引用关系。

**3. OpenAI 和本地 Llama 各做什么？** OpenAI `text-embedding-3-small` 生成 1536 维查询向量；真正回答由本机 Llama 3.1 8B 生成。OpenAI key 不发送到模型服务器或浏览器。

**4. 如何展示 embedding 的真实样子？** 运行 `python -m scripts.trace_embedding`，打开 `evidence/a/embedding-trace.json`。显示原始问题、前 8 个坐标、完整维数、归一化范数及相似度排序。8 个坐标只是完整向量的样本；不能把它说成 B 的 K 维词簇直方图。文档和查询向量先归一化，FAISS 内积因此等于余弦相似度。

**5. 为什么来源要随回答保存？** 引用编号映射到文档标题、机构、网址、页码、原文和 chunk ID。来源作为该次回答的快照写入 `message_details`，刷新后不会变成另一次检索的来源。引用编号正确不等于回答正确。

**6. 追问记忆如何隔离？** 用户 ID 加浏览器会话 UUID 构成记忆键，最多保存最近 3 轮。Llama 先把指代改写成独立问题再检索。Start a fresh assistant session 清除当前对话关联；MySQL 中的共享聊天历史不会因此删除，进程重启后模型短期记忆清空。

**7. 为什么 C 的同步检索放在线程中？** embedding 会等待网络，直接在异步端点中执行会阻塞事件循环，影响其他人的聊天和 WebSocket 广播。`asyncio.to_thread()` 负责隔离等待。

**8. 实测修了什么？** Windows 索引文件的 UTF-8/LF、源码构建长路径/Windows API 版本、密钥账户额度不足、截断句子的上下文、追问语言/主体漂移和学生章节被教师章节挤掉。只讲自己实际理解和复现过的修复。

## 建议演示顺序

1. 展示源代码：`app.py` 的 `ask_llm()`，以及 `rag_service.py` 的检索、上下文、模型请求和来源保存。
2. 打开两个已登录的浏览器，发送一条普通消息，展示同步广播和刷新后的记录。
3. 提问 `What is Form 8843 used for?`，展示加载状态、真实回答、引用编号和来源链接。
4. 追问 `What information does that form ask students to provide?`，展示仍然围绕同一表格，并与原文学生部分对照。
5. 展示 `embedding-trace.json` 中真实向量和相似度；说明 1694 个文本块与 500 字符切块来自 C。
6. 展示 390×844 手机宽度的真实页面和原文展开；这不是 Android APK 验收。
7. 展示 `A-EVALUATION.md` 中 32 题覆盖指标及实际问题，说明来源冲突和模型局限。
8. 公网入口已就绪；B 的 APK 就绪后，再补录真实 TWA 无地址栏启动、登录和提问。

按作业平台要求用手机拍到成员本人和实际屏幕，记录当天任务、遇到的问题和修复，之后剪辑成一段视频。不要把工程截图或自动化日志当作手机拍摄视频。最终提交 PDF 还需要真实 YouTube 链接与 GitHub 日志；这些尚未由代码包生成或提交。
