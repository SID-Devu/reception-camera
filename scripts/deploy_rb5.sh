#!/usr/bin/env bash
# ============================================================
#  Reception Greeter – Host-Side ADB Deploy to RB5
# ============================================================
#  Run this script from your DEVELOPMENT MACHINE (not the RB5)
#  to push the project to the RB5 board and trigger setup.
#
#  Prerequisites:
#    - ADB installed on your host (Android SDK Platform Tools)
#    - RB5 connected via USB-C (debug port)
#    - RB5 powered on
#
#  Usage:
#    ./scripts/deploy_rb5.sh                  # Push + setup
#    ./scripts/deploy_rb5.sh --push-only      # Push files only
#    ./scripts/deploy_rb5.sh --setup-only     # Run setup on board
#    ./scripts/deploy_rb5.sh --status         # Check board status
#    ./scripts/deploy_rb5.sh --shell          # Open shell on RB5
#    ./scripts/deploy_rb5.sh --ssh user@host  # Deploy via SSH instead
#
#  Reference: Qualcomm RB5 Dev Kit User Guide (80-88500-5 Rev. AF)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()    { echo -e "${GREEN}[✓]${NC} $*"; }
info()   { echo -e "${BLUE}[i]${NC} $*"; }
warn()   { echo -e "${YELLOW}[!]${NC} $*"; }
error()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }
header() { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${NC}"; }

# ---- Configuration ----
DEPLOY_DIR="/opt/reception-camera"
SSH_TARGET=""
PUSH_ONLY=false
SETUP_ONLY=false
SHOW_STATUS=false
OPEN_SHELL=false

# ---- Exclusion patterns (not pushed to board) ----
EXCLUDE_DIRS=(
    ".git"
    ".venv"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    "node_modules"
    "dist"
    "build"
    "*.egg-info"
    ".mypy_cache"
    ".tox"
    "htmlcov"
    "site"
)

# ============================================================
#  Parse Arguments
# ============================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --push-only)   PUSH_ONLY=true; shift ;;
            --setup-only)  SETUP_ONLY=true; shift ;;
            --status)      SHOW_STATUS=true; shift ;;
            --shell)       OPEN_SHELL=true; shift ;;
            --ssh)         SSH_TARGET="$2"; shift 2 ;;
            --target)      DEPLOY_DIR="$2"; shift 2 ;;
            -h|--help)     show_help; exit 0 ;;
            *)             error "Unknown argument: $1. Use --help." ;;
        esac
    done
}

show_help() {
    cat << 'EOF'
Reception Greeter - RB5 Deploy Script

Usage: ./scripts/deploy_rb5.sh [OPTIONS]

Options:
  --push-only          Push files only (don't run setup)
  --setup-only         Run setup on board only (don't push)
  --status             Show board status and diagnostics
  --shell              Open interactive shell on RB5
  --ssh USER@HOST      Deploy via SSH instead of ADB
  --target DIR         Deploy target directory (default: /opt/reception-camera)
  -h, --help           Show this help

Examples:
  # Full deploy (push + setup) via ADB:
  ./scripts/deploy_rb5.sh

  # Push code, don't run setup:
  ./scripts/deploy_rb5.sh --push-only

  # Deploy via SSH (e.g., over Wi-Fi/Ethernet):
  ./scripts/deploy_rb5.sh --ssh root@192.168.1.100

  # Check board status:
  ./scripts/deploy_rb5.sh --status

  # Open shell for debugging:
  ./scripts/deploy_rb5.sh --shell
EOF
}

# ============================================================
#  ADB Functions
# ============================================================
check_adb() {
    if ! command -v adb &>/dev/null; then
        error "ADB not found. Install Android SDK Platform Tools:
  - Linux:   sudo apt-get install android-tools-adb
  - macOS:   brew install android-platform-tools
  - Windows: https://developer.android.com/studio/releases/platform-tools"
    fi
}

wait_for_device() {
    header "Waiting for RB5"

    info "Ensure the RB5 is:"
    info "  1. Powered on"
    info "  2. USB-C debug cable connected to your host"
    info "  3. ADB authorized (check on-device prompt if needed)"
    info ""

    local devices
    devices="$(adb devices | grep -v "^List\|^$")"
    if [ -z "$devices" ]; then
        info "No devices found. Waiting up to 30 seconds..."
        timeout 30 adb wait-for-device 2>/dev/null || error "No ADB device found after 30 seconds."
    fi

    # Get root access
    adb root 2>/dev/null || true
    sleep 2

    # Show device info
    local SERIAL MODEL
    SERIAL="$(adb get-serialno 2>/dev/null || echo 'unknown')"
    MODEL="$(adb shell getprop ro.product.model 2>/dev/null || echo 'unknown')"
    log "Connected: ${MODEL} (serial: ${SERIAL})"
}

# ============================================================
#  Push Files via ADB
# ============================================================
push_files_adb() {
    header "Pushing Project to RB5"

    info "Target: ${DEPLOY_DIR}"

    # Create deploy directory
    adb shell "mkdir -p ${DEPLOY_DIR}" 2>/dev/null

    # Build exclude arguments
    local EXCLUDE_ARGS=""
    for pattern in "${EXCLUDE_DIRS[@]}"; do
        EXCLUDE_ARGS="${EXCLUDE_ARGS} --exclude=${pattern}"
    done

    # Create a clean tarball locally
    local TARBALL="/tmp/reception-camera-deploy.tar.gz"
    info "Creating deployment archive..."
    cd "$PROJECT_DIR"
    tar czf "$TARBALL" \
        --exclude='.git' \
        --exclude='.venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.pytest_cache' \
        --exclude='node_modules' \
        --exclude='*.egg-info' \
        --exclude='.mypy_cache' \
        --exclude='htmlcov' \
        --exclude='site' \
        --exclude='*.pdf' \
        --exclude='data/db/*' \
        --exclude='data/embeddings/*' \
        --exclude='data/logs/*' \
        .

    local SIZE
    SIZE="$(du -sh "$TARBALL" | cut -f1)"
    info "Archive size: ${SIZE}"

    # Push tarball
    info "Pushing to RB5 (this may take a minute)..."
    adb push "$TARBALL" "/tmp/reception-camera-deploy.tar.gz"

    # Extract on device
    info "Extracting on device..."
    adb shell "cd ${DEPLOY_DIR} && tar xzf /tmp/reception-camera-deploy.tar.gz"
    adb shell "rm /tmp/reception-camera-deploy.tar.gz"

    # Set permissions
    adb shell "chmod +x ${DEPLOY_DIR}/setup.sh"
    adb shell "chmod +x ${DEPLOY_DIR}/scripts/*.sh"

    # Cleanup local temp
    rm -f "$TARBALL"

    log "Files pushed successfully to ${DEPLOY_DIR}"
}

# ============================================================
#  Push Files via SSH
# ============================================================
push_files_ssh() {
    header "Pushing Project via SSH"

    info "Target: ${SSH_TARGET}:${DEPLOY_DIR}"

    # Create deploy directory
    ssh "$SSH_TARGET" "mkdir -p ${DEPLOY_DIR}"

    # Use rsync if available (incremental, faster)
    if command -v rsync &>/dev/null; then
        info "Using rsync for incremental transfer..."
        rsync -avz --progress \
            --exclude='.git' \
            --exclude='.venv' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.pytest_cache' \
            --exclude='node_modules' \
            --exclude='*.egg-info' \
            --exclude='.mypy_cache' \
            --exclude='htmlcov' \
            --exclude='site' \
            --exclude='*.pdf' \
            --exclude='data/db/*' \
            --exclude='data/embeddings/*' \
            --exclude='data/logs/*' \
            "${PROJECT_DIR}/" "${SSH_TARGET}:${DEPLOY_DIR}/"
    else
        # Fallback to tar + scp
        info "Using tar + scp..."
        local TARBALL="/tmp/reception-camera-deploy.tar.gz"
        cd "$PROJECT_DIR"
        tar czf "$TARBALL" \
            --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
            --exclude='*.pyc' --exclude='.pytest_cache' --exclude='node_modules' \
            --exclude='*.egg-info' --exclude='*.pdf' .
        scp "$TARBALL" "${SSH_TARGET}:/tmp/"
        ssh "$SSH_TARGET" "cd ${DEPLOY_DIR} && tar xzf /tmp/reception-camera-deploy.tar.gz && rm /tmp/reception-camera-deploy.tar.gz"
        rm -f "$TARBALL"
    fi

    # Set permissions
    ssh "$SSH_TARGET" "chmod +x ${DEPLOY_DIR}/setup.sh ${DEPLOY_DIR}/scripts/*.sh"

    log "Files pushed via SSH"
}

# ============================================================
#  Run Setup on Board
# ============================================================
run_remote_setup() {
    header "Running Setup on RB5"

    local SETUP_CMD="cd ${DEPLOY_DIR} && bash setup.sh 2>&1"

    if [ -n "$SSH_TARGET" ]; then
        info "Executing setup via SSH..."
        ssh -t "$SSH_TARGET" "$SETUP_CMD"
    else
        info "Executing setup via ADB..."
        adb shell "$SETUP_CMD"
    fi

    log "Remote setup complete"
}

# ============================================================
#  Status Check
# ============================================================
show_board_status() {
    header "RB5 Board Status"

    local exec_cmd
    if [ -n "$SSH_TARGET" ]; then
        exec_cmd="ssh ${SSH_TARGET}"
    else
        check_adb
        wait_for_device
        exec_cmd="adb shell"
    fi

    echo ""
    info "--- System Info ---"
    $exec_cmd "uname -a" 2>/dev/null || echo "  (unavailable)"
    echo ""

    info "--- Memory ---"
    $exec_cmd "free -h 2>/dev/null || cat /proc/meminfo | head -5" 2>/dev/null || true
    echo ""

    info "--- Disk Usage ---"
    $exec_cmd "df -h / /data 2>/dev/null" || true
    echo ""

    info "--- CPU Temperature ---"
    $exec_cmd "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null" || echo "  (unavailable)"
    echo ""

    info "--- Network ---"
    $exec_cmd "ip addr show | grep -E 'inet |state'" 2>/dev/null || true
    echo ""

    info "--- Camera Devices ---"
    $exec_cmd "ls -l /dev/video* 2>/dev/null" || echo "  No video devices"
    echo ""

    info "--- Service Status ---"
    $exec_cmd "systemctl status reception-greeter 2>/dev/null | head -10" || echo "  Service not installed"
    echo ""

    info "--- Recent Logs ---"
    $exec_cmd "journalctl -u reception-greeter --no-pager -n 10 2>/dev/null" || echo "  No logs"
}

# ============================================================
#  Open Shell
# ============================================================
open_shell() {
    if [ -n "$SSH_TARGET" ]; then
        info "Opening SSH shell to ${SSH_TARGET}..."
        ssh -t "$SSH_TARGET" "cd ${DEPLOY_DIR} && bash -l"
    else
        check_adb
        wait_for_device
        info "Opening ADB shell..."
        adb shell "cd ${DEPLOY_DIR} 2>/dev/null; exec /bin/bash -l 2>/dev/null || exec /bin/sh -l"
    fi
}

# ============================================================
#  Main
# ============================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  Reception Greeter – RB5 Deploy             ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""

    parse_args "$@"

    # --- Mode: Status ---
    if [ "$SHOW_STATUS" = true ]; then
        show_board_status
        exit 0
    fi

    # --- Mode: Shell ---
    if [ "$OPEN_SHELL" = true ]; then
        if [ -n "$SSH_TARGET" ]; then
            open_shell
        else
            check_adb
            wait_for_device
            open_shell
        fi
        exit 0
    fi

    # --- Deploy Mode ---
    if [ -n "$SSH_TARGET" ]; then
        info "Deploy method: SSH (${SSH_TARGET})"
    else
        info "Deploy method: ADB (USB)"
        check_adb
        wait_for_device
    fi

    # Push
    if [ "$SETUP_ONLY" = false ]; then
        if [ -n "$SSH_TARGET" ]; then
            push_files_ssh
        else
            push_files_adb
        fi
    fi

    # Setup
    if [ "$PUSH_ONLY" = false ]; then
        run_remote_setup
    fi

    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  Deploy Complete!                           ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    info "The reception-camera application is deployed to:"
    info "  ${DEPLOY_DIR}"
    echo ""
    info "Manage the service:"
    if [ -n "$SSH_TARGET" ]; then
        info "  ssh ${SSH_TARGET} systemctl start reception-greeter"
        info "  ssh ${SSH_TARGET} systemctl stop reception-greeter"
        info "  ssh ${SSH_TARGET} journalctl -u reception-greeter -f"
    else
        info "  adb shell systemctl start reception-greeter"
        info "  adb shell systemctl stop reception-greeter"
        info "  adb shell journalctl -u reception-greeter -f"
    fi
    echo ""
}

main "$@"
