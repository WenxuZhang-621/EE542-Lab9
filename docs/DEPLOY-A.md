# A: Deploying Llama, HTTPS, and Android integration

## 1. Self-hosted Llama

The website uses OpenAI-compatible Chat Completions, but answer generation points to your own Llama service. The OpenAI key is used only by C's embedding retrieval and **is not sent to Llama**.

Obtain a Llama 3 Instruct GGUF model under its applicable license. This implementation uses an 8B model with Q4_K_M quantization to fit the available hardware. Model weights are not included in the source package and must not be committed with credentials.

Source build requires Git, CMake, and a C++ compiler; on Windows, Visual Studio C++ Build Tools is one option:

```sh
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --target llama-server -j 4
```

Record the actual `git rev-parse HEAD`, build commands, model filename/quantization, hardware, and startup logs. Upstream changes over time; consult its [build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).

Linux/macOS commonly use `build/bin/llama-server`; Windows multi-configuration builds commonly use `build/bin/Release/llama-server.exe`:

```sh
llama-server -m /absolute/path/to/model.gguf --host 127.0.0.1 --port 8001 --ctx-size 4096 --alias llama-3-8b-instruct -ngl 0
```

Windows can use `scripts/start_llama.ps1 -ServerPath PATH_TO_EXE -ModelPath PATH_TO_GGUF`. CPU is the default; GPU execution needs a corresponding CUDA/Metal build and suitable GPU layers. Do not expose the model port directly to the internet.

### Verified Windows source build

The CPU build used [LLVM-MinGW 20261020](https://github.com/mstorsjo/llvm-mingw/releases/tag/20261020), archive `llvm-mingw-20261020-ucrt-x86_64.zip`, CMake 4.4.4, and Ninja 1.13.2. Toolchain SHA-256: `fd5462b7f5d93b2ff981fcd3f9c7e427e47f3203c64ea91c27bcc444eebd74cd`. Source is pinned to b12023, commit `f3586e66bc916d672773d4a6505513ba91a3595c`.

On a new computer, download/extract that toolchain, then run from the Lab9 root:

```powershell
python -m pip install cmake==4.4.4 ninja==1.13.2
git -c core.longpaths=true clone --depth 1 --branch b12023 https://github.com/ggml-org/llama.cpp.git ../llama-cpp-source
powershell -ExecutionPolicy Bypass -File scripts/build_llama_cpu.ps1 -SourcePath ../llama-cpp-source -CompilerBin C:/path/to/llvm-mingw-20261020-ucrt-x86_64/bin
```

Activate the Python environment first, or supply explicit `-CMakePath` / `-NinjaPath`. Do not clone over an existing source directory. The script builds a Release CPU server, copies needed compiler runtimes to `build-cpu/bin`, and runs `--version`. It optimizes for the current CPU; rebuild on another computer.

Two Windows problems were resolved: long paths prevented checkout of upstream UI files, and MinGW's default Windows API target did not declare `CreateFile2`. `core.longpaths=true` and the script's Windows 10 compilation target addressed these without changing upstream source. The build excludes llama.cpp's embedded UI, CUDA, and OpenSSL and serves a local HTTP model endpoint. Lab9's own UI and Python's HTTPS requests to OpenAI are unaffected. Logs and a real response are under `evidence/a/`.

The CPU verification process on 8011 was stopped. Daily website operation continues using the verified official CUDA server on 8001 for GPU speed. The source build's `build 1` reflects shallow-clone commit counting; the actual commit matches b12023.

Configure `.env`:

```dotenv
LLM_API_BASE=http://127.0.0.1:8001/v1
LLM_MODEL=llama-3-8b-instruct
LLM_API_KEY=
```

Set `LLM_API_KEY` if your model server requires authentication. `/v1/models` checks model availability; `python -m scripts.check_setup --live` makes a real QA request. See the [llama.cpp server reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## 2. Local Docker stack

Install Docker/Compose and obtain the model file. Run `python -m scripts.setup_a`, then configure your OpenAI key and model paths in `.env`:

```dotenv
LLAMA_MODEL_DIR=/absolute/path/to/model-folder
LLAMA_MODEL_FILE=your-llama3-instruct.gguf
DOCKER_LLM_API_BASE=http://llama:8001/v1
```

Use forward slashes for Windows paths, such as `C:/models`. The model directory is mounted read-only; MySQL uses a persistent volume.

```sh
docker compose --env-file .env -f infra/compose.a.yml --profile llama config --quiet
docker compose --env-file .env -f infra/compose.a.yml --profile llama up -d --build
docker compose --env-file .env -f infra/compose.a.yml logs -f web llama
docker compose --env-file .env -f infra/compose.a.yml exec web python -m scripts.check_setup --live
```

By default, only website port 8000 is bound on host loopback; MySQL/model ports are not public. QA can fail until the model finishes loading; retry afterward. This CPU container configuration was not executed on the local machine because Docker was unavailable. Native source builds and the MySQL website were tested; Compose parsing is not proof that containers ran.

To use an existing model service, omit `--profile llama` and set `DOCKER_LLM_API_BASE` to an address **reachable from the container**. Container `127.0.0.1` is not the host. For reproducible deployment, pin `LLAMA_CPP_IMAGE` to a tested version/digest; the example uses upstream's `server` tag.

## 3. Public HTTPS with your own domain

1. Prepare a server, point the domain's DNS A/AAAA records to it, and allow inbound TCP 80/443.
2. Set `LAB9_DOMAIN=YOUR_DOMAIN` without https:// and `ACME_EMAIL=YOUR_EMAIL` in `.env`. Before publication, set `PUBLIC_MODE=true`, a random `REGISTRATION_CODE` of at least 16 characters, and `PUBLIC_ORIGIN=https://YOUR_DOMAIN`.
3. Deploy the website without waiting for B's signing details:

   ```sh
   docker compose --env-file .env -f infra/compose.a.yml --profile llama --profile https up -d --build
   ```

4. Caddy obtains a certificate and proxies HTTP/WebSocket; visit `https://YOUR_DOMAIN/`.
5. Test registration, two-session chat, real questions, sources, refresh persistence, and reconnection. Do not directly expose MySQL or Llama ports.

After B supplies the package name and signing fingerprint, generate Asset Links, rebuild/restart web, and verify TWA. The HTTPS URL can be handed to B earlier; only Android domain association depends on signing details.

If certificate issuance fails, check DNS, occupied ports, firewall rules for 80/443, and Caddy logs. Skipping certificate validation does not establish working HTTPS.

### Course demonstration without renting a cloud server

The local computer already runs MySQL, FastAPI, and GPU Llama. [Tailscale Funnel](https://tailscale.com/docs/use-cases/application-testing/share-local-dev-server-with-internet) supplies an external HTTPS entry point to local port 8000 at an address such as `https://DEVICE.TAILNET.ts.net`, without purchasing a separate domain or public IP. At the recorded deployment date, Funnel was available across plans, including the free noncommercial Personal plan, and was a beta service with bandwidth limits. The computer, network, and services must stay running. Check [Funnel documentation](https://tailscale.com/docs/features/tailscale-funnel) and [plans](https://tailscale.com/pricing) for current terms.

Sequence: install the official client and sign in; confirm MagicDNS, HTTPS, and Funnel permissions; publish local port 8000 after the user authorizes public access; verify external HTTPS, WebSocket, authentication, and source links; give B the returned URL. Restrict registration/request rates and review chat QA data before publication.

Installation, login, and Funnel deployment were completed on 2026-10-31. Actual URL: **https://desktop-jdferfe.taile24d30.ts.net/**. Public HTTPS, two-client WSS, real RAG, and source readback passed. See [A-PUBLIC-DEPLOYMENT.md](A-PUBLIC-DEPLOYMENT.md) for operation and shutdown.

[Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) is another temporary-preview option, with a random URL that changes on restart. Android `defaultUrl` and Asset Links must use the same final address; a changing temporary URL is not a stable deployment.

## 4. A/B handoff

B provides the package name and SHA-256 fingerprint of the certificate signing the **actually installed APK**:

```sh
python -m scripts.assetlinks --package edu.example.actualpackage --fingerprint ACTUAL_SHA256_FINGERPRINT
```

Replace the placeholder with 32 hexadecimal bytes, normally colon-separated. The script rejects invalid formats. Debug and release certificates differ; use the certificate matching the installed build. Repeat `--fingerprint` if both must be supported.

After deployment:

```sh
python -m scripts.assetlinks --package ACTUAL_PACKAGE_NAME --fingerprint ACTUAL_SHA256_FINGERPRINT --check-url https://YOUR_DOMAIN
```

The tool checks HTTPS, no redirects, JSON MIME type, package name, and fingerprint. B sets the same URL as Android `defaultUrl`, reinstalls the signed APK, and tests address-bar-free launch, login, messaging, QA, and source links. The actual HTTPS domain now serves Asset Links matching B's release package and fingerprint; the HTTPS validation command passed. **Final behavior on B's installed signed APK remains to be verified.**

## 5. Logs and shutdown

- Stop a foreground local website/model process with Ctrl+C in its own terminal.
- Stop containers with `docker compose --env-file .env -f infra/compose.a.yml --profile llama --profile https down`. Do not add `-v`, which deletes persistent database volumes.
- Retain only necessary redacted logs. Never upload `.env`, authentication tokens, signing private keys, or model weights.
