ARG BASE_IMAGE=jupyter/datascience-notebook:latest
FROM ${BASE_IMAGE}

# Switch to root to install system packages
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Switch back to jovyan user for Python package installation
USER ${NB_UID}

WORKDIR /home/jovyan

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy startup script
COPY scripts/startup.sh /usr/local/bin/startup.sh

# Switch to root to make startup script executable
USER root
RUN chmod +x /usr/local/bin/startup.sh

# Create directories for notebooks and shared config
RUN mkdir -p /home/jovyan/work \
    /home/jovyan/notebooks \
    /shared && \
    chown -R ${NB_UID}:${NB_GID} /home/jovyan/work /home/jovyan/notebooks

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8888/api || exit 1

# Switch back to jovyan user
USER ${NB_UID}

# Set working directory
WORKDIR /home/jovyan/work

# Expose Jupyter port
EXPOSE 8888

# Use startup script as entrypoint
ENTRYPOINT ["/usr/local/bin/startup.sh"]
CMD ["start-notebook.sh"]
