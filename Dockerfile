FROM python:3.11-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "run.py" ]