# Setup: from clean clone to deployed

Follow in order. Each step ends with a check; do not move on until it passes.

## 0. Prerequisites

- Linux or macOS. On Windows, use WSL2 and keep the repo inside the Linux
  filesystem (`~/...`, not `/mnt/c/...`).
- AWS CLI v2, Terraform 1.17.x, uv 0.13.x, the GitHub CLI, and Docker.
- An AWS account with an IAM Identity Center admin user (not the root user)
  and a CLI profile for it:

  ```bash
  aws configure sso            # name the profile triage-admin
  export AWS_PROFILE=triage-admin
  aws sts get-caller-identity  # must show the SSO role, not root
  ```

## 1. Run it locally

```bash
cd backend
uv sync --locked
uv run ruff check . && uv run pyright && uv run pytest
cd ..
docker compose up --build
```

In another terminal:

```bash
curl localhost:8080/health
# {"status":"ok","version":"local"}

cd backend
uv run python scripts/send_test_message.py
```

**Check:** the `worker` container logs `received work message`.

Failure handling:

```bash
uv run python scripts/send_test_message.py --malformed
```

**Check:** the worker logs `malformed work message` three times, about 30 s
apart, then stops. The message is now in the dead-letter queue:

```bash
AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local aws sqs get-queue-attributes \
  --endpoint-url http://localhost:9324 --region us-east-1 \
  --queue-url http://localhost:9324/000000000000/triage-work-dlq \
  --attribute-names ApproximateNumberOfMessages
```

## 2. Push to GitHub

Create an empty repository and push to `main`. The `deploy` workflow runs the
CI jobs; the Terraform plan step and the deploy job skip themselves because
the repository variables do not exist yet.

**Check:** the workflow run is green.

## 3. Bootstrap AWS (once, by hand)

The deploy role trusts exactly one repository, identified by the prefix of
the OIDC `sub` claim GitHub issues for it. Ask GitHub for that prefix:

```bash
gh api repos/OWNER/REPO/actions/oidc/customization/sub
```

Then:

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # set github_sub_prefix
terraform init
terraform plan        # read every resource before applying
terraform apply
terraform output
```

`terraform.tfstate` for this stack stays on the machine that applied it
(gitignored). Back it up; losing it is recoverable with `terraform import`,
but tedious.

## 4. Configure GitHub

Settings → Secrets and variables → Actions → **Variables** (none of these
are secret):

| Variable | Value |
|---|---|
| `AWS_REGION` | `aws_region` output |
| `AWS_PLAN_ROLE_ARN` | `plan_role_arn` output |
| `AWS_DEPLOY_ROLE_ARN` | `deploy_role_arn` output |
| `TF_STATE_BUCKET` | `tf_state_bucket` output |
| `ALERT_EMAIL` | where alarms and budget alerts go |

Settings → Branches → add a protection rule for `main`:

- Require a pull request before merging (no required approvals for a solo
  repository).
- Require these status checks, picked from the search box so the names match
  exactly:
  - `backend (lint, types, tests)`
  - `repo scan (dependencies, secrets, IaC)`
  - `images (build + scan) (api)`
  - `images (build + scan) (worker)`
  - `terraform (fmt, validate, plan)`
- Block force pushes.

Settings → Code security: turn on secret scanning and push protection.

## 5. First deploy

Open a small pull request. **Check:** CI is green and the `terraform` job
summary lists the planned resources.

Merge it. The `deploy` workflow re-runs the tests, builds both images, scans
them, pushes them, applies Terraform with the image digests, and smoke-tests
`/health`.

**Check:**

- The smoke test step passed and printed the merged commit SHA.
- An "AWS Notification - Subscription Confirmation" email arrived. Confirm
  it, or alarms go nowhere.

## 6. Verify the worker in AWS

```bash
QUEUE_URL=$(aws sqs get-queue-url --queue-name triage-work --query QueueUrl --output text)
aws sqs send-message --queue-url "$QUEUE_URL" \
  --message-body '{"user_sub":"smoke","posting_id":"01J9Z3K8Q5V7X2M4N6P8R0T2W4"}'
aws logs tail /aws/lambda/triage-worker --follow
```

**Check:** a structured JSON log line with `received work message`.

Optional, slow: send a malformed body. With the production 30-minute
visibility timeout it reaches the DLQ after about 90 minutes, and the alarm
sends an email. This proves the alerting path end to end.

## Troubleshooting

**`Not authorized to perform sts:AssumeRoleWithWebIdentity`.** The OIDC `sub`
claim did not match the trust policy. Re-run the `gh api` command from step 3
and compare it with `github_sub_prefix`. Adding `environment:` to a workflow
job also changes the claim; see `infra/bootstrap/oidc.tf`.

**`EntityAlreadyExists` for the OIDC provider.** The account already has a
GitHub provider. Import it rather than create a second:
`terraform import aws_iam_openid_connect_provider.github arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com`

**`AccessDenied` on `iam:CreateRole` during deploy.** The role is missing
`permissions_boundary = local.boundary_arn`, or its name does not start with
the project prefix. Both are required by design.

**Lambda rejects the image: "image manifest ... media type is not
supported".** The image was built without `--provenance=false`.

**Lambda fails with `exec format error`.** The image was built for the wrong
CPU architecture. Always build with `--platform linux/amd64`.

**A feature needs a new AWS action and gets `AccessDenied` at runtime.** The
workload boundary does not allow it. Widen `infra/bootstrap/boundary.tf` and
re-apply bootstrap by hand.

## Teardown

From the admin profile: empty the ECR repositories, then destroy `infra/main`
(it needs the same variables CI passes). In bootstrap, remove
`prevent_destroy` from the state bucket, empty the bucket, and run
`terraform destroy`.