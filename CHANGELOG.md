# Changelog

All notable changes to **AutoBacklog** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-30

### 🚀 Initial Public Release

#### Added
* **Universal Backlog Adapters**:
  * Azure DevOps Boards (`azure_boards.py`) supporting full WIQL querying, state updates (`New` -> `Active` -> `Resolved`), and `--discussion` note synchronization with automatic offline JSON caching.
  * GitHub Issues (`github_issues.py`) using `gh` CLI with auto git remote discovery and labels filtering.
  * Local Markdown Plan (`markdown_plan.py`) parsing `#123 Title` and `- [ ] Title (#123)` from `PLAN.md` or `BACKLOG.md` files without cloud dependencies.
* **Multi-Provider AI Adapters**:
  * Google Antigravity (`agy.py`) targeting `gemini-4-argon-high` (Large) and `gemini-3.8-flash-high` (Small).
  * Anthropic Claude Code CLI (`claude.py`) targeting `claude-3-7-sonnet` (Large) and `claude-3-5-haiku` (Small).
* **Autonomous Safeguards**:
  * Pre-flight snapshots (`snapshot.py`) with automatic git tag checkpointing and ZIP archives.
  * Persistent Quota & Rate-Limit Cache (`quota_cache.py`) with real-time countdown calculation.
  * Zero-diff auto-revert guard (`dirty_guard.py`) resetting untouched items to `New` upon premature CLI aborts.
  * Physical hardware detection (`hardware.py`) querying connected Android devices over ADB.
* **Observability & UX**:
  * Smart Console Streamer (`streamer.py`) with polling loop deduplication and human-friendly quota formatting.
  * Live progress dashboard (`dashboard.py`) maintaining `RUN_SUMMARY.md` in real-time.
* **CLI & Tooling**:
  * Unified commands: `run`, `init`, `dry-run`, `summary`, `restore`, `clear-quota`.
  * Multi-platform UTF-8 encoding support for Windows terminals.
