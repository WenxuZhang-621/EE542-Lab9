# Lab9 C：边做边理解 RAG

负责范围：Wenxu 选择 C，Part 3 和 Part 4 的主题知识库；A/B 不在本次实现范围。
起始版本：6ba2ae8；本课基于该版本后的未提交修改。前置知识：Python 函数、列表、文件读取即可。

## 全流程与后续路线

建库：文档 → 文本 → 数据库 → chunks → embedding → 向量库。
问答：问题 → query embedding → 相似度检索 → 上下文 + 问题 → LLM → 带来源的回答。

| 步骤 | Lab 依据 | 要理解的问题 | 当前状态 |
|---|---|---|---|
| 1 上传和文本预览 | Part 3-I，p.3–4；提前实现 II.1 的提取部分 | PDF 如何变成程序能处理的文字？ | 已展开，见下文 |
| 2 批量提取和数据库存储 | Part 3-II.1，p.4 | 为什么保留原文、来源和页码？ | 已展开，真实 MySQL 已验证 |
| 3 切块 | Part 3-II.2，p.4 | 如何用 CharacterTextSplitter 生成可追溯的 chunk？ | 已展开，26 块已验证 |
| 4 embedding 与向量库 | Part 3-II.3，p.4 | 一段文字如何变成可检索的向量？ | 已展开，真实 OpenAI 建库完成（26 块） |
| 5 检索和带记忆问答 | Part 3-II.4、III，p.4 | 搜到的文字如何参与答案生成？ | 已展开，真实多轮问答已验证 |
| 6 上传页接入、真实主题与交接 | Part 3-I、Part 4，p.3–5 | 如何验证整条链路并交给 A/B？ | 计划，尚未实现 |

## 第 1 课：把 PDF 变成可读文本（已展开）

**目标：**你能说明上传的文件如何变成带来源和页码的文字；分清上传、解析、存储和向量化四件不同的事。

主链：选择文件 → 点击 Extract text → UploadedFile.getvalue() → extract_pages() → DocumentPage 列表 → 页面预览。

### 阅读顺序

1. `rag/run_upload.py::main`：读取 config/project.json 的 host/8501 端口，启动 Streamlit；只在本机监听。
2. `rag/upload_app.py::main`：sidebar 中接受单/多文件，点击按钮才提取。getvalue() 取出文件的原始 bytes，交给 extract_pages。
3. `rag/documents.py::extract_pages`：根据后缀区分 PDF 与 TXT/Markdown；返回统一的 DocumentPage 列表。
4. `DocumentPage`：source 是文件名，page 是从 1 开始的 PDF 页码（普通文本为 None），text 是提取出的字符串。
5. 回到 upload_app 的逐页循环：展示页数、字符数和文本；空页显示提示。

### 为什么不是直接给 LLM 一个 PDF？

本 Lab 的 RAG 流程先把资料转成文本，再切块和生成向量。因此，这里只是准备知识库的原材料，没有训练模型，也没有调用 OpenAI。

`PdfReader(BytesIO(content))` 从内存中的 PDF 字节读取页面。`page.extract_text()` 提取可选择的文字；扫描图片中的文字需要另做 OCR，当前未实现。Markdown 本质也是文本，本步骤保留其原始标记。

PDF 页和 chunk 不是一回事：页码用于追溯来源，后续 chunk 是按长度拆出的检索单位。一页可能产生多个 chunk。

### 重要分支

- PDF：逐页提取，即使一页没有文字也保留该页，提示是否需要 OCR。
- TXT/Markdown：使用 UTF-8 解码，作为一个无 PDF 页码的文本单元。
- 空文件、超过 20 MiB、格式不支持、非 UTF-8 文本、加密或损坏 PDF：显示错误；同批其他文件继续处理。
- 20 MiB 是本地开发限制，非教师要求。

### 跑起来

在仓库根目录执行：

```sh
source .venv/bin/activate
python -m rag.run_upload
```

打开 http://127.0.0.1:8501，选择课程提供的 `lab9/embedding/Ads cookbook .pdf` 或其他非敏感文档，点击 Extract text，核对页码和实际内容。该 PDF 用于 Part 3 流程验证，不代表 Part 4 主题已经确定。

目前只预览，不将上传文件持久化，不写数据库；重开会话不会保留资料。数据库存储是下一步。Part 3-I 的转换/切块/向量化整体仍未完成。

### 串起来

选择一本有 10 页的文字 PDF → 读取 bytes → 按页提取 → 得到 10 个带来源/页码的 DocumentPage → 在页面展开查看文字。若第 3 页是纯图片，这页会提示无文本，其余页正常展示。

先暂缓阅读 rag/reference 中旧的 LangChain 链和 rag/api.py 的占位实现；后面讲到切块和问答时再看。

**自己复述：上传了 PDF 之后，我们现在得到的是什么？为什么它还不是向量库？**

## 第 2 课：批量提取并保存到 MySQL（已展开）

对应 PDF p.4 Part 3-II.1。目标：文件夹里的 PDF 怎样变成可以重新读取的数据库记录？

主链：命令行 → ingest.main → ingest_folder → extract_pages → save_document → MySQL 两张表。

### 沿调用链阅读

1. `rag/ingest.py::main`：读取 --input；默认使用公共配置 paths.raw。get_engine 连接 MySQL，init_schema 只创建 RAG 自己的两张表，不动 A 的用户/消息表。
2. `ingest_folder`：遍历目录、筛选 .pdf（大小写均可），逐个读取字节，再复用第 1 课的 extract_pages。--recursive 才递归子目录；source 是相对于输入根目录的路径，同名子目录文件不会混为一项。
3. `rag/storage.py::save_document`：计算文件内容 SHA-256，再用 source + 内容哈希生成 document_id。相同来源和相同内容跳过，内容变化会形成新版本。约定持续使用同一个输入根目录，避免相同路径名在不同根目录下含义不一致。
4. `with engine.begin() as connection`：开启事务，先写文档记录，再写所有页。成功提交，任一步失败则回滚；不会留下只有文档头、没有正文的半成品。
5. 命令行输出每份文件的 inserted/skipped/failed 和页数；只要有文件失败，退出码为 1，其余文件仍尝试导入。

### 两张表怎么关联

| 表 | 记录什么 | 关键字段 |
|---|---|---|
| rag_documents | 一份文档的一个版本 | document_id、source、content_sha256、page_count、created_at（UTC） |
| rag_document_pages | 每页原文 | document_id、ordinal、page_number、text |

document_id 把两张表关联起来。ordinal 是存储顺序；page_number 是原 PDF 页码。正文使用 LONGTEXT，避免长页超出普通 TEXT 容量。这里没有向量字段。

空白页保留，整份文档完全没有文本则拒绝入库并提示 OCR；损坏文件不会导致整个批次停止。当前不支持并发导入同一文件，统一由 C 顺序导入；唯一主键防重复，并发竞争可能返回失败，重跑即可跳过已写版本。

### 运行

```sh
source .venv/bin/activate
# 从仓库根目录启动独立本地 MySQL（第一次需要下载镜像）
docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait
python -m rag.ingest --input data/raw/part3-demo
# 再运行一次，应显示 skipped
python -m rag.ingest --input data/raw/part3-demo
```

本机 MySQL 使用 127.0.0.1:13306，库 groupchat；本机生成的随机密码只存在被 Git 忽略的根目录 .env，未写入报告。C 的批处理用同步 PyMySQL，A 的 Web 可用 asyncmy，共享 DATABASE_URL 时由 get_engine 转换驱动名。

移交给队友时只交 .env.example；队友自己填写数据库连接。compose 的 LAB9_MYSQL_PASSWORD 要与 DATABASE_URL 中密码一致，本地端口为 13306。已初始化数据卷不会因修改 .env 自动改变数据库密码。

暂时不用时可以执行 `docker compose --env-file .env -f infra/compose.mysql.yml stop`，保留数据卷；不要使用 down -v 删除原文。

### 本次结果与边界

MySQL 8.4.13；2 份 PDF、130 页原文已入库。首次 inserted，重复导入 skipped；每页从数据库读回的文字与提取结果一致。7 个测试通过，包括中文、空白页、拒绝空文档、内容版本和事务回滚。

Ads cookbook 的 124 页中有特殊字体解析警告（见 evidence/c-step2/pdf-warnings.log），所以读回一致仅证明存储没有改变提取结果，不代表全部 PDF 字形都提取准确；后续正式建库前需处理字体/核对文本。本次 6 页实验要求 PDF 可用于继续学习。主题语料尚未确定；两份材料只是流程验证资料。

第 1 课的网页仍只做预览；本课通过独立命令行完成课程要求的文件夹入库。下一课从数据库读原文，使用 CharacterTextSplitter 切块，不直接重新读取 PDF。当前尚未实现切块、embedding 和检索。

**复述任务：为什么把“一份文档记录＋它的所有页”放在同一个事务中？重新导入同一文件为什么不会出现第二套重复记录？**

## 第 3 课：从数据库原文到 chunks.jsonl（已展开）

依据 PDF p.4 Part 3-II.2：CharacterTextSplitter、size=500。重叠 100、按换行切、逐页保留出处是本项目实施选择；这里长度指 Python len 的字符数，不是 token 数，也不是英文单词数。

主链：`python -m rag.chunking --document-id ...` → build_chunks 读 MySQL → split_page 切文本 → Chunk 结构 → JSONL 和 manifest。

### 代码阅读顺序

1. `rag/chunking.py::main`：显式指定已入库的文档版本 ID，防止把旧版本或其他资料意外混进知识库。默认输出来自 config 的 paths.chunks。
2. `build_chunks`：查询 rag_documents，再按 ordinal 读取 rag_document_pages。每页单独切，保留单一页码；不跨页 overlap。校验实际页数和文档页数一致。
3. `split_page`：构造 CharacterTextSplitter，执行 split_text(text) 得到 list[str]。keep_separator=True 和 strip_whitespace=False 保留正文中的换行与空白；过滤全空白结果。
4. 超长块分支：如果某一行本身超过 500，换行分割不能继续拆开它，改用 separator="" 的 CharacterTextSplitter；它按单字符合并为不超过 500 的块。常规换行分割的 overlap 是目标上限，不保证恰好 100；逐页边界无重叠。
5. `build_chunks` 将每段正文封装成 shared.contracts.Chunk，保留 source/page。chunk_id 是文档版本、页序号、块序号、切块配置/版本和正文的哈希；输入和策略相同则 ID 稳定，规则变化则 ID 改变。
6. `main` 用 asdict 转成 JSON，一行一个 chunk。manifest 记录来源文档版本、配置、splitter 版本、长度统计和输出哈希。已有同名文件且内容不同则拒绝覆盖，要求新输出路径。

### 核心调用

```python
splitter = CharacterTextSplitter(
    separator="\n",
    chunk_size=500,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
    keep_separator=True,
    strip_whitespace=False,
)
parts = splitter.split_text(text)
```

输出 parts 是字符串列表；尚没有 embedding 或模型请求。当前为保留原文，不额外做去页眉、清洗或 OCR；这些不能和切块混为一项已完成工作。

### 运行与结果

```sh
python -m rag.chunking --document-id c242899735a82fe8f7b23b8061ad43d30f98db0c2ed64f017149768e85c459cf
```

此次只选择无已知字体警告的实验要求 PDF：6 页 → 26 个 chunk，长度 205–499。4 项切块测试通过；真实输出检查了 ID 唯一、Chunk 格式兼容、来源/页码正确、每块可定位到原文，以及全部非空白原文覆盖。重复运行输出完全一致，状态 unchanged。

结果：data/processed/chunks.jsonl 和 chunks.manifest.json；验证：evidence/c-step3。资料只供 Part 3 学习/接口联调，不能当作 Part 4 正式主题知识库。原 Cookbook 字体警告尚待后续处理，不混入这次导出。

可先把这份 JSONL 和 manifest 交给 B 联调算法，A 的 retrieve 仍未实现。下一课才做 OpenAI embedding；需要配置实际可用模型与 API key。

**读代码时重点看：split_text 返回的字符串，怎样被装进带 source/page 的 Chunk？后面向量库命中 chunk_id 后，就靠这份映射取回正文和出处。**

## 第 4 课：OpenAI embedding 与 FAISS（已展开，真实建库完成）

依据 PDF p.4 Part 3-II.3：用 OpenAI embeddings 处理 chunks，保存到向量库。当前没有 OpenAI API key，未发起真实请求；6 项合成向量离线测试通过，不代表正式实验已完成。

调用主链：`python -m rag.vectorstore` → 读取 chunks.jsonl → build_store → embed_texts → make_index → 写入索引、正文映射和 manifest。

### 1. 文本交给模型

阅读 `rag/embeddings.py::embed_texts`：

```python
response = client.embeddings.create(
    model=model,
    input=batch,
    encoding_format="float",
)
```

batch 是最多 32 个 chunk 的 text 字符串。模型负责计算向量；本地代码并没有自己实现神经网络。按返回的 index 排序，保证向量第 i 行仍对应输入第 i 个 chunk，再转 float32 矩阵；校验数量、维度、非零和有限数值。返回矩阵和 API 报告的 token 用量。

默认建议模型 text-embedding-3-small；模型名和 key 来自根目录 .env。正式客户端明确连接 OpenAI 官方地址；第三方兼容接口不自动等同于课程要求。文档和后续问题必须使用同一模型。

### 2. 向量存入 FAISS

阅读 `rag/vectorstore.py::make_index`：

```python
faiss.normalize_L2(vectors)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)
```

vectors 是 n×d：n 为 chunk 数量，d 为接口实际返回的向量维度。先做 L2 归一化，再用内积索引，后续查询向量也需归一化，此时内积就是余弦相似度。IndexFlatIP 是精确检索，不需要训练索引。FAISS 是本地向量检索库，不是独立数据库服务器；本实验将它与 JSONL 原文映射组合成持久化向量存储，沿用课程示例的 FAISS 选择。

### 3. 保持向量与文字对应

build_store 保存三个文件到 artifacts/indexes/openai：

- index.faiss：按 chunk 顺序保存的向量。
- chunks.jsonl：同顺序的 chunk_id、text、source、page。
- manifest.json：模型、维度、数量、输入和索引哈希、token 用量、创建时间。

搜索命中第 i 个向量时，就取 chunks[i] 的原文。load_store 校验哈希、数量和维度，避免向量与文字错配。已有同模型/同内容索引则重用，避免重复请求；内容或模型变更时拒绝覆盖，使用新 --output 目录。临时目录验证成功后才发布最终索引。

### 配置和运行

在根目录 .env 本地填写，不把 key 发到聊天或提交 Git：

```dotenv
OPENAI_API_KEY=<你们组可用的官方 API key>
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

```sh
source .venv/bin/activate
python -m rag.vectorstore
```

该命令会把 chunk 正文发送给 OpenAI，按实际 API 用量计费；当前使用课程要求 PDF 作为流程样例。Key 的来源/账号由全组确认，课程 PDF 未提供 key。现阶段无需填写 OPENAI_CHAT_MODEL，它用于后面的回答链。

本课证据：evidence/c-step4/offline-tests.txt（合成向量离线测试）。2026-10-28 已用真实 key 运行：26 块、text-embedding-3-small、1536 维、2835 tokens；再次运行显示 unchanged，不重复请求（evidence/c-step6）。

**读代码重点：模型返回的 embedding 列表如何转成矩阵，第 i 个向量如何与第 i 个 chunk 对齐？**

## 第 5 课：检索、带记忆的问答和命令行（已展开）

依据 PDF p.4 Part 3-II.4（对话链和记忆）与 III（driver、exit、只依据最相关的上下文回答）。真实运行记录：evidence/c-step6、evidence/c-step7。

调用主链：`python -m rag.cli` → build_store（已有则复用）→ VectorStore → create_conversation_chain → repl 循环 → chain.ask。

### 1. 检索：`rag/retrieval.py::VectorStore.search`

输入问题和 k，输出 k 个 SearchHit（chunk + 分数）。

```python
query, _ = embed_texts([question], self.manifest['model'], client=self.client)
faiss.normalize_L2(query)
scores, rows = self.index.search(query, min(k, self.index.ntotal))
```

问题必须用建库时的同一个模型（从 manifest 读取），否则向量不在同一空间。归一化后的内积就是余弦相似度；rows 是命中的向量行号，取 chunks[row] 就拿回原文、来源和页码。对应 PDF Summary 的 e、f。

### 2. 对话链：`rag/chain.py::ConversationChain.ask`

输入问题和 session_id，输出 ChainResult（answer、standalone_question、hits）。每一轮：

1. 有历史时，先让 LLM 把追问改写成完整问题，例如 "that vector" → "the K-dimensional histogram vector"。不改写的话，检索只能拿 "that vector" 去搜。
2. 用完整问题检索 top-4。
3. 把编号段落和问题发给 LLM。system prompt 要求只依据段落回答、标注 [1] 这样的来源、找不到就说文档没有覆盖。对应 Summary 的 g、h。
4. 成功后把原问题和答案写进这个 session 的 BufferMemory。

BufferMemory 起的就是 ConversationBufferMemory 的作用：完整保存一个会话的全部消息。LangChain 的这类记忆类已经弃用（运行时会出现 deprecation 警告），所以用一个列表自己实现。不同 session_id 互不影响，A 的网站可以按用户区分会话。

### 3. 命令行：`rag/cli.py::repl`

循环读问题：输入 exit 退出，空行跳过；某一轮出错只打印错误、程序不退出，这一轮也不写进记忆。每轮打印改写后的问题（如果有）、答案和检索到的 4 段（分数、页码、chunk ID 前 12 位）。加 `--input 文件夹` 时会先依次调用第 2、3、4 课的入库、切块和建库，对应 PDF 的 "driver function that calls the above functions"。

### 运行与结果

```sh
source .venv/bin/activate
python -m rag.cli
```

真实 5 轮问答（evidence/c-step7/cli-transcript.txt）：连续两次追问都被正确改写；无关问题的检索分数只有 0.06 左右，模型回答文档没有覆盖；中文问题用中文回答。对话模型 gpt-6-luna 不接受 temperature=0，所以 OpenAIChat 不传 temperature。

**读代码重点：追问为什么要先改写再检索？改写后的问题和原问题分别保存在哪里？**
