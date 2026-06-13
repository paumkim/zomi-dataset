#!/bin/bash
# Pau Training Watchdog — auto-restarts training if it crashes
# Deploy on the training pod

CHECK_INTERVAL=60       # Check every 60 seconds
TRAIN_SCRIPT="/workspace/cloud_train.py"
TRAIN_LOG="/workspace/training.log"
PID_FILE="/workspace/.train_pid"
WATCHDOG_LOG="/workspace/watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$WATCHDOG_LOG"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

is_training() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            return 0  # running
        fi
    fi
    # Also check by process name
    if pgrep -f "python.*cloud_train.py" > /dev/null 2>&1; then
        PID=$(pgrep -f "python.*cloud_train.py" | head -1)
        echo "$PID" > "$PID_FILE"
        return 0
    fi
    return 1  # not running
}

start_training() {
    cd /workspace || return 1
    rm -f training.log
    nohup python cloud_train.py > training.log 2>&1 &
    PID=$!
    echo "$PID" > "$PID_FILE"
    log "Training started (PID: $PID)"
}

check_progress() {
    if [ -f "$TRAIN_LOG" ]; then
        LAST_LINE=$(tail -1 "$TRAIN_LOG" 2>/dev/null)
        # Check if there's a new checkpoint
        LATEST_CKPT=$(ls -d /workspace/zomi-qlora-v1/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
        if [ -n "$LATEST_CKPT" ]; then
            STEP=$(echo "$LATEST_CKPT" | grep -oP '\d+$')
            log "Latest checkpoint: step $STEP"
        fi
    fi
}

log "=== Watchdog started ==="
log "Check interval: ${CHECK_INTERVAL}s"

while true; do
    if ! is_training; then
        log "Training not running. Checking checkpoint..."
        LATEST_CKPT=$(ls -d /workspace/zomi-qlora-v1/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
        if [ -n "$LATEST_CKPT" ]; then
            log "Resuming from $LATEST_CKPT"
        else
            log "No checkpoint found. Starting fresh."
        fi
        start_training
    else
        check_progress
    fi
    sleep "$CHECK_INTERVAL"
done
