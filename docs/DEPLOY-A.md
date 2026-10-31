# A：Llama、HTTPS 与 Android 对接部署

## 1. 自托管 Llama（本机）

网站使用 OpenAI-compatible Chat Completions，但生成回答必须指向你自己的 Llama 服务。OpenAI key 只交给 C 的 embedding 检索接口，**不会发给 Llama 服务**。

按老师要求准备合法取得并接受相应许可的 Llama 3 Instruct GGUF 模型。建议按课程配置选择 8B 及适合本机的量化版本；模型不是交付包的一部分。不要把模型权重或密钥提交 Git。

源码构建（安装 Git、CMake、C++ 编译器；Windows 使用 Visual Studio C++ Build Tools）：

```sh
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --target llama-server -j 4
```

记录实际 `git rev-parse HEAD`、编译命令、模型文件名/量化、硬件和启动日志，方便视频复现。上游持续变化，以其 [build.md](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) 为准。

Linux/macOS 通常使用 `build/bin/llama-server`；Windows 多配置构建通常使用 `build/bin/Release/llama-server.exe`：

```sh
llama-server -m /absolute/path/to/model.gguf --host 127.0.0.1 --port 8001 --ctx-size 4096 --alias llama-3-8b-instruct -ngl 0
```

Windows 可使用 `scripts/start_llama.ps1 -ServerPath 实际exe路径 -ModelPath 实际GGUF路径`。默认 CPU；GPU 使用相应 CUDA/Metal 构建，并按硬件设置 GPU layers。不要直接把模型服务端口开放到公网。

### 本机已验证的 Windows 源码构建

已使用 [LLVM-MinGW 20261020](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261020) 的 `llvm-mingw-20261020-ucrt-x86_64.zip`、CMake 4.4.4、Ninja 1.13.2 完成 CPU 构建。工具链压缩包 SHA-256：`fd5462b7f5d93b2ff981fcd3f9c7e427e47f3203c64ea91c27bcc444eebd74cd`。源代码固定在 b12023，commit 为 `f3586e66bc916d672773d4a6505513ba91a3595c`。

新环境复现时，下载并解压上述工具链，然后从 Lab9 仓库根目录执行：

```powershell
python -m pip install cmake==4.4.4 ninja==1.13.2
git -c core.longpaths=true clone --depth 1 --branch b12023 https://github.com/ggml-org/llama.cpp.git ../llama-cpp-source
powershell -ExecutionPolicy Bypass -File scripts/build_llama_cpu.ps1 -SourcePath ../llama-cpp-source -CompilerBin C:/path/to/llvm-mingw-20261020-ucrt-x86_64/bin
```

在激活 Python 虚拟环境后运行，或通过脚本的 `-CMakePath` / `-NinjaPath` 显式指定可执行文件。源码目录已存在时不要重复 clone。脚本编译 Release CPU 服务器，复制所需的编译器运行库到 `build-cpu/bin`，最后执行 `--version`。该构建优化为本机 CPU，换电脑应重新编译。

验证时修复了两项 Windows 环境问题：Git 长路径导致上游 UI 文件检出失败；MinGW 默认 Windows API 版本过低导致 `CreateFile2` 未声明。克隆时的 `core.longpaths=true` 和脚本中的 Windows 10 编译目标解决了这两项问题，没有修改上游源码。构建不带 llama.cpp 内嵌 UI、CUDA 或 OpenSSL，用于本机 HTTP 模型端点；Lab9 自己的网页以及 Python 到 OpenAI 的 HTTPS 请求不受影响。源码编译日志与真实模型回复保存在 `evidence/a/`。

验证端口 8011 上的 CPU 进程已停止。本机日常网站继续使用 8001 上已验证的官方 CUDA 版本，以保留 GPU 推理速度。源码构建版本显示 `build 1` 是浅克隆的提交计数，实际 commit 与 b12023 一致。

`.env` 配置：

```dotenv
LLM_API_BASE=http://127.0.0.1:8001/v1
LLM_MODEL=llama-3-8b-instruct
LLM_API_KEY=
```

若模型服务设置了认证，再填写 `LLM_API_KEY`。可用 `/v1/models` 检查模型，运行 `python -m scripts.check_setup --live` 才会发真实问答。接口说明来自 [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)。

## 2. Docker 本地整套运行

准备 Docker/Compose，以及已下载的模型文件。先 `python -m scripts.setup_a`，在 `.env` 填写 OpenAI key 和模型路径：

```dotenv
LLAMA_MODEL_DIR=/absolute/path/to/model-folder
LLAMA_MODEL_FILE=your-llama3-instruct.gguf
DOCKER_LLM_API_BASE=http://llama:8001/v1
```

Windows 路径建议使用正斜杠，例如 `C:/models`。模型文件夹只读挂载；MySQL 数据使用持久卷。

```sh
docker compose --env-file .env -f infra/compose.a.yml --profile llama config --quiet
docker compose --env-file .env -f infra/compose.a.yml --profile llama up -d --build
docker compose --env-file .env -f infra/compose.a.yml logs -f web llama
docker compose --env-file .env -f infra/compose.a.yml exec web python -m scripts.check_setup --live
```

默认只在宿主机 loopback 暴露网站 8000，MySQL/模型不映射公网端口。模型加载完成前问答可能失败，可稍后重试。此 CPU 容器配置未在本机执行，因为本机没有 Docker；源码和原生 MySQL 网站已测试，不能把 Compose 配置检查当作容器运行成功。

如使用另一个已运行的模型服务，省略 `--profile llama` 并把 `DOCKER_LLM_API_BASE` 指向**容器能访问**的地址；容器内 `127.0.0.1` 不是宿主机。生产复现时将 `LLAMA_CPP_IMAGE` 固定为你验证过的镜像版本或 digest；当前示例采用上游 `server` 标签。

## 3. 公网 HTTPS（有域名后）

1. 准备服务器，把域名 DNS A/AAAA 指向它，允许入站 TCP 80/443。
2. `.env` 设置 `LAB9_DOMAIN=实际域名`（不带 https://）和 `ACME_EMAIL=你的邮箱`；公开前设置 `PUBLIC_MODE=true`、随机至少 16 字符的 `REGISTRATION_CODE` 和 `PUBLIC_ORIGIN=https://实际域名`。
3. 网站可以先独立部署，不需要等 B 的签名资料。构建部署：

   ```sh
   docker compose --env-file .env -f infra/compose.a.yml --profile llama --profile https up -d --build
   ```

4. Caddy 自动申请证书并反向代理 HTTP 与 WebSocket；网站访问地址为 `https://实际域名/`。
5. 测试注册、两窗口群聊、真实问题、来源展开、刷新保留、断网重连。禁止直接公开 MySQL 或 Llama 端口。

B 提供包名和签名指纹后，再生成 Asset Links 并重新构建/启动 web 服务，最后验收 TWA。网站 HTTPS 可先交给 B；只有 Android 域名绑定需要这一步。

若首次证书签发失败，检查 DNS、端口占用、80/443 防火墙和 Caddy 日志，不要通过忽略证书验证来冒充 HTTPS 成功。

### 不租云服务器的课程演示方案

本机已经运行 MySQL、FastAPI 和 GPU Llama，缺的是外部 HTTPS 入口。可使用 [Tailscale Funnel](https://tailscale.com/docs/use-cases/application-testing/share-local-dev-server-with-internet) 把本机 8000 网站映射到稳定的 `https://设备名.tailnet名.ts.net` 地址，无需购买独立域名或公网 IP。Funnel 对所有计划开放；非商业 Personal 计划免费。该服务目前为 beta，有带宽限制；电脑、网络和本地服务必须持续运行。具体见 [Funnel 文档](https://tailscale.com/docs/features/tailscale-funnel) 和 [计划价格](https://tailscale.com/pricing)。

实施顺序：安装官方客户端并登录个人账号；确认 MagicDNS、HTTPS、Funnel 权限；在用户明确授权公开网站后将本机 8000 端口连接到 Funnel；验证外部 HTTPS、WebSocket、注册/登录及来源链接；把实际返回的网址给 B。公开前应限制注册和请求频率，并检查群聊中的 QA 数据。2026-10-31 已实际完成安装、登录及 Funnel 部署。地址为 **https://desktop-jdferfe.taile24d30.ts.net/**，公网 HTTPS、双客户端 WSS、真实 RAG 与来源回读均已通过；运行和停止方式见 [A-PUBLIC-DEPLOYMENT.md](A-PUBLIC-DEPLOYMENT.md)。

另一种 [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) 无需账号或域名，但每次启动都会换随机地址，适合临时预览。B 的 Android `defaultUrl` 和 Asset Links 验证应使用同一个最终地址，不能把随机临时地址称为稳定部署。

## 4. A/B 交接

B 提供包名及**实际签名 APK 的证书** SHA-256：

```sh
python -m scripts.assetlinks --package edu.example.actualpackage --fingerprint AA:BB:...真实32字节
```

上面只是参数形式，不是可直接使用的指纹。脚本会拒绝无效格式。debug 与 release 使用不同证书，必须匹配手机实际安装的版本；需要同时支持时重复传 `--fingerprint`。

部署后：

```sh
python -m scripts.assetlinks --package 实际包名 --fingerprint 实际指纹 --check-url https://实际域名
```

工具检查 HTTPS、无重定向、JSON MIME、包名及指纹。B 将同一网站地址写入 Android `defaultUrl`，重新安装签名 APK，在真机/模拟器测试无地址栏、登录、发消息、问答与来源链接。`assetlinks.json` 的服务路径已实现，**已有实际 HTTPS 域名，仍缺 B 的签名，关联验收尚未完成**。

## 5. 日志和停止

- 本地网站 Ctrl+C；模型服务 Ctrl+C。
- 容器 `docker compose --env-file .env -f infra/compose.a.yml --profile llama --profile https down`。不要加 `-v`，否则会删除持久数据库卷。
- 提交时只保存必要的脱敏运行日志，禁止上传 `.env`、认证 token、签名私钥或模型权重。
