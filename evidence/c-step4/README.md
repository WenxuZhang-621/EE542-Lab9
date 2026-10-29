# 第 4 步离线验证

2026-10-28：仅离线测试，退出码 0。命令：python -m unittest discover -s tests -p test_vectorstore.py -v。
使用 mock API 返回值和小型合成向量，未调用 OpenAI；测试目录自动清理，未发布正式索引。
覆盖响应顺序/分批、错误响应索引、归一化余弦排序、保存重载和映射、重复构建、模型变更拒绝、损坏检测、API 失败不发布、零向量拒绝。
真实 key/模型配置与语义检索质量待验证。SDK 与库版本见 rag/requirements.txt。
