# Part 3-II.1 原文入库证据

记录时间：2026-10-28T17:33:41.468285-07:00
基线：6ba2ae8 + 本次未提交源码。配置：独立 Docker MySQL 8.4，127.0.0.1:13306，groupchat。
输入哈希、来源、页数见 import-first.jsonl；原文件保留，data/raw/part3-demo 为副本。

命令及退出码：
- python -m rag.ingest --input data/raw/part3-demo：首次和重复均 0，分别见 import-first.jsonl / import-repeat.jsonl。
- LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v：0，7 个测试通过，见 tests.txt。
- PYTHONPATH=. python evidence/c-step2/verify_readback.py：0，全部页原文一致，见 readback.txt。

pdf-warnings.log 保存特殊字体解析警告；尚未确认 Ads cookbook 全文字形准确性。没有用模拟数据库替代 MySQL；没有进行 embedding 或 LLM 调用。
数据库目前保持运行，Docker named volume 保留数据；只绑定本机端口，无公网部署。
