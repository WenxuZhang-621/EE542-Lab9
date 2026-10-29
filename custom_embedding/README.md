# B：自定义 Embedding

按 `api.py` 接口开发。建议新增 `word_vectors.py`、`kmeans.py`、`histogram.py`、`evaluate.py`；这些算法尚未实现。

顺序：Word2Vec N 维词向量 → 自写聚类 → K 个质心 → 每个 chunk 的 K 维归一化直方图 → 改进实验。

C 已交付的输入（详见 [data/topic/README.md](../data/topic/README.md)）：

- 文本块：`data/topic/index/chunks.jsonl`，1694 块，chunk ID 固定。
- 评估问题：`data/topic/questions.jsonl`，32 题，每题标有相关 chunk ID。
- OpenAI 检索基线：`data/topic/baseline_openai.json`（hit@1/4/10、recall@k、MRR）。用 `rag.evaluate.score(questions, rankings)` 给自己的方法打分，就能和基线直接比较。

原始方法与改进共用这份文本块和问题集，保留参数与结果。与 OpenAI 基线比较和这些指标是组内约定，PDF 没有指定评估指标。依赖版本待实现时验证后添加。
