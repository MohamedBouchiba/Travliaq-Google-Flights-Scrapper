#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/home/ubuntu/backups"
DB_FILE="/home/ubuntu/Travliaq-Google-Flights-Scrapper/data/flights.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/flights_$DATE.db"

mkdir -p $BACKUP_DIR

# Backup
cp $DB_FILE $BACKUP_FILE
gzip $BACKUP_FILE

# Garder seulement les 7 derniers backups
ls -t $BACKUP_DIR/flights_*.db.gz | tail -n +8 | xargs -r rm

echo "✅ Backup créé: $BACKUP_FILE.gz"

# Nettoyer les vieux backups (>7 jours)
find $BACKUP_DIR -name "flights_*.db.gz" -mtime +7 -delete