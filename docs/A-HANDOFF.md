# A：网站与系统集成交接

本次实现基于 `9e1a0df4e7e9a25c36b086842b11e54e73d1bcf2`。范围为 A（Part 1 + Part 4 网站端），B 的 Android 和自定义 embedding 交由另一位组员完成。

## 已实现

- 注册/登录、带认证的 WebSocket 群聊、普通消息与助手提问切换；中文/英文问号均可触发助手。
- `ask_llm()` → `answer_with_sources()` → 在线程中调用 C 的 `rag.api.retrieve()` → 自托管 Llama 的 OpenAI-compatible `/v1/chat/completions`。
- A 的上下文组装保留 C 的 500 字符索引和检索接口，补充命中片段前后各一个同文档、同页片段，避免关键句被截断。问题明确指定表格和类别时，最多一半来源优先使用该表格中类别一致的 Part 标题（例如 Students），其余保留向量检索排序。每个来源保存原始命中 ID 和 `context_chunk_ids`。
- 追问先用 Llama 改写为独立问题；记忆按用户 ID + 浏览器会话 UUID 隔离，最多保留 3 轮、256 个会话，闲置一小时后清理。历史聊天在 MySQL，模型记忆仅在当前进程，重启会清空。
- 提示模型只按检索上下文回答、标注 `[1]` 等编号、说明资料冲突；无支持资料时不猜测。检查引用编号是否存在。模型有合法引用不等于事实必然正确，录制时仍需人工对照原文。
- 来源标题、机构、链接、页码、chunk ID 和原文随回答写入 `message_details`，刷新后仍能查看。保留原始 `users/messages` 表，无需删除旧数据。
- 网页加载状态、断线重连、失败消息和原问题重试；退出登录后关闭 WebSocket。
- 手机页面、PWA manifest/图标、仅缓存公开静态文件的 service worker；`/.well-known/assetlinks.json` 路由及与 B 对接的生成/检查工具。
- MySQL + FastAPI + 可选 Llama + 可选 Caddy HTTPS 的 Docker Compose；Windows 本地启动脚本；环境检查脚本和 CI 配置。

## 实际验证范围

本机运行了 MySQL Community Server 8.4.13 和 FastAPI，浏览器验证了注册、登录、发消息、失败提示和 390 像素手机布局。测试记录见 `evidence/a/`。

自动化测试共 66 项通过，另有 5 个子测试，包含真实 MySQL 存储和受控检索/模型替身的接入、广播、记忆隔离及错误处理测试。早期 `source-card-fixture.png` 来自明确写有 **UI TEST FIXTURE** 的隔离测试服务；新增 `live-web-answer.png` 和 `live-web-smoke.json` 才是实际服务的问答证据。

2026-10-31 已在本机启动 llama.cpp b12023 官方 Windows CUDA 13.4 预编译版本，加载 Meta-Llama-3.1-8B-Instruct-Q4_K_M（约 4.92 GB），并在 RTX 5070 Ti 上验证真实生成回复。模型与运行文件的 SHA-256 均按发布方元数据校验。模型端点绑定 127.0.0.1:8001，使用随机本地密钥，网页端口为 8000；本机 MySQL 端口为 13409。

同日还完成了讲义中的源码构建：检出 llama.cpp b12023 / `f3586e66bc916d672773d4a6505513ba91a3595c`，用 LLVM-MinGW Clang 23.1.4、CMake 4.4.4 和 Ninja 1.13.2 编译 CPU 版 `llama-server`。在独立的本机 8011 端口加载同一个 8B 模型并得到真实回复，随后停止该验证进程。网站继续使用 8001 上的 GPU 版本；这两项证据分别记录，不能把 CPU 源码构建称为 CUDA 源码构建。复现脚本为 `scripts/build_llama_cpu.ps1`。

2026-10-31 已通过官方连接器创建用户确认的 key（Personal / Default project，有效期 30 天），仅保存到本机忽略的 `.env`。账户额度恢复后，真实 `text-embedding-3-small` 请求成功返回 1536 维向量；`scripts.check_setup --live` 和 `scripts.smoke_web_live` 均通过。完整链路为真实 OpenAI 查询向量 → C 的 FAISS 检索 → A 的上下文组装 → 本地 Llama 3.1 8B → HTTP/WebSocket → MySQL。两轮问题为 Form 8843 的用途，以及“that form”要求学生提供的信息；已核对表格主题、学生部分、引用、加载/完成广播和来源回读。网页刷新后仍可展开原文。

实测曾发现 500 字符片段截断、JSON 格式历史导致追问语言/主题偏移，以及教师段落挤掉学生段落的问题。对应修复为相邻上下文、使用原生对话角色且只替换指代的追问提示、明确表格与类别的章节匹配；相关回归测试已加入。小模型回答仍需人工对照原文，两轮演示通过不代表整个知识库的事实正确率已验证。现已扩展到 32 题真实评估，32/32 返回有引用的答案，30/32 覆盖标注原文，但人工检查仍发现生成和资料冲突问题，详见 `A-EVALUATION.md`。网站仍保留额度耗尽时的明确提示和重试入口。

公网 HTTPS 已在 https://desktop-jdferfe.taile24d30.ts.net/ 部署并实测，详见 `A-PUBLIC-DEPLOYMENT.md`；签名 APK 待 B 提供。最终 TWA 域名关联需要 B 的包名和证书指纹。交付代码包不含 `.env`、数据库、模型或任何真实 key，组员须使用各自获授权的本地配置。

## 给 C 的兼容性说明

C 的检索函数签名、语料和 FAISS 索引内容不变。只对 `rag/vectorstore.py` 做两个 Windows 修复：读 chunks 明确 UTF-8；写 chunks 固定 LF，确保实际文件字节与 SHA-256 一致。新增 `.gitattributes` 防止 Git 把已校验的 JSONL 改成 CRLF。若旧工作目录仍有 CRLF，先保存本地改动，再从当前分支重新检出该文件；不要随意更改 manifest 来绕过校验。

## 给 B 的接口

1. 开发阶段可以用网站所在电脑的局域网地址测试浏览器页面；Android 模拟器访问宿主机一般用 `http://10.0.2.2:8000`，真机使用电脑的 LAN 地址。服务需绑定 `0.0.0.0`，网络和防火墙需允许访问。
2. 正式 TWA 的 `defaultUrl` 必须是最终 **HTTPS 网站地址**，不是 8001 模型端口。HTTP 本地访问不等于通过 TWA 域名验证。
3. B 提供实际 `applicationId` 和安装 APK 所用证书的 SHA-256 指纹；指纹是公开值，私钥留在 B 的电脑。
4. A 执行 `python -m scripts.assetlinks --package 实际包名 --fingerprint 实际指纹`，部署生成的 JSON。
5. A 执行 `python -m scripts.assetlinks --package 实际包名 --fingerprint 实际指纹 --check-url https://实际域名`。B 重新安装签名 APK，检查登录、提问、来源外链及无地址栏启动。

当前仓库保留模板 assetlinks 的占位值，不能声称已完成域名关联。不要擅自填写与 B 不一致的包名或指纹。

## 录制 A 的视频时需要讲解

| 展示 | 讲解要点 |
|---|---|
| 两个浏览器登录并互发消息 | MySQL 保存消息；认证后的 WebSocket 同步广播；普通消息不调用模型 |
| 提问并展开来源 | `ask_llm()` 如何调用 C 的检索；为何使用后台线程；上下文如何加入 Llama 请求 |
| 显示原文与回答引用 | 来源的 chunk ID、页码、网址如何映射；刷新后仍存在 |
| 连续追问，再换用户提问 | 同一会话保留上下文，不同用户隔离；群聊消息本身是全组可见的 |
| 暂停模型服务，再恢复并重试 | 加载/失败状态与原问题重试；不要把服务错误包装成知识答案 |
| 手机浏览器、与 B 联调 | 布局、HTTPS、Asset Links；最终 TWA 验证由 A/B 一起完成 |

上述是演示提纲，不是虚构的个人工作日志。按老师要求，用手机拍摄你本人实际工作、问题和修复过程。完成真实联调后再录最终问答视频。

## 合并与提交

A 的改动通过独立分支和 Pull Request 交接，合并前检查与 B、C 最新工作的兼容性。使用离线代码包时，先对 `part-a.patch` 执行 `git apply --check`。贡献日志应对应成员实际负责和检查的工作。

可按实际工作分成后端接入、前端交互、部署与测试几个清晰提交。老师要求最终 PDF 带 YouTube 链接和 GitHub 日志，真实视频和提交链接确定后再填写；此时没有伪造最终提交材料。
