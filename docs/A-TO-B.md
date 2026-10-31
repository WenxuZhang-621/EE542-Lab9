# A 给 B 的交接说明

截至 2026-10-31：A 的网站、MySQL、本地 GPU Llama、真实 OpenAI embedding 和带来源的两轮问答已在本机运行。公网 HTTPS 已部署并通过真实两轮 RAG 与双客户端 WSS 测试；Android TWA 签名绑定尚未完成。

最终网站地址：**https://desktop-jdferfe.taile24d30.ts.net/**

B 现在可以将这个地址填入 `defaultUrl`，普通浏览器访问不需要安装 Tailscale。注册需要组内邀请码，由 A 单独私发；已有账号登录不需要邀请码。A 的电脑和服务必须保持运行。部署及停止说明见 `A-PUBLIC-DEPLOYMENT.md`。

## A 给 B 什么

**主要交付是可访问的 HTTPS 网站地址。** 最终地址确定后，B 填入 `android/app/src/main/res/values/strings.xml` 的 `defaultUrl`。地址不是 Llama 的 8001 端口。

当前 `http://127.0.0.1:8000/` 只在运行网站的电脑上可用。B 在自己电脑或手机输入这个地址，会访问 B 自己的设备，不会访问 A 的电脑。Android 模拟器的 `10.0.2.2` 只代表该模拟器所在电脑的宿主机，也不能自动访问 A 的另一台电脑。

辅助资料：A 代码包 `EE542-Lab9-Part-A.zip`、其中的 `part-a.patch`、本文件、`DEPLOY-A.md` 和 `A-HANDOFF.md`。包内 `android/` 仍是原有模板，不能覆盖 B 已经完成的 Android 改动。优先在 B 自己的分支用 `git apply --check` 检查后合并 A 的 patch。

## B 给 A 什么

截图交接表最后一行 B → A 所需内容：

1. 实际 `applicationId`，来自 B 的 `android/app/build.gradle`。
2. 实际安装 APK 使用的签名证书 SHA-256 指纹，32 个十六进制字节，通常以冒号分隔。debug 和 release 证书可能不同。
3. 相应的 `assetlinks.json` 配置；也可以先给前两项，由 A 已有的 `scripts.assetlinks` 生成。

A 把 JSON 放在最终网站的 `/.well-known/assetlinks.json`。B 将同一网站地址写入 App，安装签名 APK，双方检查能否无地址栏打开、登录、提问和查看来源。

**A 可以先部署网站并给 B 地址，不必等待 B 的签名信息。** 签名信息用于最终 App 与域名的绑定。

## B 的 Part 5 数据

这些由 C 提供，代码包已包含副本：

- `data/topic/index/chunks.jsonl`：同一套 1694 个文本块，保留 chunk ID。
- `data/topic/questions.jsonl`：32 题固定评估集。
- `data/topic/baseline_openai.json`：C 的 OpenAI 检索基线。
- `shared/contracts.py`、`docs/interfaces.md`、`data/topic/README.md`：格式、接口和评价约定。

B 应实现自己的 Word2Vec、聚类、质心、K 维归一化直方图及改进对比。A 新增的 `evidence/a/evaluation.json` 是网站回答链路的运行记录，不能替代 B 的 embedding 对比实验，也不等于问答正确率。

## 不需要互传

API key、完整 `.env`、JWT secret、数据库密码、模型认证 key、Android keystore 私钥和 keystore 密码均不需要发给 B。B 只连接已经运行的网站时不需要 A 的 OpenAI key。公开的包名和证书指纹可以共享。

## 可直接转发的消息

“A 的网站已部署：https://desktop-jdferfe.taile24d30.ts.net/ ，请填入 Android defaultUrl。我单独发你注册邀请码，你可先用浏览器注册并测试；访问不需要 Tailscale。A 的代码包是辅助资料，请保留你已有的 Android 改动，优先检查并合并 part-a.patch。你确定 Android applicationId 和实际签名 APK 后，把包名及证书 SHA-256 指纹发我，我来部署 assetlinks.json，然后一起测无地址栏启动、登录、问答和来源。Part 5 继续用 C 给的同一套 chunks、32 题和 OpenAI 基线。密钥和签名私钥不用互传。”
