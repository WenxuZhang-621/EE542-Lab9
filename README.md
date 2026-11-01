# EE542 Lab9 — Custom Chatbot

An Android app for a topic-specific group chat with a RAG chatbot. Topic: **F-1 International Student Assistant** (F-1 status, CPT/OPT work, and U.S. taxes for international students).

Android app (TWA) → group-chat website (FastAPI + MySQL) → questions are answered by a self-hosted Llama 3.1 8B from passages retrieved from a knowledge base of 17 official U.S. government sources, and each answer shows its sources. Part 5 compares a custom word-histogram embedding with OpenAI embeddings on the same retrieval task.

## Team

| Member | Role | Parts | Work |
|---|---|---|---|
| Xiaopeng Wu | A: website and system integration | Part 1, Part 4 website | MySQL + FastAPI group chat, self-hosted Llama, RAG answers with sources in the chat, public HTTPS deployment and Asset Links |
| Fengmao Xie | B: Android and custom embedding | Part 2, Part 5, Part 4 app | TWA app configuration and signed release build; Word2Vec + custom k-means histogram embedding, improvements, and comparison with OpenAI |
| Wenxu Zhang | C: data and RAG Q&A | Part 3, Part 4 knowledge base | Upload page, PDF ingest into MySQL, 500-character chunking, OpenAI + FAISS vector store, Q&A chain with memory and `exit` CLI; F-1 knowledge base and evaluation question set |

`webapp/` and `android/` started from the course templates, and the upload page started from the course's Streamlit example. The documents in this repository refer to the three roles as A, B, and C.

## Repository layout

| Folder | Content |
|---|---|
| [`webapp/`](webapp/README.md) | Group-chat website: FastAPI backend, frontend, RAG service |
| [`android/`](android/README.md) | Trusted Web Activity app that opens the website |
| [`rag/`](rag/README.md) | Part 3 pipeline: document extraction, MySQL ingest, chunking, embeddings, retrieval, Q&A chain, CLI, upload page |
| [`data/topic/`](data/topic/README.md) | Part 4 knowledge base, evaluation questions, and OpenAI retrieval baseline |
| [`custom_embedding/`](custom_embedding/README.md) | Part 5 histogram embedding and evaluation |
| [`docs/`](docs/PART-A-REPORT.md) | Part A report, deployment notes, evaluation, and the [team interface contract](docs/interfaces.md) |
| `shared/`, `config/` | Shared data types (`shared/contracts.py`) and project settings (`config/project.json`) |
| `infra/`, `scripts/` | Docker Compose, Caddy, and setup and smoke-test scripts |
| `tests/` | Unit and integration tests |
| `evidence/` | Run records for each part |

## Setup

- Python 3.12+. Run every command from the repository root; each folder's README has its own run steps.
- `cp -n .env.example .env`, then fill in the database URL, JWT secret, and OpenAI API key.
- `.env`, signing keys, model files, and raw downloaded data are not committed.
