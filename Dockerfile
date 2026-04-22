# Use standard Python 3.10
FROM python:3.10-slim

# Install latest Chromium and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    procps \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Enforce environment paths
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
