# B：自定义 Embedding（Part 5）

按 PDF Part 5 的方法把 Part 4 知识库的 1694 个文本块重新向量化：**Word2Vec 词向量 → 自写 k-means 聚成 K 类并求质心 → 每个块的 K 维归一化词直方图**，再在同一套评估上尝试改进，和 C 的 OpenAI 检索基线比较。

## 文件

| 文件 | 内容 |
|---|---|
| `tokenize.py` | 统一分词（小写、保留数字和 `f-1`、`1040-nr` 这类带连字符的词）；可选停用词表。训练、文档、查询必须用同一个分词器 |
| `kmeans.py` | **自写的 k-means**：k-means++ 初始化、Lloyd 迭代、空簇处理；欧氏或球面（余弦）两种距离；只用 NumPy。另有硬分配和软分配 |
| `model.py` | `HistogramEmbedder`：训练（gensim Word2Vec → k-means → IDF）、`embed()`、保存/加载；所有改进都是 `HistogramConfig` 上的开关 |
| `api.py` | 组内接口 `fit(chunks, n, k)` / `embed(text)`；模型存在 `artifacts/custom_embedding/<name>`（不提交），文档和查询共用一个已拟合的模型 |
| `evaluate.py` | 实验网格：基线、参数扫描、单项改进、组合、种子敏感性；输出 `evidence/b-part5/` |
| `../tests/test_custom_embedding.py` | 12 项检查：距离计算与 NumPy 一致、k-means 能分开三簇且惯性单调不增、直方图之和等于"已知词数 / 总词数"、保存后重载结果相同 |

## 运行

```sh
python -m unittest tests.test_custom_embedding -v
python -m custom_embedding.evaluate            # 全部实验，约 3 分钟 -> evidence/b-part5/results.{json,md}, metrics.png
python -m custom_embedding.api fit --best      # 用最佳配置拟合并保存模型
python -m custom_embedding.api embed "How many months of OPT can a student get at each degree level?"
```

依赖：`rag/requirements.txt` 加 `gensim`、`scikit-learn`（后者只用于可选的对比）、`matplotlib`（画图）。Python 3.12+。

## 方法

**基线（PDF 原文）**，`HistogramConfig()`：
1. 对 1694 个块的分词结果训练 Word2Vec（skip-gram，N=100，窗口 5，min_count=2，30 轮，固定种子），得到 3039 个词的向量。
2. 自写 k-means 把这 3039 个词向量分成 K=200 簇，得到 200 个质心。
3. 一个块的向量：把块里每个词按最近质心计数，得到 200 维直方图，**除以块的总词数**（含不在词表里的词，按 PDF 要求）。
4. 查询同样处理；检索按余弦相似度在全部 1694 个块里排序。

**改进**，每项只改一个开关，便于归因：

| 开关 | 想法 |
|---|---|
| `metric=cosine` | Word2Vec 的相似度本来就是余弦，用球面 k-means 聚类更一致 |
| `drop_stopwords` | the/of/and 占了大量词数却不携带主题，先去掉再计数 |
| `weighting=idf` | 出现在大多数块里的词权重低（TF-IDF 的思路搬到直方图上） |
| `soft_top_m=3` | 一个词同时落入最近的 3 个质心，按距离软分配，减少边界词的随机性 |
| `normalize=l2` | 余弦检索下 L2 归一化比"除以词数"更匹配 |
| `append_mean_vector=α` | 在直方图后拼上块内词向量的均值（N 维），直方图记"用了哪些词簇"，均值记"整体语义方向" |
| K、N、CBOW | 参数扫描 |

## 结果（32 题，`rag.evaluate.score`，同一份块和问题，和 OpenAI 基线直接可比）

| 方法 | hit@1 | hit@4 | hit@10 | MRR |
|---|---|---|---|---|
| OpenAI text-embedding-3-small（C 的基线） | 0.656 | 0.938 | 0.969 | 0.790 |
| BM25 关键词检索（参考，不是 embedding） | 0.531 | 0.844 | 0.875 | 0.663 |
| **基线：PDF 的直方图方法** | 0.250 | 0.438 | 0.562 | 0.349 |
| 单项：拼均值向量 α=0.5 | 0.312 | 0.500 | 0.719 | 0.413 |
| 组合（余弦 k-means + 去停用词 + IDF + 软分配 + L2），K=200 | 0.219 | 0.438 | 0.531 | 0.323 |
| 组合，K=400 | 0.312 | 0.656 | 0.688 | 0.455 |
| **组合，K=400，拼均值向量 α=1.0（`BEST`）** | 0.375 | 0.656 | 0.750 | 0.496 |
| 组合，K=400，α=2.0 | 0.406 | 0.625 | 0.781 | 0.526 |

完整表（含 K/N/CBOW 扫描和每道题的命中名次）在 [`evidence/b-part5/results.md`](../evidence/b-part5/results.md)，图在 `metrics.png`。

**种子敏感性。** Word2Vec 和 k-means 都随机，语料只有约 12 万词（121,307 个词），所以结果对种子很敏感。4 个种子（42、1、2、3）下：基线 hit@1 = 0.25 / 0.09 / 0.25 / 0.09，hit@4 = 0.44 / 0.22 / 0.34 / 0.31；BEST hit@1 = 0.38 / 0.31 / 0.28 / 0.28，hit@4 = 0.66 / 0.56 / 0.53 / 0.50。**BEST 在每个种子上都高于基线**，平均 hit@4 从 0.33 提到 0.56；但单个数字上下 3–10 个百分点都可能是随机，32 道题里一道题就是 3.1 个百分点，所以 α=1.0 和 α=2.0 之间的差别不作结论。

## 观察

- **为什么直方图远不如 OpenAI 和 BM25。** 直方图丢掉了词的身份，只保留"落在哪个簇"：问 OPT 的月数，`opt`、`months`、`12`、`24` 可能和几十个别的词共用一个簇。BM25 恰恰靠精确的词匹配拿到 0.53，说明这个任务很大程度是关键词任务。
- **K 太小是灾难，K 太大也不行。** K=50/100 时 hit@1 掉到 0.06–0.09（簇太粗，所有块看起来都一样）；K=800 时又下降（簇太细，查询和块的词落不到同一个簇）。K=200–400 是这套语料的合适范围。
- **单项改进几乎都不起作用，组合起来才有效。** 去停用词单独用甚至更差（问题本身很短，去掉停用词后直方图更稀疏），但和 IDF、软分配、K=400 一起用时 hit@4 从 0.44 到 0.66。改进之间有交互，不能一项项孤立判断。
- **拼均值向量是最稳的一项。** 它补回了直方图丢掉的"方向"信息，hit@10 从 0.56 提到 0.72–0.78。
- **评估中的 4 道题（4、12、13、23）所有直方图变体都找不到**，OpenAI 也只排到第 2–9 名：这些问题的措辞和原文差别大（例如 "cap-gap"、"maximum period of admission"），需要真正的语义理解，是这类方法的上限。

## 接口约定的落实（`docs/interfaces.md`）

- `fit()` 一次、`embed()` 多次，文档和查询共用同一个已保存的模型；重新 `fit` 会改变簇的编号，所以模型保存在 `artifacts/custom_embedding/current`，不在每次调用时重新聚类。
- 分词、未知词（不在词表里，不计入直方图但计入基线的分母）、空文本（返回全零向量）、归一化分母的处理都在 `model.py` 里有注释。
- 基线严格按 PDF 用总词数归一化；改进方法另外记录。
