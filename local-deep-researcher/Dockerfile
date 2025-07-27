ARG BASE_IMAGE=${LOCAL_DEEP_RESEARCHER_IMAGE:-python:3.11-slim}
FROM ${BASE_IMAGE}

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install uv

# Clone the Local Deep Researcher repository
RUN git clone https://github.com/langchain-ai/local-deep-researcher.git /tmp/local-deep-researcher && \
    cp -r /tmp/local-deep-researcher/* /app/ && \
    rm -rf /tmp/local-deep-researcher

# Install Python dependencies using uv
RUN uv pip install --system -r pyproject.toml

# Install additional dependencies for our custom integration scripts
RUN uv pip install --system psycopg2-binary

# Create necessary directories
RUN mkdir -p /app/data /app/config

# Copy initialization scripts
COPY scripts/ /app/scripts/
COPY config/ /app/config/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py

# Create healthcheck script
RUN echo '#!/bin/bash\ncurl -f http://localhost:2024/health || exit 1' > /app/scripts/healthcheck.sh && \
    chmod +x /app/scripts/healthcheck.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 2024

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/scripts/healthcheck.sh

# Run initialization and start the service
CMD ["/app/scripts/docker-entrypoint.sh"]
