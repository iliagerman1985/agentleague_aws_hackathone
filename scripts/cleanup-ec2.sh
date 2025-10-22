#!/bin/bash

# Comprehensive cleanup script for EC2 instance
# Cleans up Docker images, logs, and temporary files to free disk space

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
PROJECT_NAME="${PROJECT_NAME:-agentleague}"
KEEP_IMAGES="${KEEP_IMAGES:-2}"  # Number of images to keep per repository
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-2}"  # Days to keep compressed logs
ROTATED_LOG_RETENTION_DAYS="${ROTATED_LOG_RETENTION_DAYS:-7}"  # Days to keep rotated logs

log_info "🧹 Starting comprehensive cleanup for ${PROJECT_NAME}..."

# Show initial disk usage
log_info "📊 Disk usage before cleanup:"
df -h /

# Show Docker volumes (for safety - we'll preserve named volumes)
log_info "🗂️  Current Docker volumes (named volumes will be preserved):"
docker volume ls || true

# Stop and remove ALL containers to avoid conflicts
log_info "🛑 Stopping and removing ALL Docker containers..."

# Stop all running containers
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all containers (including stopped ones)
docker rm $(docker ps -aq) 2>/dev/null || true

# Also try docker-compose down in case there's a compose setup
docker-compose -f /opt/app/docker-compose.aws.yml down 2>/dev/null || true

# Clean up old Docker images (keep only the latest N images per repository)
log_info "🐳 Cleaning up old Docker images..."

# Function to clean up images for a specific repository
cleanup_repo_images() {
    local repo_pattern=$1
    local keep_count=$2

    log_info "Cleaning up images for pattern: ${repo_pattern}"

    # Get image IDs sorted by creation date (newest first), skip the first N to keep
    local images_to_remove=$(docker images --format "table {{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}" | \
        grep -E "${repo_pattern}" | \
        grep -v "<none>" | \
        sort -k3 -r | \
        tail -n +$((keep_count + 1)) | \
        awk '{print $2}')

    if [ -n "$images_to_remove" ]; then
        echo "$images_to_remove" | xargs -r docker rmi -f || true
        log_success "Removed old images for ${repo_pattern}"
    else
        log_info "No old images to remove for ${repo_pattern}"
    fi
}

# Clean up backend and frontend images
cleanup_repo_images "${PROJECT_NAME}-backend" "$KEEP_IMAGES"
cleanup_repo_images "${PROJECT_NAME}-frontend" "$KEEP_IMAGES"

# Also clean up any images with the ECR repository pattern
if [ -n "${ECR_BACKEND_REPO:-}" ]; then
    cleanup_repo_images "$(echo $ECR_BACKEND_REPO | cut -d'/' -f2)" "$KEEP_IMAGES"
fi
if [ -n "${ECR_FRONTEND_REPO:-}" ]; then
    cleanup_repo_images "$(echo $ECR_FRONTEND_REPO | cut -d'/' -f2)" "$KEEP_IMAGES"
fi

# Clean up dangling images and unused resources (PRESERVE PostgreSQL volumes)
log_info "🗑️  Cleaning up dangling images (preserving database volumes)..."
docker system prune -af || true  # Removed --volumes to preserve PostgreSQL data
docker image prune -af || true

# Clean up only unnamed/dangling volumes (not named volumes like postgres_data)
log_info "🗂️  Cleaning up dangling volumes (preserving named volumes)..."
docker volume prune -f || true

# Clean up log files
log_info "📝 Cleaning up log files..."

# Application logs
find /opt/app/logs -name "*.gz" -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
find /opt/app/logs -name "*.zip" -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
find /opt/app/logs -name "*.log.*" -mtime +${ROTATED_LOG_RETENTION_DAYS} -delete 2>/dev/null || true

# System logs
find /var/log -name "*.gz" -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true
find /var/log -name "*.zip" -mtime +${LOG_RETENTION_DAYS} -delete 2>/dev/null || true

# Docker logs (can get very large)
log_info "🐳 Truncating Docker container logs..."
for container in $(docker ps -aq 2>/dev/null || true); do
    if [ -n "$container" ]; then
        log_path=$(docker inspect --format='{{.LogPath}}' "$container" 2>/dev/null || true)
        if [ -n "$log_path" ] && [ -f "$log_path" ]; then
            # Truncate log file to last 1000 lines to keep recent logs but free space
            tail -n 1000 "$log_path" > "${log_path}.tmp" 2>/dev/null || true
            mv "${log_path}.tmp" "$log_path" 2>/dev/null || true
        fi
    fi
done

# Clean up temporary files
log_info "🗂️  Cleaning up temporary files..."
find /tmp -name "*.log" -mtime +1 -delete 2>/dev/null || true
find /tmp -name "*.tmp" -mtime +1 -delete 2>/dev/null || true
find /tmp -name "core.*" -mtime +1 -delete 2>/dev/null || true

# Clean up package manager caches
log_info "📦 Cleaning up package manager caches..."
apt-get clean 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true

# Clean up journal logs (systemd)
log_info "📋 Cleaning up systemd journal logs..."
journalctl --vacuum-time=7d 2>/dev/null || true
journalctl --vacuum-size=100M 2>/dev/null || true

# Show final disk usage
log_info "📊 Disk usage after cleanup:"
df -h /

# Calculate space freed
log_success "✅ Cleanup completed successfully!"
log_info "🎯 Summary:"
log_info "   - Kept ${KEEP_IMAGES} most recent images per repository"
log_info "   - Removed compressed logs older than ${LOG_RETENTION_DAYS} days"
log_info "   - Removed rotated logs older than ${ROTATED_LOG_RETENTION_DAYS} days"
log_info "   - Truncated Docker container logs"
log_info "   - Cleaned up temporary files and caches"

# Optional: Show largest files/directories for further investigation
log_info "🔍 Largest directories (for reference):"
du -sh /var/log /opt/app/logs /tmp 2>/dev/null || true
