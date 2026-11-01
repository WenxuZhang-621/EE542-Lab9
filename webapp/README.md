# A: Website and system integration

See the [Part A technical report](../docs/PART-A-REPORT.md) ([PDF](../docs/PART-A-REPORT.pdf)), [A-HANDOFF](../docs/A-HANDOFF.md) for implementation and verification, and [DEPLOY-A](../docs/DEPLOY-A.md) for deployment. Requires **Python 3.12+**. Run all commands from the repository root.

## Local setup

```powershell
# Windows with Python 3.12+ installed
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-a.txt
.\.venv\Scripts\python.exe -m scripts.setup_a
```

On macOS/Linux, use `python3.12 -m venv .venv`, activate the environment, then use `python` for subsequent commands.

`setup_a` creates `.env` only if it does not exist and generates random JWT/database passwords. It neither overwrites existing configuration nor prints passwords.

1. Set your own `OPENAI_API_KEY` in local `.env`. On Windows, `powershell -STA -ExecutionPolicy Bypass -File scripts/configure_key.ps1` saves it through a password input without printing it; restart the website afterward. A uses C's existing index, but **each retrieval still needs an OpenAI API request to embed the question**. A Llama authentication key cannot replace this key.
2. Start MySQL. If Docker is installed, use the isolated database configuration:

   ```sh
   docker compose --env-file .env -f infra/compose.mysql.yml up -d --wait
   ```

   `setup_a` defaults to `127.0.0.1:13306/groupchat`, using `.env`'s `LAB9_MYSQL_PASSWORD`. For an existing MySQL server, create `groupchat` and a `chatuser` with access to it, then update the DSN. Do not use the template's `chatpass` for a public deployment.
3. Start your own Llama 3 Instruct server; see the deployment guide. Default endpoint: `http://127.0.0.1:8001/v1`; model alias: `llama-3-8b-instruct`.
4. Start the website:

   ```sh
   python -X utf8 -m webapp.backend.run
   ```

5. Open `http://127.0.0.1:8000`, register, and log in. Use two accounts in independent browser sessions for the chat demonstration. Login state is tab-scoped. An ordinary group message requires Ask the assistant to be unchecked and no question mark in the text.

On Windows, subsequent launches can use `powershell -ExecutionPolicy Bypass -File scripts/start_web.ps1`; `-Install` checks dependencies again. The process-level ExecutionPolicy argument runs this repository's script without changing system policy.

For a UI-only preview without MySQL, run `python -m scripts.setup_a --sqlite-preview` in a **new directory with no `.env`**, then start the website. This does not satisfy the assignment's MySQL requirement, does not simulate successful RAG, and does not support C's MySQL ingestion pipeline.

## Checks

```sh
python -m scripts.check_setup
python -m scripts.check_setup --live
python -m scripts.smoke_web_live
```

The first command makes no paid model request: it checks index integrity, configuration, the database, and `/v1/models`. The second sends one real question only after prerequisites pass, calling OpenAI embeddings and self-hosted Llama. The third creates local QA accounts and sends two real questions, checking loading events, answer broadcasts, and source readback, with two embedding requests. Failures exit with code 1; missing keys or model services are not reported as passes.

`embedding_credit_exhausted` means the OpenAI embedding account has insufficient API credits. Check official API Billing and retry after credits are available; recreating the key is unnecessary. A normal preflight pass does not verify API credits.

```sh
python -m pip install -r tests/requirements.txt
python -m pytest tests/test_webapp.py tests/test_web_rag.py tests/test_public_access.py tests/test_assetlinks.py -q
node --check webapp/frontend/app.js
```

These commands run A's 27 focused tests and JavaScript syntax validation. C's real MySQL tests are separate and require `LAB9_TEST_MYSQL=1`; they clean up only their own randomly named records. `tests/browser_fixture.py` is explicitly labeled as a UI test substitute and must not be used as the final QA demonstration.

## Data and runtime conventions

- Existing `users/messages` tables are retained. Startup adds `message_details` for sources, reply IDs, and error status; it does not create the database itself.
- One shared chat room: every logged-in user can see messages and answers. Do not enter passport numbers, SSNs, or other personal identifiers. Model follow-up memory is isolated per user/session.
- Run **one Uvicorn worker**. WebSocket connections and session locks are in memory; multiple workers/replicas require a shared message bus and session storage.
- Display the knowledge-base notice from `sources.json`; source URLs come from `catalog.json`; render body text with `textContent`.
- Health reports database connectivity and configuration state. `llm_configured` means an endpoint is configured, not that it is online; use preflight for connectivity.
- C's source snapshots can differ in date and content. The prompt requests disclosure of conflicts and shows original passages for comparison. Retrieval ranking does not determine legal authority.

## Endpoints

- `POST /api/signup`, `POST /api/login` → token, username, user_id.
- `GET /api/me`, `GET /api/messages` → require a Bearer token.
- `POST /api/messages` → `{content, ask_bot, session_id}`; session_id is a UUID; returns the original message and optional answer.
- `POST /api/messages/{id}/retry` → only the original sender may retry an assistant question.
- WebSocket `/ws` → send `{token}` within ten seconds after connecting; after `ready`, receive `message` and `bot_status` events. Tokens are not placed in URLs; unauthenticated connections cannot receive messages.

A's additions are in `webapp/`, `scripts/`, `infra/`, tests, and handoff documents. Distinguish the instructor's templates, C's implementation, and A's changes in explanations and Git logs.
