FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 sentry && chown -R sentry:sentry /app
USER sentry

# Default: check logs every 60 seconds
CMD ["python", "sentry.py", "--interval", "60"]