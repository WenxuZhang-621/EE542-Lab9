# 第 10 步：上传页接入与测试

2026-10-28 PDT。

| 文件 | 内容 |
|---|---|
| process-uploads.txt | `process_uploads()` 真实运行：2 个网页 + 实验 PDF 存入 MySQL（已存在则 skipped），.docx 显示为失败行；38 块建索引后问 ITIN，回答 Form W-7，来源均为 sits-itin.html |
| browser-processed.jpg、browser-answer.jpg | 浏览器 127.0.0.1:8501：通过页面的文件输入框提交一个 Markdown 测试文件（用脚本把文件放进 input，等同选择文件），点 Process documents 后显示入库、1 块、1536 维索引；提问后得到正确答案和来源 |
| tests.txt | `LAB9_TEST_MYSQL=1 python -m unittest discover -s tests -v`：39 个测试全部通过（含 3 个 MySQL 测试、3 个 Streamlit AppTest） |

浏览器测试留下了一条测试文档 browser-upload-test.md（MySQL）和 artifacts/indexes/upload-* 索引，均不进 Git。
