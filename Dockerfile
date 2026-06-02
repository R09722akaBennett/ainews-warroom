FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Taipei

# System deps:
#   git  — entrypoint clones target repo + pushes site data
#   gcloud CLI — entrypoint syncs warroom.db with GCS
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      apt-transport-https ca-certificates gnupg curl git tzdata \
 && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
      | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
      > /etc/apt/sources.list.d/google-cloud-sdk.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends google-cloud-cli \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# export/site.py writes to pipeline/../src/data/ — make sure it exists
RUN mkdir -p /app/src/data

COPY pipeline/pyproject.toml pipeline/uv.lock ./pipeline/
RUN cd pipeline && uv sync --frozen --no-dev

COPY pipeline/ ./pipeline/

COPY bin/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
