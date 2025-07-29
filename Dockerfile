FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
      netcat-openbsd \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY scripts/run_prod.sh /app/run_prod.sh
RUN chmod +x /app/run_prod.sh

ENTRYPOINT ["/app/run_prod.sh"]
