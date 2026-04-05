#!/bin/bash
# PEACOCK ENGINE - Backup Script
# Backs up database and important files

set -e

BACKUP_DIR="/opt/peacock-engine/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="peacock_backup_$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "🦚 PEACOCK ENGINE Backup"
echo "========================"
echo "Creating backup: $BACKUP_NAME"

# Create temp directory
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

# Copy files
cp /opt/peacock-engine/peacock.db "$TMP_DIR/" 2>/dev/null || echo "⚠️ Database not found"
cp /opt/peacock-engine/.env "$TMP_DIR/" 2>/dev/null || echo "⚠️ .env not found"
cp -r /opt/peacock-engine/vault "$TMP_DIR/" 2>/dev/null || echo "⚠️ Vault not found"

# Create tar archive
tar -czf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" -C "$TMP_DIR" .

# Clean old backups (keep last 30)
ls -1t "$BACKUP_DIR"/peacock_backup_*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm

echo ""
echo "✅ Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo "📊 Backup size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)"
echo "📁 Total backups: $(ls -1 "$BACKUP_DIR"/peacock_backup_*.tar.gz 2>/dev/null | wc -l)"
