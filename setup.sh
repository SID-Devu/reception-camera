#!/usr/bin/env bash
# ============================================================
#  Reception Greeter – Universal Auto-Setup
# ============================================================
#  Single entry point that auto-detects your OS, platform, and
#  hardware, then configures everything needed to run the
#  reception-camera system.
#
#  Supports:
#    • Qualcomm Robotics RB5  (Linux Ubuntu / Linux Embedded)
#    • Raspberry Pi 3/4/5     (Raspberry Pi OS)
#    • x86/x64 Linux desktop  (Ubuntu/Debian)
#    • macOS (Intel / Apple Silicon)
#
#  Usage:
#    git clone https://github.com/SID-Devu/reception-camera.git
#    cd reception-camera
#    chmod +x setup.sh
#    sudo ./setup.sh            # Full auto-setup
#    sudo ./setup.sh --no-service   # Skip systemd service install
#    sudo ./setup.sh --dev          # Include dev dependencies
# ============================================================

set -euo pipefail

VERSION="1.3.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="${PROJECT_DIR}/.venv"
DATA_DIR="${PROJECT_DIR}/data"
LOGS_DIR="${PROJECT_DIR}/logs"
MODELS_DIR="${HOME}/.insightface/models"
SERVICE_NAME="reception-greeter"

# ---- Flags ----
INSTALL_SERVICE=true
DEV_MODE=false
SKIP_MODELS=false
WIFI_SSID=""
WIFI_PSK=""

# ---- Colors ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---- Logging ----
SETUP_LOG="${PROJECT_DIR}/setup.log"
log()    { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$SETUP_LOG"; }
info()   { echo -e "${BLUE}[i]${NC} $*" | tee -a "$SETUP_LOG"; }
warn()   { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$SETUP_LOG"; }
error()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$SETUP_LOG"; exit 1; }
header() { echo -e "\n${BOLD}${CYAN}━━━ $* ━━━${NC}" | tee -a "$SETUP_LOG"; }

# ============================================================
#  Parse arguments
# ============================================================
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-service)   INSTALL_SERVICE=false ;;
            --dev)          DEV_MODE=true ;;
            --skip-models)  SKIP_MODELS=true ;;
            --wifi-ssid)    WIFI_SSID="$2"; shift ;;
            --wifi-psk)     WIFI_PSK="$2"; shift ;;
            -h|--help)      show_help; exit 0 ;;
            *)              warn "Unknown option: $1" ;;
        esac
        shift
    done
}

show_help() {
    cat <<'EOF'
Reception Greeter – Universal Auto-Setup

Usage: sudo ./setup.sh [OPTIONS]

Options:
  --no-service       Skip systemd service installation
  --dev              Install development dependencies (pytest, black, etc.)
  --skip-models      Skip downloading face recognition models
  --wifi-ssid NAME   Configure Wi-Fi with this SSID (RB5/embedded)
  --wifi-psk PASS    Wi-Fi password (used with --wifi-ssid)
  -h, --help         Show this help

Examples:
  sudo ./setup.sh                                      # Full auto-setup
  sudo ./setup.sh --wifi-ssid "Office" --wifi-psk "password123"
  sudo ./setup.sh --no-service --dev                   # Dev machine setup
EOF
}

# ============================================================
#  Platform Detection
# ============================================================
PLATFORM="unknown"
OS_TYPE="unknown"       # linux_ubuntu, linux_embedded, raspbian, macos, windows_wsl
OS_DISTRO=""
ARCH=""
CPU_MODEL=""
TOTAL_RAM_MB=0
RB5_OS_VARIANT=""       # "ubuntu" or "embedded"

detect_platform() {
    header "Detecting Platform"

    ARCH="$(uname -m)"
    OS_NAME="$(uname -s)"
    info "Architecture: ${ARCH}"
    info "Kernel: ${OS_NAME}"

    # ---- macOS ----
    if [ "$OS_NAME" = "Darwin" ]; then
        OS_TYPE="macos"
        PLATFORM="macos"
        CPU_MODEL="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Apple Silicon')"
        TOTAL_RAM_MB=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1024 / 1024 ))
        log "Platform: macOS (${CPU_MODEL}, ${TOTAL_RAM_MB}MB RAM)"
        return
    fi

    # ---- Linux ----
    if [ "$OS_NAME" = "Linux" ]; then
        # Detect distro
        if [ -f /etc/os-release ]; then
            OS_DISTRO="$(. /etc/os-release && echo "${ID:-unknown}")"
            info "Distro: ${OS_DISTRO}"
        fi

        # RAM
        if [ -f /proc/meminfo ]; then
            TOTAL_RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
        fi

        # ---- Qualcomm RB5 Detection ----
        DT_MODEL=""
        DT_COMPAT=""
        CPUINFO=""
        [ -f /proc/device-tree/model ] && DT_MODEL="$(tr -d '\0' < /proc/device-tree/model)"
        [ -f /proc/device-tree/compatible ] && DT_COMPAT="$(tr -d '\0' < /proc/device-tree/compatible)"
        [ -f /proc/cpuinfo ] && CPUINFO="$(cat /proc/cpuinfo)"

        DETECT_STRING="${DT_MODEL}${DT_COMPAT}${CPUINFO}"
        DETECT_LOWER="$(echo "$DETECT_STRING" | tr '[:upper:]' '[:lower:]')"

        if echo "$DETECT_LOWER" | grep -qE "qrb5165|rb5|sm8250|qcs8250|qualcomm robotics"; then
            PLATFORM="rb5"
            # Detect Ubuntu vs Embedded
            if [ -f /firmware/verinfo/ver_info.txt ]; then
                if grep -qi "UBUN" /firmware/verinfo/ver_info.txt 2>/dev/null; then
                    RB5_OS_VARIANT="ubuntu"
                    OS_TYPE="linux_ubuntu"
                else
                    RB5_OS_VARIANT="embedded"
                    OS_TYPE="linux_embedded"
                fi
            elif [ -f /etc/os-release ] && grep -qi "ubuntu" /etc/os-release; then
                RB5_OS_VARIANT="ubuntu"
                OS_TYPE="linux_ubuntu"
            else
                RB5_OS_VARIANT="embedded"
                OS_TYPE="linux_embedded"
            fi
            CPU_MODEL="Qualcomm QRB5165 Kryo 585 (8-core)"
            log "Platform: Qualcomm Robotics RB5 (${RB5_OS_VARIANT}, ${TOTAL_RAM_MB}MB RAM)"
            return
        fi

        # ---- Raspberry Pi Detection ----
        if echo "$DETECT_LOWER" | grep -qi "raspberry pi"; then
            case "$DT_MODEL" in
                *"Pi 5"*) PLATFORM="rpi5" ;;
                *"Pi 4"*) PLATFORM="rpi4" ;;
                *"Pi 3"*) PLATFORM="rpi3" ;;
                *)        PLATFORM="rpi"  ;;
            esac
            OS_TYPE="raspbian"
            CPU_MODEL="${DT_MODEL}"
            log "Platform: ${DT_MODEL} (${TOTAL_RAM_MB}MB RAM)"
            return
        fi

        # ---- NVIDIA Jetson ----
        if echo "$DETECT_LOWER" | grep -qi "tegra" || [ -f /etc/nv_tegra_release ]; then
            PLATFORM="jetson"
            OS_TYPE="linux_ubuntu"
            CPU_MODEL="NVIDIA Jetson"
            log "Platform: NVIDIA Jetson (${TOTAL_RAM_MB}MB RAM)"
            return
        fi

        # ---- Generic Linux ----
        if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "armv7l" ]; then
            PLATFORM="generic_arm"
        else
            PLATFORM="generic_x86"
        fi
        OS_TYPE="linux_ubuntu"
        CPU_MODEL="$(grep 'model name' /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2 | xargs || echo 'unknown')"
        log "Platform: Generic Linux ${ARCH} (${CPU_MODEL}, ${TOTAL_RAM_MB}MB RAM)"
        return
    fi

    error "Unsupported operating system: ${OS_NAME}"
}

# ============================================================
#  Network Connectivity
# ============================================================
check_network() {
    header "Checking Network Connectivity"

    # On RB5, optionally configure Wi-Fi
    if [ "$PLATFORM" = "rb5" ] && [ -n "$WIFI_SSID" ]; then
        info "Configuring Wi-Fi: SSID=${WIFI_SSID}"
        configure_rb5_wifi
    fi

    # Try reaching the internet
    if ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log "Internet reachable (ping 8.8.8.8)"
    elif ping -c 1 -W 5 1.1.1.1 &>/dev/null; then
        log "Internet reachable (ping 1.1.1.1)"
    else
        warn "No internet connectivity detected!"
        warn "Some steps (apt, pip, model download) will fail."
        warn "Ensure Wi-Fi or Ethernet is connected."

        if [ "$PLATFORM" = "rb5" ]; then
            info "RB5 Wi-Fi setup:"
            info "  Option 1: Ethernet cable to RJ45 port"
            info "  Option 2: sudo ./setup.sh --wifi-ssid 'YourSSID' --wifi-psk 'YourPass'"
            info "  Option 3: adb shell + edit /data/misc/wifi/wpa_supplicant.conf"
        fi
    fi
}

configure_rb5_wifi() {
    # Create wpa_supplicant config for RB5
    local WPA_CONF="/data/misc/wifi/wpa_supplicant.conf"

    cat > "$WPA_CONF" <<WPAEOF
network={
    ssid="${WIFI_SSID}"
    key_mgmt=WPA-PSK
    pairwise=TKIP CCMP
    group=TKIP CCMP
    psk="${WIFI_PSK}"
}
WPAEOF

    # Enable wlan0
    ifconfig wlan0 up 2>/dev/null || true

    # Restart wpa_supplicant
    pkill wpa_supplicant 2>/dev/null || true
    sleep 1
    wpa_supplicant -B -i wlan0 -c "$WPA_CONF" 2>/dev/null || true
    dhclient wlan0 2>/dev/null || true

    # Wait for connection
    sleep 5
    if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
        log "Wi-Fi connected successfully"
    else
        warn "Wi-Fi connection may not be established yet. Continuing..."
    fi
}

# ============================================================
#  System Dependencies
# ============================================================
install_system_deps() {
    header "Installing System Dependencies"

    if [ "$OS_TYPE" = "macos" ]; then
        install_macos_deps
        return
    fi

    # ---- Linux (all variants) ----
    local APT_AVAILABLE=false
    command -v apt-get &>/dev/null && APT_AVAILABLE=true

    if [ "$APT_AVAILABLE" = false ]; then
        warn "apt-get not found. Skipping system package installation."
        warn "You may need to install Python 3.10+, espeak, v4l-utils manually."
        return
    fi

    info "Updating package lists..."
    apt-get update -qq 2>/dev/null || warn "apt-get update failed (offline?)"

    # Core packages needed everywhere
    local CORE_PKGS=(
        python3 python3-pip python3-venv python3-dev
        espeak espeak-data
        v4l-utils
        libjpeg-dev libpng-dev
        libatlas-base-dev
        git wget curl
    )

    # Audio stack
    local AUDIO_PKGS=(
        alsa-utils
        pulseaudio
    )

    # GStreamer for CSI/RTSP cameras
    local GST_PKGS=(
        libgstreamer1.0-dev
        gstreamer1.0-plugins-base
        gstreamer1.0-plugins-good
        gstreamer1.0-plugins-bad
        gstreamer1.0-tools
    )

    info "Installing core packages..."
    apt-get install -y -qq "${CORE_PKGS[@]}" 2>/dev/null || warn "Some core packages failed"

    info "Installing audio packages..."
    apt-get install -y -qq "${AUDIO_PKGS[@]}" 2>/dev/null || warn "Some audio packages failed"

    info "Installing GStreamer..."
    apt-get install -y -qq "${GST_PKGS[@]}" 2>/dev/null || warn "Some GStreamer packages failed"

    # ---- Platform-specific packages ----
    case "$PLATFORM" in
        rpi*)
            info "Installing Raspberry Pi camera stack..."
            apt-get install -y -qq \
                libcamera-apps libcamera-dev \
                python3-libcamera python3-picamera2 2>/dev/null || true
            log "Raspberry Pi packages installed"
            ;;
        rb5)
            info "Installing RB5 specific packages..."
            # RB5 Ubuntu has most things pre-installed
            # Ensure build tools for potential native compilation
            apt-get install -y -qq \
                build-essential cmake pkg-config \
                libopencv-dev 2>/dev/null || true

            # Check for QNN SDK
            if [ -d "/opt/qcom/aistack" ] || [ -n "${QNN_SDK_ROOT:-}" ]; then
                log "QNN SDK detected at ${QNN_SDK_ROOT:-/opt/qcom/aistack}"
            else
                warn "QNN SDK not found. CPU inference will be used."
                warn "For GPU/NPU acceleration, install QNN SDK to /opt/qcom/aistack"
            fi

            # RB5-specific audio configuration
            configure_rb5_audio
            # RB5-specific camera validation
            validate_rb5_cameras
            log "RB5 packages configured"
            ;;
        jetson)
            info "Installing Jetson packages..."
            apt-get install -y -qq \
                nvidia-jetpack 2>/dev/null || true
            log "Jetson packages installed"
            ;;
    esac

    log "System dependencies installed"
}

install_macos_deps() {
    if command -v brew &>/dev/null; then
        info "Installing via Homebrew..."
        brew install python@3.12 espeak 2>/dev/null || true
    else
        warn "Homebrew not found. Install it from https://brew.sh"
        warn "Then run: brew install python@3.12 espeak"
    fi
}

# ============================================================
#  RB5-Specific: Audio Configuration
# ============================================================
configure_rb5_audio() {
    header "Configuring RB5 Audio"

    # Check if speaker is connected
    if command -v aplay &>/dev/null; then
        local SPEAKER_INFO
        SPEAKER_INFO="$(aplay -l 2>/dev/null || echo '')"
        if echo "$SPEAKER_INFO" | grep -qi "card\|device"; then
            log "Audio device(s) detected via ALSA"
        else
            warn "No audio output detected. Connect speaker to RB5 board."
        fi
    fi

    # Configure ALSA mixer for RB5 speaker output
    # Based on Qualcomm RB5 User Guide section 4.6
    if command -v amixer &>/dev/null; then
        info "Configuring ALSA mixer for RB5 speaker..."
        {
            # WSA (Wall Smart Amplifier) speaker configuration
            amixer cset name='WSA_CDC_DMA_RX_0 Channels' 'Two' 2>/dev/null
            amixer cset name='WSA RX0 MUX' 'AIF1_PB' 2>/dev/null
            amixer cset name='WSA RX1 MUX' 'AIF1_PB' 2>/dev/null
            amixer cset name='WSA_RX0 INP0' 'RX0' 2>/dev/null
            amixer cset name='WSA_RX1 INP0' 'RX1' 2>/dev/null
            amixer cset name='WSA_COMP1 Switch' 1 2>/dev/null
            amixer cset name='WSA_COMP2 Switch' 1 2>/dev/null
            amixer cset name='SpkrLeft COMP Switch' 1 2>/dev/null
            amixer cset name='SpkrLeft BOOST Switch' 1 2>/dev/null
            amixer cset name='SpkrLeft VISENSE Switch' 1 2>/dev/null
            amixer cset name='SpkrLeft SWR DAC_Port Switch' 1 2>/dev/null
            amixer cset name='SpkrRight COMP Switch' 1 2>/dev/null
            amixer cset name='SpkrRight BOOST Switch' 1 2>/dev/null
            amixer cset name='SpkrRight VISENSE Switch' 1 2>/dev/null
            amixer cset name='SpkrRight SWR DAC_Port Switch' 1 2>/dev/null
            amixer cset name='WSA_RX0 Digital Volume' 68 2>/dev/null
            amixer cset name='WSA_RX1 Digital Volume' 68 2>/dev/null
            amixer cset name='WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1' 1 2>/dev/null
        } || true
        log "ALSA mixer configured for RB5 speakers"
    elif command -v tinymix &>/dev/null; then
        info "Configuring tinyALSA mixer for RB5 speaker..."
        {
            tinymix set 'WSA_CDC_DMA_RX_0 Channels' 'Two' 2>/dev/null
            tinymix set 'WSA RX0 MUX' 'AIF1_PB' 2>/dev/null
            tinymix set 'WSA RX1 MUX' 'AIF1_PB' 2>/dev/null
            tinymix set 'WSA_RX0 INP0' 'RX0' 2>/dev/null
            tinymix set 'WSA_RX1 INP0' 'RX1' 2>/dev/null
            tinymix set 'WSA_COMP1 Switch' 1 2>/dev/null
            tinymix set 'WSA_COMP2 Switch' 1 2>/dev/null
            tinymix set 'SpkrLeft COMP Switch' 1 2>/dev/null
            tinymix set 'SpkrLeft BOOST Switch' 1 2>/dev/null
            tinymix set 'SpkrLeft VISENSE Switch' 1 2>/dev/null
            tinymix set 'SpkrLeft SWR DAC_Port Switch' 1 2>/dev/null
            tinymix set 'SpkrRight COMP Switch' 1 2>/dev/null
            tinymix set 'SpkrRight BOOST Switch' 1 2>/dev/null
            tinymix set 'SpkrRight VISENSE Switch' 1 2>/dev/null
            tinymix set 'SpkrRight SWR DAC_Port Switch' 1 2>/dev/null
            tinymix set 'WSA_RX0 Digital Volume' 68 2>/dev/null
            tinymix set 'WSA_RX1 Digital Volume' 68 2>/dev/null
            tinymix set 'WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1' 1 2>/dev/null
        } || true
        log "tinyALSA mixer configured for RB5 speakers"
    fi

    # Configure digital microphone for voice feedback (optional)
    if command -v amixer &>/dev/null; then
        info "Configuring DMIC (digital microphone)..."
        {
            amixer cset name='TX DEC2 MUX' 'MSM_DMIC' 2>/dev/null
            amixer cset name='TX DMIC MUX2' 'DMIC2' 2>/dev/null
            amixer cset name='TX_CDC_DMA_TX_3 Channels' 'One' 2>/dev/null
            amixer cset name='TX_CDC_DMA_TX_3 SampleRate' 'KHZ_48' 2>/dev/null
            amixer cset name='TX_CDC_DMA_TX_3 Format' 'S16_LE' 2>/dev/null
            amixer cset name='TX_AIF1_CAP Mixer DEC2' 1 2>/dev/null
            amixer cset name='TX_DEC2 Volume' 84 2>/dev/null
            amixer cset name='MultiMedia1 Mixer TX_CDC_DMA_TX_3' 1 2>/dev/null
        } || true
        log "DMIC configured"
    fi

    # Ensure PulseAudio is running for espeak/pyttsx3
    if command -v pulseaudio &>/dev/null; then
        pulseaudio --start 2>/dev/null || true
        log "PulseAudio started"
    fi
}

# ============================================================
#  RB5-Specific: Camera Validation
# ============================================================
validate_rb5_cameras() {
    header "Validating RB5 Cameras"

    local CAMERAS_FOUND=0

    # Check V4L2 devices
    if command -v v4l2-ctl &>/dev/null; then
        local V4L_DEVICES
        V4L_DEVICES="$(v4l2-ctl --list-devices 2>/dev/null || echo '')"
        if [ -n "$V4L_DEVICES" ]; then
            info "V4L2 devices:"
            echo "$V4L_DEVICES" | tee -a "$SETUP_LOG"
            CAMERAS_FOUND=1
        fi
    fi

    # Check /dev/video* nodes
    local VIDEO_DEVS
    VIDEO_DEVS="$(ls /dev/video* 2>/dev/null || echo '')"
    if [ -n "$VIDEO_DEVS" ]; then
        info "Video device nodes: ${VIDEO_DEVS}"
        CAMERAS_FOUND=1
    fi

    # MIPI CSI cameras (RB5 uses qmmf framework)
    for i in 0 1 2 3; do
        local CAM_NAME
        CAM_NAME="$(cat /sys/class/video4linux/video${i}/name 2>/dev/null || echo '')"
        if [ -n "$CAM_NAME" ]; then
            info "  /dev/video${i}: ${CAM_NAME}"
        fi
    done

    # Check USB cameras
    if command -v lsusb &>/dev/null; then
        local USB_CAMS
        USB_CAMS="$(lsusb 2>/dev/null | grep -i 'camera\|webcam\|video\|logitech\|uvc' || echo '')"
        if [ -n "$USB_CAMS" ]; then
            info "USB cameras: ${USB_CAMS}"
            CAMERAS_FOUND=1
        fi
    fi

    # Test GStreamer camera pipeline (RB5 uses qtiqmmfsrc for MIPI CSI)
    if command -v gst-launch-1.0 &>/dev/null; then
        info "GStreamer available. Testing qtiqmmfsrc..."
        if gst-inspect-1.0 qtiqmmfsrc &>/dev/null; then
            log "GStreamer qtiqmmfsrc plugin available (MIPI CSI cameras)"
        else
            warn "qtiqmmfsrc not found. MIPI cameras may not work via GStreamer."
            info "USB cameras will still work via V4L2/OpenCV."
        fi
    fi

    if [ "$CAMERAS_FOUND" -eq 0 ]; then
        warn "No cameras detected!"
        warn "Connect a USB webcam or MIPI camera to the RB5 board."
        warn "For MIPI cameras, ensure the vision mezzanine is properly seated."
    else
        log "Camera(s) detected"
    fi
}

# ============================================================
#  Python Virtual Environment
# ============================================================
setup_python() {
    header "Setting Up Python Environment"

    # Find Python
    local PYTHON_CMD=""
    for cmd in python3.12 python3.11 python3.10 python3; do
        if command -v "$cmd" &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    done
    if [ -z "$PYTHON_CMD" ]; then
        error "Python 3.10+ not found. Install Python first."
    fi

    local PY_VERSION
    PY_VERSION="$($PYTHON_CMD --version 2>&1 | awk '{print $2}')"
    info "Using: ${PYTHON_CMD} (${PY_VERSION})"

    # Minimum version check
    local PY_MINOR
    PY_MINOR="$(echo "$PY_VERSION" | cut -d. -f2)"
    if [ "$PY_MINOR" -lt 10 ]; then
        error "Python 3.10+ required (found ${PY_VERSION})"
    fi

    # Create venv
    info "Creating virtual environment at ${VENV_DIR}..."
    $PYTHON_CMD -m venv "$VENV_DIR" || {
        warn "venv creation failed. Trying to install python3-venv..."
        apt-get install -y "python3.${PY_MINOR}-venv" 2>/dev/null || \
        apt-get install -y python3-venv 2>/dev/null || true
        $PYTHON_CMD -m venv "$VENV_DIR"
    }

    # Activate
    source "${VENV_DIR}/bin/activate"
    log "Virtual environment created and activated"

    # Upgrade pip
    info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel -q
    log "pip upgraded"
}

# ============================================================
#  Python Dependencies
# ============================================================
install_python_deps() {
    header "Installing Python Dependencies"

    source "${VENV_DIR}/bin/activate"

    # Platform-specific installation flags
    local PIP_FLAGS=()

    case "$PLATFORM" in
        rb5|rpi*|generic_arm|jetson)
            # ARM platforms: prefer binary wheels to avoid compilation
            PIP_FLAGS+=("--prefer-binary")
            # On aarch64, onnxruntime may need special build
            info "ARM platform: using --prefer-binary"
            ;;
    esac

    # Core requirements
    info "Installing core dependencies..."
    pip install "${PIP_FLAGS[@]}" \
        "opencv-python-headless>=4.8" \
        "numpy>=1.24" \
        "insightface>=0.7.3" \
        "onnxruntime>=1.16" \
        "scipy>=1.11" \
        "pyttsx3>=2.90" \
        "PyYAML>=6.0" \
        "Pillow>=10.0" \
        "scikit-learn>=1.3" \
        "albumentations>=1.3" \
        2>&1 | tail -5

    # RB5: Try QNN-enabled ONNX Runtime
    if [ "$PLATFORM" = "rb5" ]; then
        info "Attempting to install QNN-enabled ONNX Runtime..."
        pip install onnxruntime-qnn 2>/dev/null || \
            warn "onnxruntime-qnn not available. Using CPU provider."
    fi

    # Jetson: CUDA-enabled ONNX Runtime
    if [ "$PLATFORM" = "jetson" ]; then
        info "Installing CUDA-enabled ONNX Runtime..."
        pip install onnxruntime-gpu 2>/dev/null || \
            warn "onnxruntime-gpu failed. Using CPU provider."
    fi

    # Dev dependencies
    if [ "$DEV_MODE" = true ]; then
        info "Installing development dependencies..."
        pip install \
            "pytest>=7.0" "pytest-cov>=4.0" \
            "black>=23.0" "isort>=5.12" \
            "mypy>=1.0" "flake8>=6.0" \
            -q 2>/dev/null || true
        log "Dev dependencies installed"
    fi

    # Verify core imports
    info "Verifying Python imports..."
    python -c "
import cv2; print(f'  opencv:     {cv2.__version__}')
import numpy; print(f'  numpy:      {numpy.__version__}')
import insightface; print(f'  insightface: {insightface.__version__}')
import onnxruntime as ort; print(f'  onnxruntime: {ort.__version__}')
import pyttsx3; print('  pyttsx3:    OK')
import yaml; print('  PyYAML:     OK')
providers = ort.get_available_providers()
print(f'  ONNX providers: {providers}')
" 2>&1 || error "Python import verification failed!"

    log "Python dependencies installed and verified"
}

# ============================================================
#  Download Face Recognition Models
# ============================================================
download_models() {
    if [ "$SKIP_MODELS" = true ]; then
        info "Skipping model download (--skip-models)"
        return
    fi

    header "Downloading Face Recognition Models"

    source "${VENV_DIR}/bin/activate"

    # Select model based on platform
    local MODEL_PACK="buffalo_l"
    case "$PLATFORM" in
        rpi3|rpi)     MODEL_PACK="buffalo_s" ;;
        rpi4)         MODEL_PACK="buffalo_s" ;;
        generic_arm)  MODEL_PACK="buffalo_s" ;;
    esac

    if [ -d "${MODELS_DIR}/${MODEL_PACK}" ]; then
        log "Model pack '${MODEL_PACK}' already exists at ${MODELS_DIR}/${MODEL_PACK}"
        return
    fi

    info "Downloading model pack: ${MODEL_PACK} (~350MB for buffalo_l, ~100MB for buffalo_s)"
    python tools/download_models.py --model "$MODEL_PACK" 2>&1 || {
        warn "Model download via tool failed. Trying manual download..."
        python -c "
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='${MODEL_PACK}', root='${HOME}/.insightface')
app.prepare(ctx_id=-1, det_size=(640, 640))
print('Model downloaded successfully')
" 2>&1 || error "Failed to download models. Check internet connectivity."
    }

    log "Model pack '${MODEL_PACK}' downloaded"
}

# ============================================================
#  Select & Copy Configuration
# ============================================================
configure_app() {
    header "Configuring Application"

    local CONFIG_SRC=""
    local CONFIG_DST="${PROJECT_DIR}/app/config_active.yaml"

    case "$PLATFORM" in
        rb5)    CONFIG_SRC="${PROJECT_DIR}/app/config_rb5.yaml" ;;
        rpi*)   CONFIG_SRC="${PROJECT_DIR}/app/config_rpi.yaml" ;;
        *)      CONFIG_SRC="${PROJECT_DIR}/app/config.yaml" ;;
    esac

    if [ -f "$CONFIG_SRC" ]; then
        cp "$CONFIG_SRC" "$CONFIG_DST"
        log "Active config: ${CONFIG_SRC} -> config_active.yaml"
    else
        cp "${PROJECT_DIR}/app/config.yaml" "$CONFIG_DST"
        warn "Platform config not found. Using default config."
    fi

    # Create data and log directories
    mkdir -p "$DATA_DIR" "$LOGS_DIR"

    # Set ownership to the actual user (not root)
    local ACTUAL_USER
    ACTUAL_USER="$(logname 2>/dev/null || echo "${SUDO_USER:-$(whoami)}")"
    chown -R "${ACTUAL_USER}:${ACTUAL_USER}" "$DATA_DIR" "$LOGS_DIR" 2>/dev/null || true

    log "Directories created: data/, logs/"
}

# ============================================================
#  Systemd Service Installation
# ============================================================
install_service() {
    if [ "$INSTALL_SERVICE" = false ]; then
        info "Skipping service installation (--no-service)"
        return
    fi

    # Only on Linux with systemd
    if ! command -v systemctl &>/dev/null; then
        warn "systemctl not found. Skipping service installation."
        return
    fi

    header "Installing Systemd Service"

    local ACTUAL_USER
    ACTUAL_USER="$(logname 2>/dev/null || echo "${SUDO_USER:-pi}")"

    local CONFIG_FILE="${PROJECT_DIR}/app/config_active.yaml"
    if [ ! -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="${PROJECT_DIR}/app/config.yaml"
    fi

    # Environment variables for display
    local DISPLAY_ENV=""
    if [ "$PLATFORM" = "rb5" ]; then
        DISPLAY_ENV='Environment="XDG_RUNTIME_DIR=/run/user/root"'
        if [ "$RB5_OS_VARIANT" = "embedded" ]; then
            DISPLAY_ENV="${DISPLAY_ENV}
Environment=\"WAYLAND_DISPLAY=wayland-1\""
        fi
    else
        DISPLAY_ENV='Environment="DISPLAY=:0"'
    fi

    cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SVCEOF
[Unit]
Description=Reception Greeter – Face Recognition Camera System
After=network.target sound.target
Wants=network.target

[Service]
Type=simple
User=${ACTUAL_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
${DISPLAY_ENV}
Environment="PULSE_SERVER=unix:/run/user/1000/pulse/native"
ExecStartPre=${VENV_DIR}/bin/python -c "import insightface; print('Models OK')"
ExecStart=${VENV_DIR}/bin/python app/main.py --config ${CONFIG_FILE} --no-display
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits
MemoryMax=75%
CPUQuota=85%

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=${PROJECT_DIR}/data ${PROJECT_DIR}/logs ${HOME}/.insightface
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"

    log "Service '${SERVICE_NAME}' installed and enabled for auto-start"
    info "  Start now: sudo systemctl start ${SERVICE_NAME}"
    info "  View logs: journalctl -u ${SERVICE_NAME} -f"
    info "  Stop:      sudo systemctl stop ${SERVICE_NAME}"
}

# ============================================================
#  Post-Setup Validation
# ============================================================
validate_setup() {
    header "Validating Setup"

    local PASS=0
    local FAIL=0

    # 1. Python venv
    if [ -f "${VENV_DIR}/bin/python" ]; then
        log "Python venv: OK"
        ((PASS++))
    else
        warn "Python venv: MISSING"
        ((FAIL++))
    fi

    # 2. Core imports
    source "${VENV_DIR}/bin/activate"
    if python -c "import cv2, insightface, onnxruntime, pyttsx3, yaml" 2>/dev/null; then
        log "Python imports: OK"
        ((PASS++))
    else
        warn "Python imports: FAILED"
        ((FAIL++))
    fi

    # 3. Models
    local MODEL_CHECK="buffalo_l"
    case "$PLATFORM" in
        rpi3|rpi|generic_arm) MODEL_CHECK="buffalo_s" ;;
        rpi4)                 MODEL_CHECK="buffalo_s" ;;
    esac
    if [ -d "${MODELS_DIR}/${MODEL_CHECK}" ]; then
        log "Models (${MODEL_CHECK}): OK"
        ((PASS++))
    else
        warn "Models (${MODEL_CHECK}): MISSING (run: python tools/download_models.py)"
        ((FAIL++))
    fi

    # 4. Camera
    if ls /dev/video* &>/dev/null; then
        log "Camera device: OK"
        ((PASS++))
    elif [ "$OS_TYPE" = "macos" ]; then
        log "Camera device: macOS (FaceTime assumed)"
        ((PASS++))
    else
        warn "Camera device: NOT DETECTED"
        ((FAIL++))
    fi

    # 5. Audio
    if command -v espeak &>/dev/null || [ "$OS_TYPE" = "macos" ]; then
        log "TTS engine: OK"
        ((PASS++))
    else
        warn "TTS engine: espeak NOT FOUND"
        ((FAIL++))
    fi

    # 6. Config
    if [ -f "${PROJECT_DIR}/app/config_active.yaml" ]; then
        log "Active config: OK"
        ((PASS++))
    else
        warn "Active config: MISSING"
        ((FAIL++))
    fi

    # 7. Database directory
    if [ -d "$DATA_DIR" ]; then
        log "Data directory: OK"
        ((PASS++))
    else
        warn "Data directory: MISSING"
        ((FAIL++))
    fi

    # 8. Service (if Linux)
    if command -v systemctl &>/dev/null && [ "$INSTALL_SERVICE" = true ]; then
        if systemctl is-enabled "${SERVICE_NAME}" &>/dev/null; then
            log "Systemd service: ENABLED"
            ((PASS++))
        else
            warn "Systemd service: NOT ENABLED"
            ((FAIL++))
        fi
    fi

    echo ""
    echo -e "${BOLD}━━━ Validation Results ━━━${NC}"
    echo -e "  ${GREEN}Passed: ${PASS}${NC}  ${RED}Failed: ${FAIL}${NC}"

    if [ "$FAIL" -gt 0 ]; then
        warn "Some checks failed. See messages above for details."
    fi
}

# ============================================================
#  Print Summary
# ============================================================
print_summary() {
    local CONFIG_FILE="${PROJECT_DIR}/app/config_active.yaml"
    [ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="${PROJECT_DIR}/app/config.yaml"

    echo ""
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║  Reception Greeter – Setup Complete! v${VERSION}  ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Platform:  ${BOLD}${PLATFORM}${NC} (${OS_TYPE})"
    echo -e "  Arch:      ${ARCH}"
    echo -e "  RAM:       ${TOTAL_RAM_MB} MB"
    echo -e "  Config:    ${CONFIG_FILE}"
    echo -e "  Venv:      ${VENV_DIR}"
    echo -e "  Log:       ${SETUP_LOG}"
    echo ""
    echo -e "${BOLD}Quick Start:${NC}"
    echo ""
    echo "  # Activate virtual environment"
    echo "  source ${VENV_DIR}/bin/activate"
    echo ""
    echo "  # Enroll a person"
    echo "  python tools/enroll.py --name 'John Doe'"
    echo ""
    echo "  # Run the application"
    echo "  python app/main.py --config ${CONFIG_FILE}"
    echo ""

    if [ "$INSTALL_SERVICE" = true ] && command -v systemctl &>/dev/null; then
        echo -e "${BOLD}Auto-Start Service:${NC}"
        echo "  sudo systemctl start ${SERVICE_NAME}"
        echo "  sudo systemctl status ${SERVICE_NAME}"
        echo "  journalctl -u ${SERVICE_NAME} -f"
        echo ""
    fi

    echo -e "Full setup log: ${SETUP_LOG}"
    echo ""
}

# ============================================================
#  Main
# ============================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  Reception Greeter – Universal Auto-Setup v${VERSION}  ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""

    # Init log
    echo "=== Setup started at $(date) ===" > "$SETUP_LOG"

    parse_args "$@"

    # Root check (skip on macOS)
    if [ "$(uname -s)" != "Darwin" ] && [ "$(id -u)" -ne 0 ]; then
        error "Please run as root: sudo ./setup.sh"
    fi

    detect_platform
    check_network
    install_system_deps
    setup_python
    install_python_deps
    download_models
    configure_app
    install_service
    validate_setup
    print_summary

    echo "=== Setup completed at $(date) ===" >> "$SETUP_LOG"
}

main "$@"
