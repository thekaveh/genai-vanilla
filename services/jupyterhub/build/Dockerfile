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

# PyG family packages (torch-scatter, torch-sparse, etc.) use legacy setup.py builds
# that require `torch` to be importable at metadata-generation time. Install torch
# first so pip can resolve those packages' build dependencies.
RUN pip install --no-cache-dir torch==2.4.1  # keep in sync with requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ml-lab NLP-task assets: spaCy language model + NLTK VADER lexicon. These are
# bundled separately from their respective pip packages (spacy / nltk) and are
# required by ml-lab's text_classification-agnews + sentiment_classification-vader
# Tier-A notebooks. ~14 MB total.
RUN python -m spacy download en_core_web_sm \
 && python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

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
