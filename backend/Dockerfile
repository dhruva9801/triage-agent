# syntax=docker/dockerfile:1
#
# One Dockerfile, two deployable targets:
#   api     python:3.12-slim + Lambda Web Adapter. The same image runs uvicorn
#           under Docker Compose and on Lambda.
#   worker  AWS Lambda Python base image, for the SQS-triggered worker.
#
# FROM lines use literal image references (not ARGs) so Dependabot can see and
# bump them. Pin each to a digest after your first pull:
#   docker pull python:3.12-slim-bookworm
#   docker inspect --format '{{index .RepoDigests 0}}' python:3.12-slim-bookworm
# then write FROM python:3.12-slim-bookworm@sha256:<digest>.

FROM ghcr.io/astral-sh/uv:0.13.8 AS uv
FROM public.ecr.aws/awsguru/aws-lambda-adapter:1.0.1 AS lwa

# ---- Export the locked, production-only dependency set (with hashes) --------
FROM python:3.12-slim-bookworm AS export
COPY --from=uv /uv /bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project -o requirements.txt

# ---- Install deps for the api image (Debian userland) -------------------------
FROM python:3.12-slim-bookworm AS api-deps
COPY --from=uv /uv /bin/uv
COPY --from=export /build/requirements.txt /tmp/requirements.txt
RUN uv pip install --no-cache --require-hashes --target /opt/deps -r /tmp/requirements.txt

# ---- Install deps for the worker image -----------------------------------------
# Installed inside the Lambda base image itself, so compiled wheels match the
# Lambda OS (Amazon Linux) rather than Debian.
FROM public.ecr.aws/lambda/python:3.12 AS worker-deps
COPY --from=uv /uv /bin/uv
COPY --from=export /build/requirements.txt /tmp/requirements.txt
RUN uv pip install --no-cache --require-hashes --python /var/lang/bin/python3 \
      --target /opt/deps -r /tmp/requirements.txt

# ---- api target -------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS api
ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/deps:/app/src \
    GIT_SHA=${GIT_SHA} \
    AWS_LWA_PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/health
# The adapter is a Lambda extension: inert under Docker, active on Lambda.
COPY --from=lwa /lambda-adapter /opt/extensions/lambda-adapter
COPY --from=api-deps /opt/deps /opt/deps
COPY src /app/src
RUN useradd --system --no-create-home --uid 10001 app
USER app
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "triage.api.app:app", "--host", "0.0.0.0", "--port", "8080"]

# ---- worker target ----------------------------------------------------------------
FROM public.ecr.aws/lambda/python:3.12 AS worker
ARG GIT_SHA=dev
# The Lambda base image lags behind Amazon Linux security fixes, so pull them
# in at build time. The runtime interface emulator is a Go binary used only to
# run this image outside Lambda; it never runs in AWS, so remove it rather
# than ship its CVEs.
RUN dnf -y upgrade --releasever=latest \
    && dnf clean all \
    && rm -f /usr/local/bin/aws-lambda-rie
ENV PYTHONDONTWRITEBYTECODE=1 \
    GIT_SHA=${GIT_SHA}
COPY --from=worker-deps /opt/deps ${LAMBDA_TASK_ROOT}
COPY src/triage ${LAMBDA_TASK_ROOT}/triage
CMD ["triage.worker.handler.handler"]
