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

RUN python3 -m venv /venv
RUN /venv/bin/pip install --upgrade pip
RUN /venv/bin/pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/venv/bin:$PATH"

COPY . /app/

CMD ["/venv/bin/python", "manage.py", "runserver", "0.0.0.0:8000"]