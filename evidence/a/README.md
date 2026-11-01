# A: Verification records

Original implementation base: `9e1a0df4e7e9a25c36b086842b11e54e73d1bcf2`. Environment: Windows, Python 3.12.14, MySQL Community Server 8.4.13.

| File | Description |
|---|---|
| `tests.txt` | 66 tests and five subtests passed, including real MySQL storage, A's automated checks, insufficient-credit handling, truncated-context expansion, and matching form sections |
| `delivery-checks.txt` | Latest A-only checks: 27 focused tests, JavaScript syntax validation, and read-only local preflight passed; separate from the earlier combined suite |
| `mysql-web-smoke.txt` | Running FastAPI + MySQL: random QA account creation, login, bidirectional WebSocket broadcasts, and history readback; no LLM call |
| `preflight.txt` | Index integrity, JWT, real MySQL connectivity, and Llama connectivity passed; an OpenAI key was configured; this check does not verify account credits |
| `local-llama-live.json` | Real Llama output/timing on the local RTX 5070 Ti; verifies only the official prebuilt CUDA model service |
| `llama-source-configure.txt` / `llama-source-build.txt` | Local CPU build logs for pinned b12023 source; 227 build steps completed with LLVM-MinGW, CMake, and Ninja |
| `source-llama-live.json` | The source-built CPU server loaded the same 8B model and generated a real response; records commit, compiler, and timing, without OpenAI retrieval |
| `openai-embedding-check.json` | Successful real OpenAI embedding request using the locally configured key: text-embedding-3-small, 1,536 dimensions |
| `live-preflight.txt` | Complete real RAG environment check, generated answer, sources, and citation status |
| `live-web-smoke.json` | Two real turns through MySQL + FastAPI + OpenAI embeddings + local Llama; topic/Students-field checks, loading/done broadcasts, and persisted-source readback |
| `live-web-answer.png` | Browser screenshot of the actual local service's two-turn QA; answers/sources remain after refresh; not a fixture |
| `compose-validation.txt` | Docker Compose v5.6.1 parsed all web/MySQL/Llama/HTTPS profiles; configuration validation does not mean containers ran |
| `android-association.json` | Public HTTPS Asset Links matched B's package and release certificate fingerprint; installed-APK verification remains pending |
| `mobile-error-state.png` | Actual 390×844 page showing retrieval failure when the OpenAI key was missing; DOM checks found no horizontal overflow |
| `source-card-fixture.png` | Simulated answer from an isolated SQLite UI service, explicitly labeled UI TEST FIXTURE; validates source links, pages, citations, and excerpts, not model-generated answers |

Browser checks also verified persisted sources after refresh and return to the login screen after logout. No browser-console JS errors/warnings were observed. Production pages contain no fixture-answer logic; the fixture runs only when explicitly launched with `python -m tests.browser_fixture` on port 8002.

On 2026-10-31, the full local RAG pipeline and two-turn follow-up were verified; the cited Students section was compared manually with the displayed source. Coverage is limited and does not imply correct answers to every question. Older fixture/failure screenshots remain as records of state handling, not the current service state. Public HTTPS is deployed and tested; B has since provided signing details, and A has validated the deployed Asset Links response; actual signed-APK behavior still needs device verification. See `docs/A-PUBLIC-DEPLOYMENT.md`.

These are engineering QA records, not a replacement for the instructor's required phone footage of team work. Personal logs and Git contributions must reflect each member's actual work.

Additional local evidence: `evaluation.json` stores real generated answers, sources, and coverage metrics for 32 questions; human findings and limitations are in `docs/A-EVALUATION.md`. `embedding-trace.json` shows real 1,536-dimensional query/document-vector samples and similarities. `mobile-live-sources.png` and `mobile-live-check.json` verify real source expansion at 390×844 without horizontal overflow.

Public evidence: `public-https-smoke.json` records HTTPS through a public Funnel address, two-client WSS, real two-turn QA, and source readback. `public-https-login.png` shows the invitation-based authentication page; `public-https-sources.png` shows expanded excerpts after refresh. `funnel-status.json` shows that only HTTPS port 443 proxies local port 8000.
