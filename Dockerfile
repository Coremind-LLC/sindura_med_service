FROM python:3.12.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    apt-utils \
    gnupg \
    dirmngr \
    curl \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --chown=app:app . .

RUN mkdir -p /app/logs /app/media /app/static \
    && chown -R app:app /app/logs /app/media /app/static

USER app

CMD ["sh", "-c", \
    "python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${WORKER_COUNT:-9} --worker-class gthread --threads ${THREAD_COUNT:-4} --timeout 120 ${APPLICATION:-config.wsgi:application}"]
