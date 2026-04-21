ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TRANSFORMERS_CACHE=/app/model_cache
ENV HF_HOME=/app/model_cache

ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ENV PIP_INDEX_URL=$PIP_INDEX_URL
ENV PIP_TRUSTED_HOST=$PIP_TRUSTED_HOST

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
    default-libmysqlclient-dev perl-modules \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN env
RUN python -m pip install -r requirements.txt

RUN python -c "import nltk; nltk.download('punkt_tab', download_dir='/usr/local/share/nltk_data')"

RUN python -c "from transformers import AutoTokenizer, AutoModelForCausalLM; \
    AutoTokenizer.from_pretrained('gpt2'); \
    AutoModelForCausalLM.from_pretrained('gpt2'); \
    AutoTokenizer.from_pretrained('dbddv01/gpt2-french-small'); \
    AutoModelForCausalLM.from_pretrained('dbddv01/gpt2-french-small'); \
    AutoTokenizer.from_pretrained('stefan-it/german-gpt2-larger'); \
    AutoModelForCausalLM.from_pretrained('stefan-it/german-gpt2-larger')"

RUN chmod -R 777 /app/model_cache && mkdir /app/_rftagger_tmp && chown appuser:appuser /app/_rftagger_tmp


USER appuser

COPY . .

EXPOSE 8000

ENTRYPOINT ["/app/cicd/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
