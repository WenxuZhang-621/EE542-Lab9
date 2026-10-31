# A 的验证记录

基于 `9e1a0df4e7e9a25c36b086842b11e54e73d1bcf2`，Windows / Python 3.12.14 / MySQL Community Server 8.4.13。

| 文件 | 说明 |
|---|---|
| `tests.txt` | 66 个测试通过，另有 5 个子测试；包含真实 MySQL 存储、A 的自动化测试、额度不足处理、断句上下文和正确表格章节匹配 |
| `mysql-web-smoke.txt` | 运行中的 FastAPI + MySQL：创建随机 QA 账号、登录、双向 WebSocket 广播、历史回读；没有调用 LLM |
| `preflight.txt` | 最新环境检查；索引完整性、JWT、真实 MySQL 连接与 Llama 连通性通过，OpenAI key 已配置；该检查不验证 API 账户额度 |
| `local-llama-live.json` | 本机 RTX 5070 Ti 上的真实 Llama 回复及耗时；该单项测试仅验证官方预编译 CUDA 模型服务 |
| `llama-source-configure.txt` / `llama-source-build.txt` | 固定 b12023 源码的本机 CPU 编译日志，227 个构建步骤完成，使用 LLVM-MinGW / CMake / Ninja |
| `source-llama-live.json` | 源码编译的 CPU 服务器加载同一个 8B 模型后实际生成回复；记录 commit、编译器和耗时，不包含 OpenAI 检索 |
| `openai-embedding-check.json` | 使用本机已配置 key 发出的真实 OpenAI embedding 请求成功，模型 text-embedding-3-small，1536 维 |
| `live-preflight.txt` | 完整真实 RAG 环境检查、生成答案、来源及引用状态 |
| `live-web-smoke.json` | 真实 MySQL + FastAPI + OpenAI embedding + 本地 Llama 的两轮问答；含主题与学生字段检查、加载/完成广播、来源持久化回读 |
| `live-web-answer.png` | 本机生产服务实际两轮问答的浏览器截图；刷新后回答及来源仍保留，不是 fixture |
| `compose-validation.txt` | 官方 Docker Compose v5.6.1 对 web/MySQL/Llama/HTTPS 所有 profile 的配置解析通过；不等于容器已运行 |
| `mobile-error-state.png` | 390×844 viewport 下的实际页面，缺 OpenAI key 时展示检索失败；DOM 检查无横向溢出 |
| `source-card-fixture.png` | 隔离 SQLite UI 测试服务中的模拟回答，明确标注 UI TEST FIXTURE；验证来源链接、页码、引用编号及原文展开，不是模型回答证据 |

浏览器还验证了刷新后仍有来源、退出登录返回登录页。浏览器控制台未观察到 JS error/warn。生产页面不包含测试回答逻辑；fixture 只在 `python -m tests.browser_fixture` 启动的 8002 端口运行。

2026-10-31 完整本地 RAG 链路及两轮追问已验证，回答引用的学生部分已人工与显示的原文核对。测试覆盖有限，不代表模型对所有问题都正确。旧 fixture 和失败截图保留作为状态处理记录，不是当前真实服务的运行状态。公网 HTTPS 现已部署并实测；Android TWA 仍待 B 的签名资料，见 `docs/A-PUBLIC-DEPLOYMENT.md`。

此目录是工程 QA 证据，不能代替老师要求的手机拍摄团队工作视频。个人工作日志与 Git 贡献应依据成员实际工作记录填写。

补充本地验收：`evaluation.json` 保存 32 题的真实生成结果、来源和覆盖指标；人工复核及局限见 `docs/A-EVALUATION.md`。`embedding-trace.json` 展示真实 1536 维查询/文档向量样本和相似度。`mobile-live-sources.png` 与 `mobile-live-check.json` 验证 390×844 下真实来源展开且无横向溢出。

公网补充：`public-https-smoke.json` 记录通过公网 Funnel 地址的 HTTPS、双客户端 WSS、真实两轮问答及来源回读。`public-https-login.png` 为邀请码登录页，`public-https-sources.png` 为刷新后展开原文的浏览器证据；`funnel-status.json` 表明仅 443 代理本机 8000。
