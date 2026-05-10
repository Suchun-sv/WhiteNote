FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY . .

RUN mkdir -p /app/cache/pdfs /app/cache/imgs /app/cache/embeddings /app/logs

EXPOSE 8501 8765

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.address=0.0.0.0"]
