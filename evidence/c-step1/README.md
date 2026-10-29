# C 第一步验证记录

时间：2026-10-28T17:23:58.033147-07:00
基线 commit：6ba2ae8；本次为未提交变更。
Python：3.12.13；依赖：rag/requirements.txt。
输入：lab9-f26.pdf，SHA-256 867bc2f8eebf2d35f4884c644c0f9755a070f591512677c53521958e981aff4c。

运行：`python -m unittest discover -s tests -v`（退出码 0）；PdfReader 真实文档检查与 Streamlit AppTest（退出码 0），结果见 checks.txt。
AppTest 注入文件对象验证的是页面处理/渲染，不是浏览器上传端到端测试。
页面已在 127.0.0.1:8501 启动。
未验证数据库、embedding、检索、模型回答或正式主题数据。
