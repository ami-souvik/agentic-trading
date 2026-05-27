FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN mkdir trader && touch trader/__init__.py && pip install --no-cache-dir .

COPY trader/ ./trader/
RUN pip install --no-cache-dir --no-deps .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "trader.daily_run"]
