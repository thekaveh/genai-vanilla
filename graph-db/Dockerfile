FROM neo4j:latest

# Copy backup and restore scripts
COPY ./scripts/backup.sh /usr/local/bin/backup.sh
COPY ./scripts/restore.sh /usr/local/bin/restore.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/backup.sh \
    && chmod +x /usr/local/bin/restore.sh

# Create backup directory
RUN mkdir -p /backups

# Set up a cron job to run backups (optional - commented out by default)
# RUN apt-get update && apt-get install -y cron \
#    && echo "0 0 * * * /usr/local/bin/backup.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/neo4j-backup \
#    && chmod 0644 /etc/cron.d/neo4j-backup \
#    && crontab /etc/cron.d/neo4j-backup

ENTRYPOINT ["tini", "-g", "--", "/startup/docker-entrypoint.sh"]
CMD ["neo4j"]