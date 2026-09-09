# Project Rules

## GitHub workflow

- Always deliver repository changes through a Pull Request.
- Never commit or push directly to `main`.
- Before making GitHub changes, create or use a feature branch based on the
  latest `main`.
- Push the feature branch, open a PR targeting `main`, and report the PR URL.
- Do not merge the PR unless the user explicitly asks for the merge.
- When the user says deploy for this repository, interpret it as committing
  the requested changes, pushing the feature branch to GitHub, creating or
  updating a PR targeting main, and enabling squash auto-merge so it merges
  after required checks pass. Never push directly to main; if checks fail,
  report the blocker instead of forcing a merge.
- Keep local-only configuration, credentials, and logs out of commits. In
  particular, never commit `.env.rag`, `.env.pgvector`, or files under
  `rag_pipeline/logs/`.

## Verification before a PR

- Run the relevant tests and report their result in the PR description.
- Run `git diff --check` before committing.
- For this project, prefer validating with:
  - `python3 -m compileall -q rag_pipeline eval`
  - `docker compose config --quiet`
  - `docker compose exec -T rag-app python -m unittest discover -s tests -p 'test_*.py'`

## Change discipline

- Preserve unrelated user changes in the working tree.
- Do not use destructive Git commands such as `git reset --hard` or
  `git checkout --` without explicit user approval.
- When a task changes runtime configuration, update `.env.rag.example` with a
  safe example while keeping the real `.env.rag` local and ignored.
