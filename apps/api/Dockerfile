FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src/cataloging_api/__init__.py ./src/cataloging_api/__init__.py
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir ".[dev]"
COPY src ./src
COPY tests ./tests
COPY alembic.ini ./
COPY migrations ./migrations
RUN pip install --no-cache-dir --no-deps .

CMD ["sh", "-c", "alembic upgrade head && uvicorn cataloging_api.main:app --host 0.0.0.0 --port 8000"]
