#!/bin/bash
# Per-session locks so several machines can process one dataset at once.
# Sourced by preprocess_all.sh and DCE_all.sh; both use the same lock file name, so a
# session is never preprocessed on one machine while being analyzed on another.
#
# The lock file holds "host:pid" and its mtime is refreshed while held. A lock is stale if
# its process is gone (same host) or it hasn't been refreshed in SESSION_LOCK_STALE_SECONDS
# (other hosts). Ages use the share's clock, since machine and file server clocks can differ.

SESSION_LOCK_NAME=dceprep_lock.txt
SESSION_LOCK_HEARTBEAT_SECONDS=${SESSION_LOCK_HEARTBEAT_SECONDS:-60}
SESSION_LOCK_STALE_SECONDS=${SESSION_LOCK_STALE_SECONDS:-600}
SESSION_LOCK_OWNER="$(hostname):$$"
HELD_LOCK=""
HELD_LOCK_HEARTBEAT_PID=""

# Current time according to the file server holding $1
share_now() {
	local probe="$1/.lock_clock_${SESSION_LOCK_OWNER//:/_}"
	touch "$probe" && stat -c %Y "$probe" && rm -f "$probe"
}

# Lock the session directory $1. Returns 1 if another live process holds it.
acquire_session_lock() {
	local dir=$1
	local lock="$dir/$SESSION_LOCK_NAME"
	local owner owner_host owner_pid age

	release_session_lock
	if ! ( set -o noclobber; echo "$SESSION_LOCK_OWNER" > "$lock" ) 2> /dev/null; then
		owner=$(cat "$lock" 2> /dev/null)
		owner_host=${owner%%:*}
		owner_pid=${owner##*:}
		if [ "$owner_host" = "$(hostname)" ]; then
			if kill -0 "$owner_pid" 2> /dev/null; then
				echo "Skipping $dir because it is currently being processed by $owner." >> "$LOG_FILE"
				return 1
			fi
		else
			age=$(( $(share_now "$dir") - $(stat -c %Y "$lock" 2> /dev/null || echo 0) ))
			if [ $age -lt $SESSION_LOCK_STALE_SECONDS ]; then
				echo "Skipping $dir because it is currently being processed by $owner (lock refreshed ${age}s ago)." >> "$LOG_FILE"
				return 1
			fi
		fi
		echo "Removing stale lock on $dir held by $owner." >> "$LOG_FILE"
		rm -f "$lock"
		if ! ( set -o noclobber; echo "$SESSION_LOCK_OWNER" > "$lock" ) 2> /dev/null; then
			echo "Skipping $dir because another process took its lock first." >> "$LOG_FILE"
			return 1
		fi
	fi

	HELD_LOCK=$lock
	( while sleep "$SESSION_LOCK_HEARTBEAT_SECONDS" && kill -0 $$ 2> /dev/null; do touch -c "$lock"; done ) &
	HELD_LOCK_HEARTBEAT_PID=$!
	return 0
}

release_session_lock() {
	if [ -n "$HELD_LOCK_HEARTBEAT_PID" ]; then
		kill_tree "$HELD_LOCK_HEARTBEAT_PID"
		wait "$HELD_LOCK_HEARTBEAT_PID" 2> /dev/null
		HELD_LOCK_HEARTBEAT_PID=""
	fi
	# Only remove the lock if it is still ours (it may have been taken over as stale)
	if [ -n "$HELD_LOCK" ] && [ "$(cat "$HELD_LOCK" 2> /dev/null)" = "$SESSION_LOCK_OWNER" ]; then
		rm -f "$HELD_LOCK"
	fi
	HELD_LOCK=""
}

kill_tree() {
	local pid=$1
	local children child
	children=$(pgrep -P "$pid")
	kill "$pid" 2> /dev/null
	for child in $children; do
		kill_tree "$child"
	done
}

# On exit or interrupt, stop every process this script started (workers ignore Ctrl-C
# otherwise and keep writing to the session) before releasing its lock, and keep the
# script's exit status.
session_cleanup() {
	local status=$?
	local child
	trap - EXIT INT TERM
	for child in $(pgrep -P $$); do
		[ "$child" = "$HELD_LOCK_HEARTBEAT_PID" ] || kill_tree "$child"
	done
	release_session_lock
	exit $status
}

install_session_cleanup() {
	trap session_cleanup EXIT
	trap 'exit 130' INT
	trap 'exit 143' TERM
}
