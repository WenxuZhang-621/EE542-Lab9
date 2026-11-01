# A-to-B handoff

As of 2026-10-31, A's website, MySQL, local GPU Llama, real OpenAI embeddings, and two-turn QA with sources run locally. Public HTTPS has passed real two-turn RAG and two-client WSS tests. The website now serves Asset Links matching B's release signing information. Final TWA behavior on the installed APK is still pending.

Final website: **https://desktop-jdferfe.taile24d30.ts.net/**

B can set this as `defaultUrl` now. Visitors do not need Tailscale. Registration requires the team invitation code, which A shares privately; existing accounts do not need the code to log in. A's computer and services must remain running. See `A-PUBLIC-DEPLOYMENT.md` for deployment and shutdown instructions.

## What A provides to B

**The main deliverable is a reachable HTTPS website URL.** Put it in `defaultUrl` in `android/app/src/main/res/values/strings.xml`. It is not the Llama endpoint on port 8001.

`http://127.0.0.1:8000/` works only on the website computer. On B's computer or phone, it refers to B's own device. An Android emulator's `10.0.2.2` refers only to that emulator's host computer, not A's separate computer.

Supporting materials in the shared repository are this document, `DEPLOY-A.md`, and `A-HANDOFF.md`. Use the merged main branch and preserve B's local changes. Older offline archives are snapshots, not the current source of truth.

## What B provides to A

The final B → A row of the team's handoff table requires:

1. The actual `applicationId` from `android/app/build.gradle`.
2. The SHA-256 fingerprint of the certificate signing the APK actually installed: 32 hexadecimal bytes, usually colon-separated. Debug and release certificates may differ.
3. The corresponding `assetlinks.json`, or just the first two items so A can generate it with `scripts.assetlinks`.

A deploys the JSON at `/.well-known/assetlinks.json` on the final website. B uses the same URL in the app and installs the signed APK. Together, verify launch without an address bar, login, questions, and sources.

**A can deploy the website and share its URL before B's signing details are ready.** Those details are needed for the final app/domain association.

## B's Part 5 data

C supplies these inputs in the shared repository:

- `data/topic/index/chunks.jsonl`: the same 1,694 chunks; use matching chunk IDs for comparisons.
- `data/topic/questions.jsonl`: the fixed 32-question evaluation set.
- `data/topic/baseline_openai.json`: C's OpenAI retrieval baseline.
- `shared/contracts.py`, `docs/interfaces.md`, and `data/topic/README.md`: formats, interfaces, and evaluation conventions.

B implements Word2Vec, clustering, centroids, normalized K-dimensional histograms, and improvement comparisons. A's `evidence/a/evaluation.json` records the website answer pipeline; it does not replace B's embedding experiment or establish factual accuracy.

## Credentials do not need to be exchanged

B does not need A's API key, complete `.env`, JWT secret, database password, model authentication key, Android keystore private key, or keystore password. Connecting to the running website does not require A's OpenAI key. Package names and certificate fingerprints are public and may be shared.
