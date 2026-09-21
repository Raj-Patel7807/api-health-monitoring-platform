# Working Guide

## Before work

Read this file and the relevant files in `docs/`. Always read `docs/engineering/CODE_RULES.md` and `docs/design/ARCHITECTURE.md`. Read `docs/design/DATABASE.md` before database work, `docs/design/API.md` before API work, `docs/engineering/TESTING.md` before tests or feature work, `docs/engineering/CONFIG.md` before adding environment variables, and `docs/planning/DECISIONS.md` before an architecture decision. Read the related requirement IDs and user stories. Check the Git branch and status. Understand existing code before editing it.

## While working

Stay in the requested scope. Do not change another member's unrelated work. Follow the architecture and reuse existing utilities. Prefer the standard library for simple work and a mature library only when it has clear value. Write the smallest correct solution. Keep functions and classes focused, public interfaces typed, and external input validated. Handle errors clearly. Never hardcode secrets. Store timestamps in UTC. Keep migrations backward-aware and preserve API compatibility unless the task says otherwise. Add useful logging at important boundaries.

Write comments or docstrings only when they explain a business rule, public contract, important reason, edge case, retry, lock, or security decision. Remove dead code instead of commenting it out. Do not leave unexplained TODOs or add dependencies without a clear reason.

## Tests are required

For every feature or fix, add or update unit tests. Add integration tests when a database, Redis, API boundary, worker, or external integration is involved. Add a regression test for bugs. Mock external providers. CI must never call real Slack, Discord, email, webhook, or LLM APIs. Test success, important failures, and relevant security boundaries. Run affected tests before committing.

## Documentation and Git

Update documentation when API behavior, architecture, schema, configuration, deployment, tests, user behavior, or a technical decision changes. Record important architecture choices in `docs/planning/DECISIONS.md`.

Never commit directly to `main`, force-push, bypass branch protection, or merge a pull request yourself. Use a member feature branch. Keep commits small and meaningful. Use Conventional Commit style when practical, such as `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, or `ci:`. Avoid vague commit messages. Do not squash member commits unless the project lead asks.

## Before finishing

Format code, run lint, type checks, unit tests, relevant integration tests, and the affected build. Check migrations for database work and `docker compose config` for infrastructure work. Check for secrets, update documentation, and inspect `git diff` for intended changes only.

**A task is not complete while tests, build, type checks, lint, or required CI are failing.**
