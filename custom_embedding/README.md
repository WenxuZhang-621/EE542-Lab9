# B：自定义 Embedding

按 `api.py` 接口开发。建议新增 `word_vectors.py`、`kmeans.py`、`histogram.py`、`evaluate.py`；这些算法尚未实现。

顺序：Word2Vec N 维词向量 → 自写聚类 → K 个质心 → 每个 chunk 的 K 维归一化直方图 → 改进实验。先用 data/examples 验证数据结构，再换 C 的真实数据。

原始方法与改进共用文本块和问题集，保留参数与结果。与 OpenAI 基线比较、recall@k 均为实施建议，非 PDF 指定指标。依赖版本待实现时验证后添加。
