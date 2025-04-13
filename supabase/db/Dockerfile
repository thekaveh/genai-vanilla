FROM supabase/postgres:15.8.1.054

# Add scripts to image
COPY ./initdb.d/init.sql /docker-entrypoint-initdb.d/02-init.sql

# Add backup and restore scripts
COPY ./scripts/backup.sh /usr/local/bin/backup.sh
COPY ./scripts/restore.sh /usr/local/bin/restore.sh
COPY ./scripts/auto_restore.sh /docker-entrypoint-initdb.d/03-auto_restore.sh

# Make scripts executable
RUN chmod +x /usr/local/bin/backup.sh \
    && chmod +x /usr/local/bin/restore.sh \
    && chmod +x /docker-entrypoint-initdb.d/03-auto_restore.sh

# Create backup directory
RUN mkdir -p /backups

# Set default command
CMD ["postgres"]
