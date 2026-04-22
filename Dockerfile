FROM python:3.10-slim

# 1. Install Chromium + Modern Dependencies (Updated for Debian 12)
# Removed: libgconf-2-4 (Deprecated)
# Added: libgbm1, libgtk-3-0 (Required for Headless Chrome)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    jq \
    libnss3 \
    libxss1 \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    libatk-bridge2.0-0 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 2. Enforce Paths
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 3. Setup App
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000

# 4. Launch
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
