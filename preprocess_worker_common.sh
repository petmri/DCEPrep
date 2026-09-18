#!/bin/bash

WORKER_POLL_INTERVAL_SECONDS="${WORKER_POLL_INTERVAL_SECONDS:-1}"

wait_for_job_slot() {
	if [ "$MAX_PARALLEL_JOBS" -le 0 ]; then
		return 0
	fi

	while [ "$(jobs -pr | wc -l)" -ge "$MAX_PARALLEL_JOBS" ]; do
		wait -n
	done
}

start_background_job() {
	wait_for_job_slot || return 1
	"$@" &
}

log_worker() {
	echo "$1" >> "$LOG_FILE"
}

mark_worker_done() {
	touch "$WORKER_STATUS_DIR/$1.done"
}

mark_worker_failed() {
	local worker_name=$1
	local message=$2

	log_worker "$message"
	touch "$WORKER_STATUS_DIR/$worker_name.failed"
	exit 1
}

wait_for_file() {
	local file_path=$1
	local timeout_seconds=${2:-$WORKER_WAIT_TIMEOUT_SECONDS}
	local peer_failed_marker=$3
	local start_seconds=$SECONDS

	while [ ! -f "$file_path" ]; do
		if [ -n "$peer_failed_marker" ] && [ -f "$WORKER_STATUS_DIR/$peer_failed_marker" ]; then
			return 2
		fi
		if [ $((SECONDS - start_seconds)) -ge "$timeout_seconds" ]; then
			return 1
		fi
		sleep "$WORKER_POLL_INTERVAL_SECONDS"
	done
}