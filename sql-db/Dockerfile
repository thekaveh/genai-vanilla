FROM postgres:16.2-bullseye

# Add scripts to image
COPY ./scripts/setup_extensions.sh /docker-entrypoint-initdb.d/01-setup_extensions.sh
COPY ./scripts/init_extensions.sql /docker-entrypoint-initdb.d/02-init_extensions.sql

# Add backup and restore scripts
COPY ./scripts/backup.sh /usr/local/bin/backup.sh
COPY ./scripts/restore.sh /usr/local/bin/restore.sh

# Make scripts executable
RUN chmod +x /docker-entrypoint-initdb.d/01-setup_extensions.sh \
    && chmod +x /usr/local/bin/backup.sh \
    && chmod +x /usr/local/bin/restore.sh

# Set up a cron job to run backups (optional - can be enabled by uncommenting)
# RUN apt-get update && apt-get install -y cron \
#    && echo "0 0 * * * /usr/local/bin/backup.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/db-backup \
#    && chmod 0644 /etc/cron.d/db-backup \
#    && crontab /etc/cron.d/db-backup

# Create backup directory
RUN mkdir -p /backups

# Set default command
CMD ["postgres"]
