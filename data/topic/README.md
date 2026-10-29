# Part 4 知识库：F-1 International Student Assistant

主题：F-1 学生的身份维持、校内外工作（CPT/OPT/STEM OPT）和美国报税。资料全部来自美国联邦政府官方来源，回答只作一般信息，不构成法律或税务建议。

| 文件 | 内容 | 谁用 |
|---|---|---|
| `sources.json` | 17 份资料的标题、发布方、网址和整理方式 | 全组 |
| `sources.lock.json` | 实际下载的字节数、SHA-256 和下载时间 | 复现 |
| `catalog.json` | chunk 的 `source`（语料文件名）→ 标题、发布方、网址 | A 显示来源链接 |
| `index/` | FAISS 索引、同序 `chunks.jsonl`、`manifest.json`（1694 块，text-embedding-3-small，1536 维） | A：`rag.api.retrieve()`；B：读 `chunks.jsonl` |
| `questions.draft.jsonl` | 32 个评估问题及原文证据句 | 修改问题时改这里 |
| `questions.jsonl` | 由证据句标出的相关 chunk ID | B 的评估输入 |
| `baseline_openai.json` | OpenAI embedding 检索基线：hit@k、recall@k、MRR 和每题排名 | B 对比用 |

## 复现

```sh
python -m rag.topic_data fetch      # 下载到 data/raw/topic/downloads（不提交）
python -m rag.topic_data curate     # 整理成 data/raw/topic/corpus
python -m rag.cli --input data/raw/topic/corpus --index data/topic/index --build-only
python -m rag.evaluate label        # 重新标注 questions.jsonl
python -m rag.evaluate baseline     # 重新计算 OpenAI 基线
```

整理规则：8 CFR 214.2 只保留 (f) F-1 部分，用的是 eCFR 截至 2026-09-30 的现行文本（govinfo 还没有 2026 年版）；IRS 的两份 PDF 去掉每页的印刷校样页眉，修复断行连字符和字距造成的拆词，转成按页分隔的文本，保留页码；网页只取正文。重建索引前先删除 `index/`，因为已有索引不会被覆盖。

## 已知冲突

2026 年修订后的 8 CFR 214.2(f) 改为固定入境期限（最长 4 年）、结束后 30 天离境、OPT 最晚在项目结束后 30 天内申请。部分较早更新的 Study in the States 和 USCIS 页面仍写 60 天。问答提示要求模型指出冲突并优先采用法规或较新的来源；评估问题按法规标注，申请 OPT 时限一题同时把两种说法标为相关。

## B 如何对比

对每个问题按自己的 embedding 排出 chunk ID 列表，然后：

```python
from rag.evaluate import read_jsonl, score
from shared.config import project_path
questions = read_jsonl(project_path('questions'))
result = score(questions, rankings)   # rankings[i]：第 i 题的有序 chunk_id 列表
```

用同一份 `index/chunks.jsonl` 和同样的指标，结果才能和 `baseline_openai.json` 直接比较。
