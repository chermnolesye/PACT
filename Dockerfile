ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV HF_HOME=/app/model_cache

WORKDIR /app

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN apt-get update && apt-get install -y \
    pkg-config \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

RUN python -c "import nltk; nltk.download('punkt_tab', download_dir='/usr/local/share/nltk_data')"

RUN python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; \
    AutoTokenizer.from_pretrained('gpt2'); \
    AutoModelForCausalLM.from_pretrained('gpt2'); \
    AutoTokenizer.from_pretrained('dbddv01/gpt2-french-small'); \
    AutoModelForCausalLM.from_pretrained('dbddv01/gpt2-french-small'); \
    AutoTokenizer.from_pretrained('stefan-it/german-gpt2-larger'); \
    AutoModelForCausalLM.from_pretrained('stefan-it/german-gpt2-larger')"

RUN chmod -R 777 /app/model_cache

USER appuser

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]