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

# Send all of this worker's tool output (stdout and stderr) to a per-session log
# instead of the terminal or /dev/null, so failures can be traced afterwards.
init_worker_log() {
	mkdir -p "$SUBJECT_TP_PATH/logs"
	WORKER_LOG="$SUBJECT_TP_PATH/logs/${PREFIX}_preprocess_$1.log"
	echo "=== $(date) $1 worker ===" > "$WORKER_LOG"
	exec >> "$WORKER_LOG" 2>&1
}

# Current step label, shown on preprocess_all.sh's progress line
set_worker_step() {
	echo "$2" > "$WORKER_STATUS_DIR/$1.step"
}

mark_worker_done() {
	touch "$WORKER_STATUS_DIR/$1.done"
}

mark_worker_ready() {
	touch "$WORKER_STATUS_DIR/$1.ready"
}

mark_worker_failed() {
	local worker_name=$1
	local message=$2

	log_worker "$message"
	if [ -n "$WORKER_LOG" ]; then
		log_worker "  Worker log: $WORKER_LOG (last 20 lines below)"
		tail -n 20 "$WORKER_LOG" | sed 's/^/    | /' >> "$LOG_FILE"
	fi
	# preprocess_all.sh reads the message back to report it on the terminal
	echo "$message" > "$WORKER_STATUS_DIR/$worker_name.failed"
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