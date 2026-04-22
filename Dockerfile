FROM python:3.10-slim

# Install specific compatible versions
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    procps \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Force Python to see the correct binary locations
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
