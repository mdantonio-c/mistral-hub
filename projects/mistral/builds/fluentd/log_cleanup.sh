#!/bin/bash

# Fluentd Log Cleanup Script
# This script monitors and limits the size of logs in /var/log/fluentd

# Configuration
LOG_DIR="/var/log/fluentd"
MAX_TOTAL_SIZE_GB=4                    # Maximum total size in GB (leave 1GB buffer from our 5GB config)
MAX_FILE_AGE_DAYS=7                    # Delete files older than this many days
BUFFER_DIR="$LOG_DIR/buffer"
CHECK_INTERVAL=300                     # Check every 5 minutes (300 seconds)

# Convert GB to bytes for calculations
MAX_TOTAL_SIZE_BYTES=$((MAX_TOTAL_SIZE_GB * 1024 * 1024 * 1024))

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to get directory size in bytes
get_dir_size() {
    local dir="$1"
    if [ -d "$dir" ]; then
        du -sb "$dir" 2>/dev/null | cut -f1
    else
        echo "0"
    fi
}

# Function to clean old files
clean_old_files() {
    local target_dir="$1"
    local days="$2"
    
    if [ -d "$target_dir" ]; then
        log_message "Cleaning files older than $days days in $target_dir"
        find "$target_dir" -type f -mtime +$days -exec rm -f {} \; 2>/dev/null
        local deleted_count=$(find "$target_dir" -type f -mtime +$days 2>/dev/null | wc -l)
        if [ $deleted_count -gt 0 ]; then
            log_message "Deleted $deleted_count old files from $target_dir"
        fi
    fi
}

# Function to clean by size (remove oldest files first)
clean_by_size() {
    local current_size="$1"
    local target_reduction=$((current_size - MAX_TOTAL_SIZE_BYTES))
    
    log_message "Current size: $(($current_size / 1024 / 1024))MB, need to free: $(($target_reduction / 1024 / 1024))MB"
    
    # Remove oldest log files first (not buffer files)
    if [ -d "$LOG_DIR" ]; then
        # Find and remove oldest log files (excluding buffer directory)
        find "$LOG_DIR" -type f -name "*.log*" -not -path "$BUFFER_DIR/*" -printf '%T@ %s %p\n' | \
        sort -n | \
        while read timestamp size filepath; do
            if [ $target_reduction -le 0 ]; then
                break
            fi
            
            rm -f "$filepath" 2>/dev/null
            if [ $? -eq 0 ]; then
                log_message "Removed old log file: $(basename "$filepath") ($(($size / 1024 / 1024))MB)"
                target_reduction=$((target_reduction - size))
            fi
        done
    fi
    
    # If still over limit, clean some buffer files (oldest first)
    current_size=$(get_dir_size "$LOG_DIR")
    if [ $current_size -gt $MAX_TOTAL_SIZE_BYTES ]; then
        target_reduction=$((current_size - MAX_TOTAL_SIZE_BYTES))
        log_message "Still over limit, cleaning buffer files. Need to free: $(($target_reduction / 1024 / 1024))MB"
        
        find "$BUFFER_DIR" -type f -printf '%T@ %s %p\n' 2>/dev/null | \
        sort -n | \
        while read timestamp size filepath; do
            if [ $target_reduction -le 0 ]; then
                break
            fi
            
            rm -f "$filepath" 2>/dev/null
            if [ $? -eq 0 ]; then
                log_message "Removed buffer file: $(basename "$filepath") ($(($size / 1024 / 1024))MB)"
                target_reduction=$((target_reduction - size))
            fi
        done
    fi
}

# Function to perform cleanup
perform_cleanup() {
    log_message "Starting log directory cleanup check"
    
    # Ensure directories exist
    mkdir -p "$LOG_DIR" "$BUFFER_DIR"
    
    # Get current total size
    current_size=$(get_dir_size "$LOG_DIR")
    current_size_mb=$(($current_size / 1024 / 1024))
    max_size_mb=$(($MAX_TOTAL_SIZE_BYTES / 1024 / 1024))
    
    log_message "Current log directory size: ${current_size_mb}MB (limit: ${max_size_mb}MB)"
    
    # Clean old files first
    clean_old_files "$LOG_DIR" $MAX_FILE_AGE_DAYS
    
    # Check size after cleaning old files
    current_size=$(get_dir_size "$LOG_DIR")
    
    # If still over size limit, clean by size
    if [ $current_size -gt $MAX_TOTAL_SIZE_BYTES ]; then
        log_message "Directory still over size limit, cleaning by size"
        clean_by_size $current_size
    else
        log_message "Directory size within limits"
    fi
    
    # Final size check
    final_size=$(get_dir_size "$LOG_DIR")
    final_size_mb=$(($final_size / 1024 / 1024))
    log_message "Cleanup completed. Final size: ${final_size_mb}MB"
}

# Main execution
if [ "$1" = "--daemon" ]; then
    log_message "Starting log cleanup daemon (checking every ${CHECK_INTERVAL} seconds)"
    while true; do
        perform_cleanup
        sleep $CHECK_INTERVAL
    done
else
    # Run once
    perform_cleanup
fi