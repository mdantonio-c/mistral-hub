#!/usr/bin/env bash
# Host sampler for issue 852 benchmark campaigns (run by the human on local/dev/prod hosts).
#
# Samples host metrics (/proc) and, if the user can run docker, per-container metrics
# (docker stats) every INTERVAL seconds, tagged with a campaign_id. No root needed.
# Bounded output: stops after MAX_DURATION seconds or when the output dir exceeds MAX_MB.
#
# Usage: host_sampler.sh <campaign_id> [out_dir] [interval_s] [max_duration_s] [max_mb]
#   defaults: out_dir=/tmp/perf_issue852/<campaign_id>, interval 5 s, 4 h, 50 MB
#   container filter: env CONTAINER_FILTER (grep -E regex on container names,
#   default "observed_celery|backend|postgres")
# Stop early with Ctrl-C or `kill <pid>` (pid in <out_dir>/meta.txt); the stop is recorded.
#
# Output (TSV, UTC ISO timestamps):
#   meta.txt        campaign_id, hostname, nproc, mem total, start/stop, stop reason
#   host.tsv        ts load1 load5 cpu_user cpu_nice cpu_system cpu_idle cpu_iowait cpu_steal
#                   (cumulative jiffies) mem_available_kb swap_free_kb disk_read_sectors disk_write_sectors
#                   (cumulative, whole disks listed in meta.txt)
#   containers.tsv  ts name cpu_perc mem_usage mem_perc block_io net_io
set -u

CAMPAIGN_ID="${1:-}"
if [[ ! "$CAMPAIGN_ID" =~ ^(local|dev|prod)-[0-9]{8}-[a-z0-9][a-z0-9-]*$ ]]; then
    echo "usage: $0 <campaign_id: <env>-<yyyymmdd>-<purpose>> [out_dir] [interval_s] [max_duration_s] [max_mb]" >&2
    exit 2
fi
OUT_DIR="${2:-/tmp/perf_issue852/$CAMPAIGN_ID}"
INTERVAL="${3:-5}"
MAX_DURATION="${4:-14400}"
MAX_MB="${5:-50}"
FILTER="${CONTAINER_FILTER:-observed_celery|backend|postgres}"

mkdir -p "$OUT_DIR" || exit 2
META="$OUT_DIR/meta.txt"
HOST_TSV="$OUT_DIR/host.tsv"
CONT_TSV="$OUT_DIR/containers.tsv"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# whole disks only (no partitions, loop, ram, device-mapper, optical)
DISKS=$(ls /sys/block | grep -Ev '^(loop|ram|zram|dm-|sr|md)' | tr '\n' ' ')

USE_DOCKER=0
if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
    USE_DOCKER=1
fi

{
    echo "campaign_id=$CAMPAIGN_ID"
    echo "hostname=$(hostname)"
    echo "nproc=$(nproc)"
    echo "mem_total_kb=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
    echo "interval_s=$INTERVAL max_duration_s=$MAX_DURATION max_mb=$MAX_MB"
    echo "disks=$DISKS"
    echo "docker_stats=$USE_DOCKER container_filter=$FILTER"
    echo "pid=$$"
    echo "start=$(now)"
} >> "$META"

[[ -s "$HOST_TSV" ]] || printf 'ts\tload1\tload5\tcpu_user\tcpu_nice\tcpu_system\tcpu_idle\tcpu_iowait\tcpu_steal\tmem_available_kb\tswap_free_kb\tdisk_read_sectors\tdisk_write_sectors\n' > "$HOST_TSV"
if [[ $USE_DOCKER == 1 && ! -s "$CONT_TSV" ]]; then
    printf 'ts\tname\tcpu_perc\tmem_usage\tmem_perc\tblock_io\tnet_io\n' > "$CONT_TSV"
fi

STOP_REASON="signal"
finish() {
    echo "stop=$(now) reason=$STOP_REASON" >> "$META"
    exit 0
}
trap finish INT TERM

START_EPOCH=$(date +%s)
while true; do
    TS=$(now)
    read -r LOAD1 LOAD5 _ < /proc/loadavg
    # cpu  user nice system idle iowait irq softirq steal
    read -r _ CU CN CS CI CW _ _ CST _ < /proc/stat
    MEM=$(awk '/^MemAvailable:/ {a=$2} /^SwapFree:/ {s=$2} END {print a "\t" s}' /proc/meminfo)
    DISK=$(awk -v disks=" $DISKS " 'index(disks, " " $3 " ") {r+=$6; w+=$10} END {print r+0 "\t" w+0}' /proc/diskstats)
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$TS" "$LOAD1" "$LOAD5" "$CU" "$CN" "$CS" "$CI" "$CW" "$CST" "$MEM" "$DISK" >> "$HOST_TSV"
    if [[ $USE_DOCKER == 1 ]]; then
        docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.BlockIO}}\t{{.NetIO}}' 2>/dev/null \
            | grep -E "$FILTER" | sed "s/^/$TS\t/" >> "$CONT_TSV"
    fi

    ELAPSED=$(( $(date +%s) - START_EPOCH ))
    if (( ELAPSED >= MAX_DURATION )); then
        STOP_REASON="max_duration"; finish
    fi
    SIZE_KB=$(du -sk "$OUT_DIR" | cut -f1)
    if (( SIZE_KB >= MAX_MB * 1024 )); then
        STOP_REASON="max_size"; finish
    fi
    sleep "$INTERVAL" &
    wait $!
done
