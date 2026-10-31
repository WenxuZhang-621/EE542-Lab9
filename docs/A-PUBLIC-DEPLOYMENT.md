# A 公网部署交付（2026-10-31）

网站：**https://desktop-jdferfe.taile24d30.ts.net/**

该地址已经通过 Tailscale Funnel 发布，访问者不需要安装 Tailscale。网站在 A 的 Windows 电脑运行；电脑关机、休眠、断网或本地服务停止时，公网网站也会离线。这不是独立的全天候云服务器。设备及 tailnet 名称不变时保留此域名，不要在 B 完成绑定后随意改名。

## 已验收

- 正式证书 HTTPS，验证证书和域名，未跳过 TLS 检查。
- 使用公共 DNS-over-HTTPS 查询到的公网 Funnel 地址直接连接，排除本机 Tailscale 内网解析带来的误判。
- 两个账号注册、登录，两个 WSS 客户端接收同一消息及助手 loading/done 事件。
- 两轮真实问答：Form 8843 的用途、追问该表要求学生提供哪些信息；使用真实 OpenAI embedding、C 的检索索引、本地 Llama 和 MySQL。
- 来源写入数据库后回读一致；公网浏览器登录、刷新、来源与原文展开正常。
- 无邀请码注册返回 403，未登录读取聊天返回 401。
- `/.well-known/assetlinks.json` 返回 JSON；仍是模板内容，**尚未验证 B 的签名 APK**。
- 66 项自动化测试与 5 项子测试通过。运行证据见 `evidence/a/public-https-smoke.json`、`public-https-login.png`、`public-https-sources.png`。

验证脚本会创建 QA 账号与聊天消息，并调用两次真实 RAG，产生少量 embedding 使用量。从配置了自己 `.env` 的源码目录执行：

```powershell
python -m scripts.smoke_public --base-url https://desktop-jdferfe.taile24d30.ts.net
```

脚本只接受与本地 `PUBLIC_ORIGIN` 完全一致的地址，避免把本地邀请码误发到其他服务器。只读健康检查：网站 `/api/health`。

## 当前部署配置

官方签名 Tailscale 1.104.4 已安装并登录个人账户；Windows IP Helper 已从禁用改为手动并启动。最初的 0x80070643 安装失败来自该前置服务被禁用，启用后重新安装成功。

仅代理 `http://127.0.0.1:8000`，TLS 由 Tailscale 处理；数据库 13409 和模型 8001 继续只供本机使用。网站只有一个 Uvicorn worker。

```powershell
& 'C:/Program Files/Tailscale/tailscale.exe' funnel --bg http://127.0.0.1:8000
& 'C:/Program Files/Tailscale/tailscale.exe' funnel status
```

此电脑的命令可能需要管理员权限。`--bg` 的 Funnel 配置会保留；重启电脑后仍需使用本机 `Start-Lab9.cmd` 启动数据库、模型和网站。无需反复开通 Funnel。

仅关闭此网站的公网转发：

```powershell
& 'C:/Program Files/Tailscale/tailscale.exe' funnel --https=443 off
```

不要使用 `funnel reset` 清除可能属于其他应用的配置。重新公开时执行前面的 `funnel --bg` 命令。没有创建其他端口转发。

## 组内访问与使用限制

本机 `.env` 已设置 `PUBLIC_MODE=true`、随机 `REGISTRATION_CODE`、准确的 `PUBLIC_ORIGIN`。邀请码由 A 私下发给组员；不进入 Git、代码包、日志或公开前端配置。创建自己的账号时填写邀请码，已有账号登录不需要再填。

公开模式限制：每分钟全站 60 次注册/登录、每个用户名 10 次；每分钟全站 120 条消息、每账号 30 条；每账号每分钟 6 次助手请求、全站每小时 60 次助手请求，同时只处理 1 个助手请求。重试也计入额度。被拒绝的请求在保存聊天或调用模型前返回 429，页面保留输入草稿。

限制在单个进程的内存中，网站重启会重置。它适用于本次单机小组演示；多 worker 或多服务器部署需要共享的限流状态。不要通过增加 worker 直接扩容。邀请码轮换只影响新注册，不注销已有账号；群聊对已登录成员可见，历史中保留开发 QA 消息及当时的错误记录。

## 交给 B

B 将 `defaultUrl` 设为 `https://desktop-jdferfe.taile24d30.ts.net/`，获得组内邀请码后可自行注册测试。B 返回实际 `applicationId` 与安装 APK 所用证书 SHA-256，A 再用 `scripts.assetlinks` 生成和部署关联文件，然后一起验证 TWA 无地址栏启动。

详细交接见 `A-TO-B.md`。该公网部署不代表 Android APK、Part 5 自定义 embedding、团队手机录像、GitHub 提交或最终 PDF 已完成。
