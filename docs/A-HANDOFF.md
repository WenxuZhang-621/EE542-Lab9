# A: Website and system integration handoff

This implementation started from `9e1a0df4e7e9a25c36b086842b11e54e73d1bcf2`. Its scope is A: Part 1 and the Part 4 website. Another team member handles B's Android app and custom embeddings.

## Implemented

- Registration/login, authenticated WebSocket group chat, and ordinary-message/assistant-question selection. Both ASCII and full-width question marks can trigger the assistant.
- `ask_llm()` → `answer_with_sources()` → C's `rag.api.retrieve()` in a worker thread → the self-hosted Llama OpenAI-compatible `/v1/chat/completions` endpoint.
- Context assembly preserves C's 500-character index and retrieval interface, adding up to one neighboring chunk on each side from the same document and page to avoid truncated sentences. For questions naming a specific form and category, at most half the sources prioritize matching Part headings such as Students; the remaining sources retain vector ranking. Every source preserves its original hit ID and `context_chunk_ids`.
- Llama rewrites follow-ups as standalone questions. Memory is keyed by user ID plus browser-session UUID, retains up to three turns across at most 256 sessions, and expires after one idle hour. MySQL stores shared chat history; model memory exists only in the current process and resets on restart.
- The prompt requests answers supported by retrieved context, numbered citations such as `[1]`, and disclosure of conflicting sources. It requests no guessing when evidence is missing. Citation numbers are checked against available sources, but valid citations do not guarantee factual correctness; compare answers with the original text during evaluation.
- Source titles, publishers, URLs, pages, chunk IDs, and excerpts are stored with answers in `message_details` and remain available after refresh. Existing `users/messages` tables and records are preserved.
- Loading indicators, reconnection, failure messages, and retrying the original question. Logging out closes the WebSocket.
- Mobile layout, PWA manifest/icons, a service worker caching only public static files, and the `/.well-known/assetlinks.json` route with generation/validation tools for B.
- Docker Compose for MySQL/FastAPI with optional Llama and Caddy HTTPS, Windows launch scripts, environment checks, and CI.

## Actual verification scope

MySQL Community Server 8.4.13 and FastAPI ran locally. Browser checks covered registration, login, messaging, failures, and a 390-pixel mobile layout. Evidence is under `evidence/a/`.

The test suite passed 66 tests and five subtests, including real MySQL storage and controlled retrieval/model substitutes for integration, broadcasting, memory isolation, and error handling. The earlier `source-card-fixture.png` came from an isolated service explicitly labeled **UI TEST FIXTURE**. `live-web-answer.png` and `live-web-smoke.json` record actual service answers.

On 2026-10-31, the official prebuilt llama.cpp b12023 Windows CUDA 13.4 server loaded Meta-Llama-3.1-8B-Instruct-Q4_K_M, approximately 4.92 GB, and generated real responses on an RTX 5070 Ti. Model and runtime SHA-256 hashes were checked against publisher metadata. The model binds to 127.0.0.1:8001 with a random local authentication key; the website uses port 8000 and local MySQL uses 13409.

The source-build requirement was also verified that day: llama.cpp b12023 / `f3586e66bc916d672773d4a6505513ba91a3595c` was compiled as a CPU `llama-server` using LLVM-MinGW Clang 23.1.4, CMake 4.4.4, and Ninja 1.13.2. It loaded the same 8B model on local port 8011 and produced a real response, then was stopped. The website continues using the GPU server on 8001. These are separate results: the CPU source build must not be described as a CUDA source build. Reproduction script: `scripts/build_llama_cpu.ps1`.

On 2026-10-31, with an authorized OpenAI key stored in the ignored local `.env` and sufficient API credits, a real `text-embedding-3-small` request returned 1,536 dimensions. Both `scripts.check_setup --live` and `scripts.smoke_web_live` passed. The full chain was real OpenAI query embedding → C's FAISS retrieval → A's context assembly → local Llama 3.1 8B → HTTP/WebSocket → MySQL. The two questions covered the purpose of Form 8843 and what information “that form” requests from students. Checks covered the form/topic, Students section, citations, loading/done broadcasts, and persisted sources. Excerpts remained available after browser refresh.

Testing exposed truncated 500-character passages, follow-up language/topic drift caused by JSON-formatted history, and teacher sections displacing student sections. Fixes included neighboring context, native conversation roles with minimal reference-only rewriting, and explicit form/category section matching; regression tests cover these cases. Small-model answers still need human comparison with the source. Two successful demo questions do not establish knowledge-base-wide factual accuracy. A subsequent 32-question evaluation returned cited answers for 32/32 questions and covered annotated source text for 30/32, but human review found generation errors and unacknowledged source conflicts. See `A-EVALUATION.md`. The website retains an explicit insufficient-credit message and retry control.

Public HTTPS is deployed and tested at https://desktop-jdferfe.taile24d30.ts.net/; see `A-PUBLIC-DEPLOYMENT.md`. B has committed a signed release build record, package name, and certificate fingerprint. A has deployed matching Asset Links and verified the public HTTPS response. Final TWA behavior still needs validation on the installed signed APK. The source package excludes `.env`, databases, models, and real keys; teammates must use their own authorized local configuration.

## Compatibility with C's work

A's original integration preserved C's retrieval signature, corpus, and FAISS index contents. It made two Windows fixes in `rag/vectorstore.py`: explicitly read chunks as UTF-8 and write them with LF so file bytes match SHA-256 checksums. `.gitattributes` prevents Git from converting verified JSONL to CRLF. If an old checkout still has CRLF, save local changes before checking out the current file again; do not bypass validation by arbitrarily changing the manifest. The current A documentation cleanup does not modify C's source data, index, or baseline.

## Interface for B

1. During development, test the browser page through the website computer's LAN address. An Android emulator typically reaches its own host at `http://10.0.2.2:8000`; a physical phone uses the computer's LAN address. LAN access requires binding to `0.0.0.0` and suitable network/firewall rules.
2. A production TWA `defaultUrl` must be the final **HTTPS website URL**, not the model endpoint on port 8001. Local HTTP access does not establish TWA domain verification.
3. B supplies the actual `applicationId` and SHA-256 fingerprint of the certificate used to sign the installed APK. The fingerprint is public; B retains the private key.
4. A runs `python -m scripts.assetlinks --package ACTUAL_PACKAGE_NAME --fingerprint ACTUAL_SHA256_FINGERPRINT` and deploys the generated JSON.
5. A runs `python -m scripts.assetlinks --package ACTUAL_PACKAGE_NAME --fingerprint ACTUAL_SHA256_FINGERPRINT --check-url https://YOUR_DOMAIN`. B reinstalls the signed APK and checks login, questions, source links, and launch without an address bar.

B has supplied applicationId `edu.usc.ee542.f1assistant` and its release certificate fingerprint. The deployed Asset Links JSON matches them; device-level TWA verification remains pending. See `evidence/a/android-association.json` and B's build record in `evidence/b-part2/README.md`.

## Integration workflow

Use a branch and pull request to coordinate changes with B and C. Check compatibility with their latest work before merging. The shared repository is the source of truth; preserve teammates' local changes when updating a checkout. Commit messages and contribution logs should identify each member's actual implementation and verification work.
