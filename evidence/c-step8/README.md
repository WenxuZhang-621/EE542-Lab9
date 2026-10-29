# 第 8 步：Part 4 主题资料与知识库

2026-10-28 PDT，Wenxu 本机。主题：F-1 International Student Assistant（身份、CPT/OPT、报税）。

| 文件 | 内容 |
|---|---|
| build-kb.txt | `rag.cli --input data/raw/topic/corpus --index data/topic/index --build-only`：17 份文档入库，1694 块（21–500 字符），text-embedding-3-small 1536 维，163,063 tokens |
| cli-topic.txt | `rag.cli --index data/topic/index` 真实 6 轮问答 |

资料清单、哈希和整理规则见 data/topic/README.md 与 sources.lock.json。

处理过程中的修正：
- govinfo 没有 2026 版 Title 8，下载返回"Page Not Found"网页；加了文件签名检查，改用 eCFR 截至 2026-09-30 的现行 8 CFR 214.2，并只保留 (f)。
- IRS PDF 每页有印刷校样页眉，另有约 2000 处断行连字符和 "Y ou"、"W -4" 一类拆词；整理成按页分隔的干净文本后重建了索引（前两次建出的索引已删除）。

cli-topic 结果：
- OPT 失业上限 90 天；追问 "And with the STEM extension?" 被改写后答 150 天（总 OPT 期间）。
- "毕业后能留多久"：回答以法规为准是 30 天，并指出另一来源写 60 天与法规冲突。
- 中文问题用中文回答（校内每周 20 小时）；无关问题（披萨）回答文档未覆盖。
- 不足："没有收入要不要交 Form 8843"，前 4 个检索结果未命中对应段落，回答文档未覆盖。
