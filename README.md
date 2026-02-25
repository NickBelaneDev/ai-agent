<div align="center">

# 🤖 AI Agent Service
### *FastAPI backend for Gemini-based chat applications*

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.123-009688?logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/LLM-Google_Gemini-8E75B2)
![Quality](https://img.shields.io/badge/Code_Quality-Ruff%20%7C%20Black%20%7C%20MyPy-111827)
![Security](https://img.shields.io/badge/Security-Bandit%20%7C%20pip--audit-B91C1C)

</div>

---

## ✨ About this project

This service provides a clean and extensible API layer on top of **Google Gemini** for chat applications.
It includes session persistence, token limits, configurable tool calling, and quality/security checks for CI pipelines.

---

## 🧩 Core Features

- 🧠 **Gemini Integration** via `google-genai` and `generic-llm-lib`
- 💬 **Stateful Chat Sessions** with persistent storage
- 🛡️ **Security-first design** (auth token headers, SQLi-focused tests, isolation checks)
- ⚡ **Async FastAPI architecture** for high-throughput workloads
- 🧰 **Tool calling support** through dynamic tool registry
- 📉 **Token-limit enforcement** for predictable cost and performance
- 🐳 **Docker support** for reproducible deployment

---

## 🏗️ Architecture Overview

```text
Client App
   │
   ▼
FastAPI API Layer (main.py)
   │
   ├── Auth / Rate limiting / Validation
   ├── Chat Service (src/services)
   ├── LLM Adapter (src/llms/gemini_default)
   └── DB Layer (src/db)
```

---

## 🚀 Quickstart

### 1) Clone

```bash
git clone https://github.com/NickBelaneDev/ai-agent
cd ai-agent
```

### 2) Configure environment

```bash
cp empty.env .env
```

Set at least:

```env
GEMINI_API_KEY=your_api_key_here
APP_API_TOKEN=your_strong_token_here
DATABASE_URL=sqlite+aiosqlite:///./chat_database.db
MAX_HISTORY_LENGTH=20
MAX_TOKENS_PER_CHAT_SESSION=10000
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Run locally

```bash
uvicorn main:app --reload --port 8000
```

Service URL: `http://localhost:8000`

---

## 🔐 Authentication

All `/gemini/*` endpoints require header authentication:

- Header: `X-Auth-Token`
- Value: `APP_API_TOKEN` from `.env`

Example:

```bash
curl -X POST "http://localhost:8000/gemini/chat" \
  -H "X-Auth-Token: your_strong_token_here" \
  -H "Content-Type: application/json" \
  -d '{"user_name":"test_user","prompt":"Hello Gemini"}'
```

---

## 🧪 Developer Workflow

A complete quality workflow is available via **Makefile** and **GitHub Actions**.

### Make targets

```bash
make install      # runtime + quality tooling
make quality      # ruff + black --check + mypy
make fix          # ruff --fix + black
make complexity   # xenon checks
make security     # bandit + pip-audit
make doc          # interrogate docstring coverage
make test         # pytest
```

### CI Pipeline

GitHub workflow: `.github/workflows/quality-gate.yml`

It runs:
- Ruff
- Black
- MyPy
- Xenon
- Bandit
- pip-audit
- Interrogate
- Pytest

---

## 🐳 Docker

```bash
docker-compose up --build -d
```

Default mapped service endpoint: `http://localhost:8083`

---

## 🗂️ Project Structure

```text
src/
├── config/      # Settings, logging, configuration loading
├── db/          # DB models, connection and persistence services
├── llms/        # Gemini adapter and model config
├── services/    # Chat orchestration and domain services
└── tools/       # LLM callable tools

tests/           # Security, config, db and service tests
```

---

## ✅ Testing

```bash
pytest
```

Optional DB inspection utility:

```bash
python inspect_db.py
```

---

## 📜 License

Use and adapt according to your repository license policy.
