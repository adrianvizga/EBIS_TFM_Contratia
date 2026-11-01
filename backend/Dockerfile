# syntax=docker/dockerfile:1
FROM python:3.11.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd --gid 10001 contratia \
    && useradd --uid 10001 --gid contratia --create-home contratia \
    && mkdir -p /uploads \
    && chown -R contratia:contratia /uploads

COPY requirements.txt .
RUN --mount=type=secret,id=host_ca,required=false \
    if [ -s /run/secrets/host_ca ]; then export PIP_CERT=/run/secrets/host_ca; fi \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=contratia:contratia . .

USER contratia
EXPOSE 8000
CMD [python, -m, uvicorn, app:app, --host, 0.0.0.0, --port, 8000]
