# 第 5 步：OpenAI 连通性检查

2026-10-28 PDT，Wenxu 本机。账号预付 $5，自动充值关闭。脚本为同目录 `check_openai.py`（不输出 key），从仓库根目录以 `PYTHONPATH=. .venv/bin/python evidence/c-step5/check_openai.py <stage>` 运行。

| stage | 结果 |
|---|---|
| models | key 有效；可用 128 个模型，embedding 有 text-embedding-3-small/-3-large/ada-002 |
| embed | text-embedding-3-small，单条测试文本，1536 维，5 tokens |
| chat | gpt-6-luna 可用 Chat Completions；回复 "OK"，11 输入 / 4 输出 tokens |

注意：gpt-6-luna 不接受 temperature=0（400，只支持默认值 1），对话链不要传 temperature。
模型选择依据：PDF Part 3 只要求 OpenAI，未指定型号；按成本选用 gpt-6-luna（$0.10/$0.50 每 1M token，2026-10-28 核对 OpenAI 价格页）。
只是连通性检查，未建正式索引，未发送课程 PDF 内容。
