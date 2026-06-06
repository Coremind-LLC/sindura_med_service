FROM python:3.12.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Ulaanbaatar

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    apt-utils \
    gnupg \
    dirmngr \
    curl \
    tzdata \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . .

CMD ["sh", "-c", \
    "python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    python manage.py crontab remove; \
    python manage.py crontab add && \
    service cron start && \
    exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${WORKER_COUNT:-9} --worker-class gthread --threads ${THREAD_COUNT:-4} --timeout 120 ${APPLICATION:-config.wsgi:application}"]