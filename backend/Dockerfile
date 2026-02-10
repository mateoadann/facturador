FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    pkg-config \
    libcairo2-dev \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libasound2 \
    libpango-1.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxshmfence1 \
    libxext6 \
    libx11-6 \
    libxcb1 \
    libxrender1 \
    libxi6 \
    libxtst6 \
    libegl1 \
    libgles2 \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium for Playwright PDF rendering
RUN python -m playwright install chromium

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]
