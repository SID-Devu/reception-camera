#!/usr/bin/env bash
# ============================================================
#  Reception Greeter – Post-Setup Health Check
# ============================================================
#  Run this script on the target device (RB5, RPi, x86, etc.)
#  to validate that the setup is complete and ready to run.
#
#  Usage:
#    ./scripts/validate.sh               # Full validation
#    ./scripts/validate.sh --quick       # Quick check (skip slow tests)
#    ./scripts/validate.sh --fix         # Attempt auto-fix for issues
#    ./scripts/validate.sh --json        # Output as JSON
# ============================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0
SKIP=0
QUICK=false
FIX_MODE=false
JSON_MODE=false
JSON_RESULTS="[]"

# ---- Parse args ----
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=true ;;
        --fix)   FIX_MODE=true ;;
        --json)  JSON_MODE=true ;;
    esac
done

log_pass() {
    if [ "$JSON_MODE" = true ]; then
        JSON_RESULTS="$(echo "$JSON_RESULTS" | python3 -c "
import sys,json
r=json.loads(sys.stdin.read())
r.append({'test':'$1','status':'pass','message':'$2'})
print(json.dumps(r))" 2>/dev/null || echo "$JSON_RESULTS")"
    else
        echo -e "  ${GREEN}[PASS]${NC} $1: $2"
    fi
    ((PASS++))
}

log_fail() {
    if [ "$JSON_MODE" = true ]; then
        JSON_RESULTS="$(echo "$JSON_RESULTS" | python3 -c "
import sys,json
r=json.loads(sys.stdin.read())
r.append({'test':'$1','status':'fail','message':'$2'})
print(json.dumps(r))" 2>/dev/null || echo "$JSON_RESULTS")"
    else
        echo -e "  ${RED}[FAIL]${NC} $1: $2"
    fi
    ((FAIL++))
}

log_warn() {
    if [ "$JSON_MODE" = true ]; then
        JSON_RESULTS="$(echo "$JSON_RESULTS" | python3 -c "
import sys,json
r=json.loads(sys.stdin.read())
r.append({'test':'$1','status':'warn','message':'$2'})
print(json.dumps(r))" 2>/dev/null || echo "$JSON_RESULTS")"
    else
        echo -e "  ${YELLOW}[WARN]${NC} $1: $2"
    fi
    ((WARN++))
}

log_skip() {
    if [ "$JSON_MODE" = false ]; then
        echo -e "  ${BLUE}[SKIP]${NC} $1: $2"
    fi
    ((SKIP++))
}

# ============================================================
header() {
    if [ "$JSON_MODE" = false ]; then
        echo -e "\n${BOLD}$*${NC}"
    fi
}

# ============================================================
#  1. Python Environment
# ============================================================
check_python() {
    header "Python Environment"

    # Python binary
    if [ -f "${PROJECT_DIR}/.venv/bin/python" ]; then
        local PY_VER
        PY_VER="$("${PROJECT_DIR}/.venv/bin/python" --version 2>&1)"
        log_pass "Virtual env" "${PY_VER}"
    elif command -v python3 &>/dev/null; then
        local PY_VER
        PY_VER="$(python3 --version 2>&1)"
        log_warn "Virtual env" "Not found, using system Python: ${PY_VER}"
        if [ "$FIX_MODE" = true ]; then
            echo "  Attempting fix: creating virtual environment..."
            python3 -m venv "${PROJECT_DIR}/.venv" && log_pass "Fix: venv" "Created"
        fi
    else
        log_fail "Python" "Not found!"
    fi

    # Pip packages
    local PYTHON="${PROJECT_DIR}/.venv/bin/python"
    [ ! -f "$PYTHON" ] && PYTHON="python3"

    local REQUIRED_PKGS=("onnxruntime" "insightface" "opencv-python" "numpy" "chromadb" "pyttsx3")
    for pkg in "${REQUIRED_PKGS[@]}"; do
        if $PYTHON -c "import $(echo $pkg | tr '-' '_')" 2>/dev/null; then
            log_pass "Package: ${pkg}" "Installed"
        else
            log_fail "Package: ${pkg}" "Missing"
            if [ "$FIX_MODE" = true ]; then
                echo "  Attempting fix: pip install ${pkg}..."
                $PYTHON -m pip install "$pkg" --quiet 2>/dev/null && log_pass "Fix: ${pkg}" "Installed"
            fi
        fi
    done
}

# ============================================================
#  2. Configuration
# ============================================================
check_config() {
    header "Configuration"

    local ACTIVE_CONFIG="${PROJECT_DIR}/app/config_active.yaml"
    if [ -f "$ACTIVE_CONFIG" ]; then
        log_pass "Active config" "Found: config_active.yaml"
    elif [ -f "${PROJECT_DIR}/app/config.yaml" ]; then
        log_warn "Active config" "Missing config_active.yaml, using config.yaml"
    else
        log_fail "Config" "No config file found in app/"
    fi

    # Check platform-specific configs exist
    for cfg in config.yaml config_rb5.yaml config_rpi.yaml; do
        if [ -f "${PROJECT_DIR}/app/${cfg}" ]; then
            log_pass "Config: ${cfg}" "Present"
        fi
    done
}

# ============================================================
#  3. Models
# ============================================================
check_models() {
    header "AI Models"

    local MODEL_DIR="${PROJECT_DIR}/models"
    if [ ! -d "$MODEL_DIR" ]; then
        log_fail "Model directory" "Not found: models/"
        return
    fi

    # Check for insightface model pack
    local FOUND_MODELS=0
    for pack in buffalo_l buffalo_s buffalo_sc antelopev2; do
        if [ -d "${MODEL_DIR}/${pack}" ] || [ -d "${MODEL_DIR}/insightface/${pack}" ]; then
            log_pass "Model pack: ${pack}" "Found"
            ((FOUND_MODELS++))
        fi
    done
    if [ "$FOUND_MODELS" -eq 0 ]; then
        # Check for .onnx files directly
        local ONNX_COUNT
        ONNX_COUNT="$(find "$MODEL_DIR" -name '*.onnx' 2>/dev/null | wc -l)"
        if [ "$ONNX_COUNT" -gt 0 ]; then
            log_pass "ONNX models" "Found ${ONNX_COUNT} model(s)"
        else
            log_fail "Models" "No model packs or .onnx files found"
            echo "    Run: python tools/download_models.py"
        fi
    fi
}

# ============================================================
#  4. Camera
# ============================================================
check_camera() {
    header "Camera"

    if [ "$QUICK" = true ]; then
        # Quick check: just see if video devices exist
        if ls /dev/video* &>/dev/null; then
            local COUNT
            COUNT="$(ls /dev/video* 2>/dev/null | wc -l)"
            log_pass "Video devices" "${COUNT} device(s) found"
        elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
            log_skip "Camera" "Windows (check in app)"
        else
            log_fail "Video devices" "None found (/dev/video*)"
        fi
        return
    fi

    # Full camera check
    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$OSTYPE" == "win32"* ]]; then
        log_skip "Camera" "Windows (DirectShow cameras checked at runtime)"
        return
    fi

    # Linux V4L2
    if ls /dev/video* &>/dev/null; then
        for dev in /dev/video*; do
            if [ -c "$dev" ]; then
                local DEV_NAME=""
                local DEV_NUM="$(basename "$dev" | sed 's/video//')"
                if [ -f "/sys/class/video4linux/video${DEV_NUM}/name" ]; then
                    DEV_NAME="$(cat "/sys/class/video4linux/video${DEV_NUM}/name")"
                fi
                log_pass "$dev" "${DEV_NAME:-unknown}"
            fi
        done
    else
        log_fail "Camera" "No /dev/video* devices found"
    fi

    # GStreamer test
    if command -v gst-launch-1.0 &>/dev/null; then
        log_pass "GStreamer" "Available"
        # Check qtiqmmfsrc (RB5 MIPI)
        if gst-inspect-1.0 qtiqmmfsrc &>/dev/null; then
            log_pass "MIPI CSI (qtiqmmfsrc)" "Plugin available"
        fi
    else
        log_warn "GStreamer" "Not installed (may affect performance)"
    fi
}

# ============================================================
#  5. Audio
# ============================================================
check_audio() {
    header "Audio"

    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
        log_skip "Audio" "Windows (WASAPI checked at runtime)"
        return
    fi

    # Check audio systems
    if command -v pulseaudio &>/dev/null; then
        log_pass "PulseAudio" "Available"
    elif command -v pipewire &>/dev/null; then
        log_pass "PipeWire" "Available"
    elif command -v amixer &>/dev/null; then
        log_pass "ALSA" "Available"
    else
        log_warn "Audio system" "None detected"
    fi

    # Check TTS
    if command -v espeak &>/dev/null; then
        log_pass "TTS (espeak)" "Available"
    elif command -v espeak-ng &>/dev/null; then
        log_pass "TTS (espeak-ng)" "Available"
    else
        log_warn "TTS" "espeak not found (greeting audio disabled)"
    fi
}

# ============================================================
#  6. Network
# ============================================================
check_network() {
    header "Network"

    if ping -c 1 -W 3 8.8.8.8 &>/dev/null 2>&1; then
        log_pass "Internet" "Connected"
    elif ping -c 1 -W 3 1.1.1.1 &>/dev/null 2>&1; then
        log_pass "Internet" "Connected (via 1.1.1.1)"
    else
        log_warn "Internet" "Not reachable (offline mode OK if models downloaded)"
    fi
}

# ============================================================
#  7. Data Directories
# ============================================================
check_data_dirs() {
    header "Data Directories"

    for dir in data data/db data/embeddings data/logs data/faces; do
        if [ -d "${PROJECT_DIR}/${dir}" ]; then
            log_pass "$dir" "Exists"
        else
            log_warn "$dir" "Not found"
            if [ "$FIX_MODE" = true ]; then
                mkdir -p "${PROJECT_DIR}/${dir}"
                log_pass "Fix: ${dir}" "Created"
            fi
        fi
    done

    # Check write permissions
    if touch "${PROJECT_DIR}/data/.write_test" 2>/dev/null; then
        rm -f "${PROJECT_DIR}/data/.write_test"
        log_pass "data/ writable" "Yes"
    else
        log_fail "data/ writable" "No write permission!"
    fi
}

# ============================================================
#  8. Systemd Service
# ============================================================
check_service() {
    header "Systemd Service"

    if ! command -v systemctl &>/dev/null; then
        log_skip "Systemd" "Not available (macOS/Windows)"
        return
    fi

    if systemctl list-unit-files | grep -q "reception-greeter"; then
        local STATUS
        STATUS="$(systemctl is-active reception-greeter 2>/dev/null || echo 'unknown')"
        case "$STATUS" in
            active)    log_pass "Service" "Running" ;;
            inactive)  log_warn "Service" "Installed but not running" ;;
            failed)    log_fail "Service" "Failed! Check: journalctl -u reception-greeter" ;;
            *)         log_warn "Service" "Status: ${STATUS}" ;;
        esac
    else
        log_warn "Service" "Not installed (use setup.sh to install)"
    fi
}

# ============================================================
#  9. Disk Space
# ============================================================
check_disk() {
    header "Disk Space"

    local AVAIL
    AVAIL="$(df -m "${PROJECT_DIR}" 2>/dev/null | tail -1 | awk '{print $4}')"
    if [ -n "$AVAIL" ] && [ "$AVAIL" -gt 0 ] 2>/dev/null; then
        if [ "$AVAIL" -lt 500 ]; then
            log_fail "Disk space" "${AVAIL}MB free (need >= 500MB)"
        elif [ "$AVAIL" -lt 1024 ]; then
            log_warn "Disk space" "${AVAIL}MB free (recommend >= 1GB)"
        else
            log_pass "Disk space" "${AVAIL}MB free"
        fi
    fi
}

# ============================================================
#  10. Quick Application Test
# ============================================================
test_app_import() {
    header "Application Import Test"

    if [ "$QUICK" = true ]; then
        log_skip "Import test" "Skipped (--quick)"
        return
    fi

    local PYTHON="${PROJECT_DIR}/.venv/bin/python"
    [ ! -f "$PYTHON" ] && PYTHON="python3"

    local RESULT
    RESULT="$($PYTHON -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}')
try:
    from app.hardware.detector import detect_platform
    p = detect_platform()
    print(f'OK:platform={p.get(\"platform\",\"unknown\")}')
except Exception as e:
    print(f'ERR:{e}')
" 2>&1)"

    if echo "$RESULT" | grep -q "^OK:"; then
        local PLATFORM
        PLATFORM="$(echo "$RESULT" | sed 's/OK://')"
        log_pass "App import" "Success (${PLATFORM})"
    else
        log_fail "App import" "${RESULT}"
    fi
}

# ============================================================
#  Summary
# ============================================================
print_summary() {
    if [ "$JSON_MODE" = true ]; then
        python3 -c "
import json
results = json.loads('''${JSON_RESULTS}''')
summary = {
    'pass': ${PASS},
    'fail': ${FAIL},
    'warn': ${WARN},
    'skip': ${SKIP},
    'overall': 'pass' if ${FAIL} == 0 else 'fail',
    'checks': results
}
print(json.dumps(summary, indent=2))
" 2>/dev/null
        return
    fi

    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  Validation Summary${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}PASS:${NC} ${PASS}"
    echo -e "  ${RED}FAIL:${NC} ${FAIL}"
    echo -e "  ${YELLOW}WARN:${NC} ${WARN}"
    if [ "$SKIP" -gt 0 ]; then
        echo -e "  ${BLUE}SKIP:${NC} ${SKIP}"
    fi
    echo ""

    if [ "$FAIL" -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}System is ready!${NC}"
        echo ""
        echo "  Start the application:"
        if [ -f "${PROJECT_DIR}/.venv/bin/python" ]; then
            echo "    ${PROJECT_DIR}/.venv/bin/python app/main.py"
        else
            echo "    python3 app/main.py"
        fi
        echo ""
        echo "  Or use the systemd service:"
        echo "    sudo systemctl start reception-greeter"
    else
        echo -e "  ${RED}${BOLD}Issues found! Fix the FAILed checks above.${NC}"
        echo ""
        echo "  Quick fix attempt:"
        echo "    ./scripts/validate.sh --fix"
    fi
    echo ""
}

# ============================================================
#  Main
# ============================================================
main() {
    if [ "$JSON_MODE" = false ]; then
        echo ""
        echo "╔══════════════════════════════════════════════╗"
        echo "║  Reception Greeter – Health Check            ║"
        echo "╚══════════════════════════════════════════════╝"
    fi

    cd "$PROJECT_DIR"

    check_python
    check_config
    check_models
    check_camera
    check_audio
    check_network
    check_data_dirs
    check_service
    check_disk
    test_app_import

    print_summary

    # Exit code
    [ "$FAIL" -gt 0 ] && exit 1
    exit 0
}

main "$@"
