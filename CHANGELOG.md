# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0-alpha] - 2026-01-02

### Added
- **Core:** Initial implementation of `GenericAgent` with support for Google Gemini 2.0.
- **Tools:** `AgentToolRegistry` to manage and inject Python functions into the LLM context.
- **API:** FastAPI backend with endpoints for stateful chat (`/gemini/chat`) and one-off generation (`/gemini/generate_content`).
- **Database:** Async SQLAlchemy integration with SQLite to persist chat history.
- **Deployment:** `Dockerfile` and `docker-compose.yml` for containerized environments.
- **Security:** Header-based authentication using `X-Auth-Token`.
- **Tests:** Comprehensive test suite for services, core logic, and database operations.

### Changed
- Refactored session management to include an automatic timeout (300 seconds) for clearing context.

### Fixed
- Improved history serialization to handle Google GenAI objects and Pydantic models correctly.