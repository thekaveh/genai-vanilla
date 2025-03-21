FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy requirements first for better layer caching
COPY ./app/requirements.txt .

# Install dependencies using uv with --system flag
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health').raise_for_status()"

# Expose API port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]