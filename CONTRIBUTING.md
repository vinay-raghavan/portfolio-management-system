# Contributing to Portfolio Management System

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all experience levels.

## Getting Started

1. **Fork the repository** and clone your fork
2. **Set up the development environment**:
   ```bash
   # Copy environment files
   cp .env.example .env
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env

   # Start services with Docker
   docker-compose up -d

   # Or run locally
   cd backend && uv sync && uv run uvicorn app.main:app --reload
   cd frontend && npm install && npm run dev
   ```

3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

## Development Guidelines

### Code Style

**Python (Backend)**:
- Use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Run before committing:
  ```bash
  cd backend
  uv run ruff check . ../shared
  uv run ruff format . ../shared
  ```

**TypeScript (Frontend)**:
- Follow existing code patterns
- Use TypeScript strict mode
- Run lint checks:
  ```bash
  cd frontend
  npm run lint
  ```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting:
  ```bash
  # Backend tests
  cd backend && uv run pytest

  # Shared library tests
  cd shared && uv run pytest
  ```

### Commit Messages

Use conventional commit format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Examples:
```
feat(screener): add RSI indicator filter
fix(broker): handle Fyers token expiration
docs: update API documentation
```

## Pull Request Process

1. **Update documentation** if needed
2. **Add/update tests** for your changes
3. **Run all checks**:
   ```bash
   cd backend
   uv run ruff check . ../shared
   uv run ruff format --check . ../shared
   uv run pytest
   uv run bandit -r app -q
   ```
4. **Submit the PR** with a clear description of changes
5. **Link related issues** using `Fixes #123` or `Closes #123`

## Reporting Issues

When reporting bugs, please include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, browser, Python/Node versions)
- Relevant logs or screenshots

## Feature Requests

We welcome feature suggestions! Please:
- Check existing issues first
- Describe the use case
- Explain why it would benefit other users

## Project Structure

```
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Config, security, database
│   │   └── modules/  # Feature modules
│   └── tests/
├── frontend/         # Next.js frontend
│   ├── src/
│   │   ├── app/      # App router pages
│   │   ├── components/
│   │   └── lib/      # Utilities, API client
├── shared/           # Shared Python library
├── trading-engine/   # Algo trading engine
└── worker/           # Celery background tasks
```

## Questions?

Feel free to open a discussion or issue if you have questions about contributing.

Thank you for helping improve this project! 🚀
