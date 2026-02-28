#!/usr/bin/env bash
# ============================================================
# Reception Greeter – Auto-setup & service installer
# ============================================================
# Run this on Raspberry Pi or Qualcomm RB5 to:
#   1. Install system dependencies (espeak, ALSA, v4l-utils)
#   2. Create a Python venv and install pip packages
#   3. Install a systemd service for auto-start on boot
#
# Usage:
#   chmod +x scripts/setup_edge_device.sh
#   sudo ./scripts/setup_edge_device.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_DIR}/venv"
SERVICE_NAME="reception-greeter"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[x]${NC} $*"; exit 1; }

# ---- Detect platform ----
detect_platform() {
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(tr -d '\0' < /proc/device-tree/model)
        case "$MODEL" in
            *"Raspberry Pi 5"*) PLATFORM="rpi5" ;;
            *"Raspberry Pi 4"*) PLATFORM="rpi4" ;;
            *"Raspberry Pi 3"*) PLATFORM="rpi3" ;;
            *"Raspberry Pi"*)   PLATFORM="rpi"  ;;
            *) PLATFORM="unknown" ;;
        esac
    elif grep -qi "qrb5165\|rb5\|sm8250" /proc/cpuinfo 2>/dev/null; then
        PLATFORM="rb5"
    else
        PLATFORM="unknown"
    fi
    log "Detected platform: ${PLATFORM} ($(uname -m))"
}

# ---- Install system dependencies ----
install_system_deps() {
    log "Installing system dependencies..."
    apt-get update -qq

    # Core packages
    apt-get install -y -qq \
        python3 python3-pip python3-venv \
        espeak espeak-data \
        alsa-utils pulseaudio \
        v4l-utils \
        libopencv-dev \
        libatlas-base-dev \
        libjpeg-dev libpng-dev \
        libgstreamer1.0-dev gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
        gstreamer1.0-tools

    # RPi-specific
    if [[ "$PLATFORM" == rpi* ]]; then
        apt-get install -y -qq \
            libcamera-apps libcamera-dev \
            python3-libcamera python3-picamera2 || true
        log "RPi camera stack installed"
    fi

    # RB5-specific
    if [ "$PLATFORM" = "rb5" ]; then
        # qtiqmmfsrc and QNN SDK are typically pre-installed on the RB5 BSP
        log "RB5 detected – ensure QNN SDK is installed in /opt/qcom/aistack"
    fi

    log "System dependencies installed"
}

# ---- Create Python virtual environment ----
setup_venv() {
    log "Setting up Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip setuptools wheel

    # Install requirements (use ARM-compatible versions)
    pip install \
        "opencv-python-headless>=4.8" \
        "numpy>=1.24" \
        "insightface>=0.7" \
        "onnxruntime>=1.16" \
        "scipy>=1.11" \
        "pyttsx3>=2.90" \
        "PyYAML>=6.0" \
        "albumentations>=1.3"

    log "Python packages installed"
}

# ---- Select config ----
select_config() {
    case "$PLATFORM" in
        rpi*) CONFIG_FILE="${PROJECT_DIR}/app/config_rpi.yaml" ;;
        rb5)  CONFIG_FILE="${PROJECT_DIR}/app/config_rb5.yaml" ;;
        *)    CONFIG_FILE="${PROJECT_DIR}/app/config.yaml" ;;
    esac
    log "Using config: ${CONFIG_FILE}"
}

# ---- Create systemd service ----
install_service() {
    log "Installing systemd service: ${SERVICE_NAME}"

    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Reception Greeter – Face Recognition Camera System
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=$(logname 2>/dev/null || echo "pi")
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="DISPLAY=:0"
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"
ExecStart=${VENV_DIR}/bin/python app/main.py --config ${CONFIG_FILE} --no-display
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=75%
CPUQuota=85%

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${PROJECT_DIR}/data ${PROJECT_DIR}/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"
    log "Service installed and enabled (auto-start on boot)"
    log "  Start now:   sudo systemctl start ${SERVICE_NAME}"
    log "  View logs:   journalctl -u ${SERVICE_NAME} -f"
    log "  Stop:        sudo systemctl stop ${SERVICE_NAME}"
}

# ---- Create data/logs directories ----
create_dirs() {
    mkdir -p "${PROJECT_DIR}/data" "${PROJECT_DIR}/logs"
    chown -R "$(logname 2>/dev/null || echo 'pi'):$(logname 2>/dev/null || echo 'pi')" \
        "${PROJECT_DIR}/data" "${PROJECT_DIR}/logs"
}

# ---- Main ----
main() {
    echo "=============================================="
    echo "  Reception Greeter – Edge Device Setup"
    echo "=============================================="

    if [ "$(id -u)" -ne 0 ]; then
        error "Please run as root: sudo $0"
    fi

    detect_platform
    install_system_deps
    setup_venv
    select_config
    create_dirs
    install_service

    echo ""
    log "Setup complete!"
    log "Platform: ${PLATFORM}"
    log "Config:   ${CONFIG_FILE}"
    log "Service:  ${SERVICE_NAME}"
    echo ""
    log "Quick start:"
    log "  sudo systemctl start ${SERVICE_NAME}"
    log "  journalctl -u ${SERVICE_NAME} -f"
}

main "$@"
