# Instructions for coding agents

Read README.md first, then the code. This file is the rules of engagement.

## How this repo uses AI assistance

Code here is written with AI assistance and reviewed line by line by the
owner, who must be able to explain and defend every design decision. Optimize
for the owner's understanding, not for speed: explain each change, and prefer
the simplest design that does the job.

## Hard rules

1. Never run `terraform apply`, `terraform destroy`, or any command against a
   real AWS account. Local tools, Docker Compose and moto only.
2. `infra/bootstrap/` is applied by hand. Propose changes to it; never apply
   them.
3. Never weaken a security control (auth, IAM scope, permissions boundary,
   OIDC trust conditions, quota) without saying plainly what was weakened and
   why.
4. Never put secrets, account IDs, or real emails in code or tests.
5. Never put posting text in an SQS message. IDs only.
6. Never add a dependency without stating why, and what the alternative was.
7. Before saying a change is done, run from `backend/`:
   `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
   and report the actual result. Do not claim tests pass without running them.

## How to work

- Plan first: state what will change and why before editing.
- Small diffs. One concern per commit.
- Comments say *why*, not *what*.