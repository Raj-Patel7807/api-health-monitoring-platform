# Contributing

Thank you for contributing. This is a team course project. Keep each change small, clear, tested, and linked to a requirement or story.

## Start safely

1. Read `AGENT.md`, `docs/engineering/CODE_RULES.md`, and the relevant design and requirement documents.
2. Create a branch from the current shared branch. Do not work on `main`.
3. Check `git status` before editing.
4. Keep work inside the agreed issue or story scope.

## Development checks

Backend: run `uv sync --frozen`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy app`, and `uv run pytest --cov=app` from `backend/`.

Frontend: run `npm ci`, `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` from `frontend/`.

Run `docker compose config` after compose changes. Add tests with every behavior change. Never add secrets to Git.

## Pull requests

Use a descriptive title. Explain what changed, the requirement/story IDs, tests run, and any documentation updates. Request review. Do not bypass failed checks or merge your own pull request.
