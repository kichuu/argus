#!/usr/bin/env bash
# install_ingest_daemon.sh -- manage the Argus ingest LaunchAgent on macOS.
#
# WHAT IT DOES
# ------------
# Installs scripts/com.argus.ingest.plist as a per-user LaunchAgent at
# ~/Library/LaunchAgents/com.argus.ingest.plist, substituting the
# __REPO_ROOT__ and __USER_HOME__ placeholders so launchd sees
# absolute paths (launchd does not expand ~ or $HOME).
#
# Why launchd, not cron: cron on macOS is deprecated and runs in a
# stripped PATH that usually lacks `uv`. launchd is per-user, restarts
# on crash via KeepAlive, survives logout, and is introspectable via
# `launchctl print`.
#
# USAGE
# -----
#   ./scripts/install_ingest_daemon.sh install     # copy plist & load
#   ./scripts/install_ingest_daemon.sh uninstall   # unload & delete plist
#   ./scripts/install_ingest_daemon.sh status      # launchctl print + list
#   ./scripts/install_ingest_daemon.sh logs        # tail -F the log files
#
# DEBUGGING
# ---------
# After install, watch logs with `... logs`. If the agent keeps
# bouncing, run `... status` to see launchd's exit-code history.

set -euo pipefail

LABEL="com.argus.ingest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLIST_TEMPLATE="${SCRIPT_DIR}/${LABEL}.plist"

USER_HOME="${HOME}"
LAUNCH_AGENTS_DIR="${USER_HOME}/Library/LaunchAgents"
INSTALLED_PLIST="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
LOG_DIR="${USER_HOME}/Library/Logs/argus"
OUT_LOG="${LOG_DIR}/ingest-loop.out.log"
ERR_LOG="${LOG_DIR}/ingest-loop.err.log"

UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
SERVICE_TARGET="${DOMAIN}/${LABEL}"

usage() {
    cat <<EOF
Usage: $0 {install|uninstall|status|logs}

  install     substitute paths, copy plist to ${LAUNCH_AGENTS_DIR},
              create ${LOG_DIR}, and bootstrap the LaunchAgent.
  uninstall   bootout (or unload) the agent and remove the plist.
  status      show launchctl print + a filtered launchctl list.
  logs        tail -F the stdout and stderr log files.
EOF
}

require_template() {
    if [[ ! -f "${PLIST_TEMPLATE}" ]]; then
        echo "ERROR: plist template not found at ${PLIST_TEMPLATE}" >&2
        exit 1
    fi
}

cmd_install() {
    require_template
    mkdir -p "${LAUNCH_AGENTS_DIR}"
    mkdir -p "${LOG_DIR}"
    : >> "${OUT_LOG}"
    : >> "${ERR_LOG}"

    echo "[argus.ingest] rendering plist with REPO_ROOT=${REPO_ROOT} HOME=${USER_HOME}"
    # Use a delimiter that won't appear in absolute filesystem paths.
    sed \
        -e "s|__REPO_ROOT__|${REPO_ROOT}|g" \
        -e "s|__USER_HOME__|${USER_HOME}|g" \
        "${PLIST_TEMPLATE}" > "${INSTALLED_PLIST}"

    # If something is already loaded under this label, remove it first
    # so bootstrap doesn't fail with EALREADY.
    if launchctl print "${SERVICE_TARGET}" >/dev/null 2>&1; then
        echo "[argus.ingest] existing agent detected; booting out first"
        launchctl bootout "${SERVICE_TARGET}" 2>/dev/null || \
            launchctl unload -w "${INSTALLED_PLIST}" 2>/dev/null || true
    fi

    echo "[argus.ingest] loading ${INSTALLED_PLIST}"
    if ! launchctl bootstrap "${DOMAIN}" "${INSTALLED_PLIST}" 2>/dev/null; then
        # Older macOS / fallback path.
        echo "[argus.ingest] bootstrap failed; falling back to launchctl load -w"
        launchctl load -w "${INSTALLED_PLIST}"
    fi

    echo
    echo "Argus ingest daemon installed. Inspect: ./scripts/install_ingest_daemon.sh logs"
}

cmd_uninstall() {
    if [[ -f "${INSTALLED_PLIST}" ]]; then
        echo "[argus.ingest] booting out ${SERVICE_TARGET}"
        launchctl bootout "${SERVICE_TARGET}" 2>/dev/null || \
            launchctl unload -w "${INSTALLED_PLIST}" 2>/dev/null || true
        rm -f "${INSTALLED_PLIST}"
        echo "[argus.ingest] removed ${INSTALLED_PLIST}"
    else
        echo "[argus.ingest] nothing to remove at ${INSTALLED_PLIST}"
        # Try to bootout anyway, in case it's loaded from elsewhere.
        launchctl bootout "${SERVICE_TARGET}" 2>/dev/null || true
    fi
}

cmd_status() {
    echo "=== launchctl print ${SERVICE_TARGET} ==="
    launchctl print "${SERVICE_TARGET}" 2>&1 || echo "(not loaded)"
    echo
    echo "=== launchctl list | grep com.argus ==="
    launchctl list 2>/dev/null | grep "com.argus" || echo "(no com.argus.* entries)"
}

cmd_logs() {
    mkdir -p "${LOG_DIR}"
    : >> "${OUT_LOG}"
    : >> "${ERR_LOG}"
    echo "[argus.ingest] tailing ${OUT_LOG} and ${ERR_LOG} (Ctrl-C to stop)"
    exec tail -F "${OUT_LOG}" "${ERR_LOG}"
}

main() {
    if [[ $# -lt 1 ]]; then
        usage
        exit 64
    fi
    case "$1" in
        install)   cmd_install ;;
        uninstall) cmd_uninstall ;;
        status)    cmd_status ;;
        logs)      cmd_logs ;;
        -h|--help|help) usage ;;
        *)
            echo "ERROR: unknown subcommand: $1" >&2
            usage
            exit 64
            ;;
    esac
}

main "$@"
