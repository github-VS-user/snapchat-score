FROM python:3.10-slim

# 1. Install Chromium + ALL required dependencies for stability
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    jq \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# 2. Set environment variables explicitly
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 3. Python Setup
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000

# 4. Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
