# Contributing to AutoBacklog

Thank you for your interest in contributing to **AutoBacklog**!

AutoBacklog is an autonomous backlog runner built for software engineers who want reliable, resilient AI-driven sprint execution. We welcome contributions, bug reports, and feature proposals.

---

## 🛠️ Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/allardv03/AutoBacklog.git
   cd AutoBacklog
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install editable dependencies and dev tools:
   ```bash
   pip install -e ".[dev]"
   ```

---

## 🧪 Running Tests

Before submitting a Pull Request, make sure all tests pass:

```bash
python -m unittest discover
```

---

## 📐 Code Style & Architecture Guidelines

* **Multi-Platform Support**: AutoBacklog must run seamlessly across Windows (PowerShell/CMD), macOS (zsh), and Linux (bash). Never assume bash pipes or POSIX paths.
* **Resilience First**: Always design safeguards for errors, quota exhaustion (429), and connection drops. Zero-diff aborts must never leave dirty or locked states.
* **Minimal Dependencies**: The core package relies only on standard Python libraries, `pyyaml`, and `python-dotenv`. Keep third-party dependencies to an absolute minimum.

---

## 🚀 Submitting a Pull Request

1. Create a feature branch: `git checkout -b feat/my-new-feature`.
2. Follow Conventional Commits: `feat(...)`, `fix(...)`, `docs(...)`, `test(...)`.
3. Add unit tests in `tests/` for any new logic.
4. Ensure all unit tests pass with `python -m unittest discover`.
5. Open a Pull Request on GitHub with a clear summary and verification proof.

---

## 📄 License

By contributing to AutoBacklog, you agree that your contributions will be licensed under the [MIT License](LICENSE).
