# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0-beta] - 2026-01-05

### Added
- **Security:** Enhanced security with SQL injection prevention tests and session security validation.
- **Database:** Added `inspect_db.py` utility for quick database inspection.
- **Testing:** Added comprehensive tests for race conditions, resource exhaustion, and SQL injection.
- **Configuration:** Added `empty.env` template and updated configuration loading logic.
- **Service:** Implemented new `ChatService` logic with improved error handling and session management.

### Changed
- **Refactoring:** Major refactoring of `ChatService` to improve maintainability and performance.
- **Database:** Updated `models.py` and `service.py` to support new session management features.
- **Dependencies:** Updated `requirements.txt` to reflect new dependencies.
- **Main:** Updated `main.py` to integrate new service logic and configuration.

### Fixed
- **Concurrency:** Resolved potential race conditions in database operations.
- **Security:** Fixed potential SQL injection vulnerabilities.

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