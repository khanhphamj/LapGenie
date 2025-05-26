FROM apache/airflow:3.0.1

# Switch to root to install system dependencies
USER root

# Install system dependencies for Playwright browsers
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Switch back to airflow user
USER airflow

# Install Playwright and additional Python dependencies
RUN pip install --no-cache-dir \
    apache-airflow-providers-neo4j==3.7.0 \
    tqdm==4.66.1 \
    playwright==1.48.0

# Install Playwright browsers
RUN python -m playwright install chromium

# Create playwright cache directory with proper permissions
RUN mkdir -p /opt/airflow/.cache/ms-playwright 