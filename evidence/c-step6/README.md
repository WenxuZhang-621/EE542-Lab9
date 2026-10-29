# 第 6 步：真实 OpenAI 向量库与 retrieve()

2026-10-28 PDT，Wenxu 本机。输入：data/processed/chunks.jsonl（实验要求 PDF，6 页 → 26 块，output_sha256 3eb28f90…）。

| 文件 | 内容 |
|---|---|
| build-index.txt | `python -m rag.vectorstore` 首次建库：created，text-embedding-3-small，1536 维，26 个向量，2835 tokens |
| rebuild-reuse.txt | 再次运行：unchanged，没有重新调用 API |
| reload-check.txt | load_store 重载：26 向量 / 1536 维 / 26 chunks，哈希校验通过 |
| retrieve-samples.txt | `rag.api.retrieve()` 真实查询 3 个问题，top-4 分数（余弦）、页码和 chunk ID |
| retrieve_samples.py | 生成上面记录的脚本 |

3 个问题的第 1 名都是对应原文：chunk 大小 → p.4 CharacterTextSplitter 段（0.478）；直方图归一化 → p.6 Part 5 段（0.626）；视频要求 → p.6 Deliverables 段（0.501）。
索引位于 artifacts/indexes/openai（Git 忽略）。只是 Part 3 流程样例，不是 Part 4 主题知识库。
