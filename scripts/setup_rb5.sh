#!/usr/bin/env bash
# ============================================================
#  Reception Greeter – Qualcomm RB5 Board-Level Setup
# ============================================================
#  Run this script ON the RB5 board itself (via adb shell or SSH).
#  Handles everything specific to the QRB5165 platform:
#
#    1. OS variant detection (Ubuntu vs Linux Embedded)
#    2. Network connectivity (Wi-Fi / Ethernet)
#    3. Camera setup (USB, MIPI-CSI via V4L2/qmmf)
#    4. Audio hardware (ALSA/tinyALSA/PulseAudio, speaker, DMIC)
#    5. Display output (Weston / HDMI)
#    6. QNN SDK / accelerator detection
#    7. GStreamer pipeline validation
#    8. Thermal monitoring
#    9. DIP switch guidance
#
#  Reference: Qualcomm Robotics RB5 Development Kit User Guide
#             (80-88500-5 Rev. AF)
#
#  Usage:
#    ssh root@rb5-device
#    cd /path/to/reception-camera
#    chmod +x scripts/setup_rb5.sh
#    sudo ./scripts/setup_rb5.sh
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

# ============================================================
#  Verify we're actually on an RB5
# ============================================================
verify_platform() {
    header "Verifying RB5 Platform"

    local DT_MODEL="" DT_COMPAT="" CPUINFO=""
    [ -f /proc/device-tree/model ] && DT_MODEL="$(tr -d '\0' < /proc/device-tree/model)"
    [ -f /proc/device-tree/compatible ] && DT_COMPAT="$(tr -d '\0' < /proc/device-tree/compatible)"
    [ -f /proc/cpuinfo ] && CPUINFO="$(cat /proc/cpuinfo)"

    local DETECT_LOWER
    DETECT_LOWER="$(echo "${DT_MODEL}${DT_COMPAT}${CPUINFO}" | tr '[:upper:]' '[:lower:]')"

    if ! echo "$DETECT_LOWER" | grep -qE "qrb5165|rb5|sm8250|qcs8250"; then
        error "This script is for the Qualcomm Robotics RB5 only.
       Detected: ${DT_MODEL:-unknown}
       Run setup.sh instead for generic platforms."
    fi

    log "Confirmed: Qualcomm Robotics RB5 (QRB5165)"
}

# ============================================================
#  Detect OS Variant
# ============================================================
OS_VARIANT="unknown"

detect_os_variant() {
    header "Detecting OS Variant"

    if [ -f /firmware/verinfo/ver_info.txt ]; then
        local BUILD_ID
        BUILD_ID="$(grep 'Meta_Build_ID' /firmware/verinfo/ver_info.txt 2>/dev/null || echo '')"
        if echo "$BUILD_ID" | grep -qi "UBUN"; then
            OS_VARIANT="ubuntu"
            log "OS: Linux Ubuntu (QRB5165)"
        else
            OS_VARIANT="embedded"
            log "OS: Linux Embedded (QRB5165)"
        fi
    elif [ -f /etc/os-release ] && grep -qi "ubuntu" /etc/os-release; then
        OS_VARIANT="ubuntu"
        log "OS: Linux Ubuntu"
    elif [ -f /usr/bin/ros_setup.sh ]; then
        # Linux Embedded comes with built-in ROS2
        OS_VARIANT="embedded"
        log "OS: Linux Embedded (ROS2 detected)"
    else
        OS_VARIANT="ubuntu"
        warn "Could not determine OS variant. Assuming Ubuntu."
    fi

    # Show system info
    info "Kernel:  $(uname -r)"
    info "Arch:    $(uname -m)"
    if [ -f /proc/meminfo ]; then
        local RAM_MB
        RAM_MB="$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)"
        info "RAM:     ${RAM_MB} MB"
    fi
    info "CPU:     $(nproc) cores"
}

# ============================================================
#  DIP Switch Guidance
# ============================================================
check_dip_switches() {
    header "DIP Switch Configuration"

    info "For proper operation, verify these DIP switch settings:"
    echo ""
    echo "  DIP_SW_0 (Board config):"
    echo "  ┌─────┬──────────────────────┬─────────────────────┐"
    echo "  │ Pin │ Function             │ Recommended         │"
    echo "  ├─────┼──────────────────────┼─────────────────────┤"
    echo "  │  1  │ Mic (DMIC)           │ ON  (onboard mic)   │"
    echo "  │  2  │ Debug UART           │ ON  (for debugging) │"
    echo "  │  3  │ Auto Power-Up        │ ON  (auto-boot)     │"
    echo "  │  4  │ HDMI                 │ OFF (HDMI output)   │"
    echo "  │  5  │ IMU sensor           │ ON  (default)       │"
    echo "  │  6  │ IMU external clock   │ OFF (default)       │"
    echo "  └─────┴──────────────────────┴─────────────────────┘"
    echo ""
    echo "  Key settings for reception-camera:"
    echo "    * Pin 1 ON  -> enables onboard digital mic (DMIC)"
    echo "    * Pin 3 ON  -> board auto-powers on (no button press needed)"
    echo "    * Pin 4 OFF -> DSI0 routed to HDMI bridge (for HDMI output)"
    echo "    * Pin 5 ON  -> routes SPI to LS3 connector (OFF = onboard IMU)"
    echo ""
    echo "  Vision Mezzanine DIP switches (if using CSI cameras):"
    echo "    * DIP2 Pin 2 ON -> required for onboard DMIC audio recording"
    echo ""

    if [ "$OS_VARIANT" = "embedded" ]; then
        info "Linux Embedded: Weston display enabled by default."
    fi
}

# ============================================================
#  Network Setup
# ============================================================
setup_network() {
    header "Network Configuration"

    # Check Ethernet first (most reliable)
    if ifconfig eth0 2>/dev/null | grep -q "inet "; then
        local ETH_IP
        ETH_IP="$(ifconfig eth0 | grep 'inet ' | awk '{print $2}')"
        log "Ethernet connected: ${ETH_IP}"
        return
    fi

    # Check Wi-Fi
    if ifconfig wlan0 2>/dev/null | grep -q "inet "; then
        local WLAN_IP
        WLAN_IP="$(ifconfig wlan0 | grep 'inet ' | awk '{print $2}')"
        log "Wi-Fi connected: ${WLAN_IP}"
        return
    fi

    warn "No network connection detected!"
    info ""
    info "Option 1 - Ethernet:"
    info "  Connect Ethernet cable to RJ45 port on the RB5 board"
    info ""
    info "Option 2 - Wi-Fi (edit wpa_supplicant.conf):"
    info "  1. Edit /data/misc/wifi/wpa_supplicant.conf:"
    info "     network={"
    info "         ssid=\"YOUR_WIFI_SSID\""
    info "         key_mgmt=WPA-PSK"
    info "         psk=\"YOUR_PASSWORD\""
    info "     }"
    info "  2. Reboot: reboot"
    info ""
    info "Option 3 - Wi-Fi (via setup.sh):"
    info "  sudo ./setup.sh --wifi-ssid 'YourSSID' --wifi-psk 'YourPass'"
    info ""

    # Try to enable and connect
    ifconfig wlan0 up 2>/dev/null || true
    if [ -f /data/misc/wifi/wpa_supplicant.conf ]; then
        info "Found existing wpa_supplicant.conf, attempting connection..."
        wpa_supplicant -B -i wlan0 -c /data/misc/wifi/wpa_supplicant.conf 2>/dev/null || true
        dhclient wlan0 2>/dev/null || true
        sleep 5
        if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
            log "Wi-Fi connected after retry"
        fi
    fi

    # Final check
    if ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log "Internet connectivity: OK"
    else
        warn "Still no internet. Package installation will fail."
        warn "Connect via Ethernet or Wi-Fi before continuing."
    fi
}

# ============================================================
#  Camera Configuration
# ============================================================
setup_cameras() {
    header "Camera Configuration"

    local CAMERAS_FOUND=0

    # ---- USB Cameras ----
    info "Scanning USB cameras..."
    local USB_CAMS=""
    if command -v lsusb &>/dev/null; then
        USB_CAMS="$(lsusb 2>/dev/null | grep -iE 'camera|webcam|video|uvc|logitech|microsoft' || echo '')"
    fi
    if [ -n "$USB_CAMS" ]; then
        log "USB camera(s) found:"
        echo "$USB_CAMS" | while read -r line; do
            echo "    ${line}"
        done
        CAMERAS_FOUND=1
    fi

    # ---- V4L2 Devices ----
    info "Scanning V4L2 devices..."
    if [ -d /sys/class/video4linux ]; then
        for dev in /sys/class/video4linux/video*; do
            if [ -f "${dev}/name" ]; then
                local DEV_NAME
                DEV_NAME="$(cat "${dev}/name")"
                local DEV_NUM
                DEV_NUM="$(basename "$dev")"
                info "  /dev/${DEV_NUM}: ${DEV_NAME}"
                CAMERAS_FOUND=1
            fi
        done
    fi

    # ---- MIPI CSI Cameras (via qtiqmmfsrc) ----
    info "Checking MIPI CSI cameras..."
    if command -v gst-inspect-1.0 &>/dev/null; then
        if gst-inspect-1.0 qtiqmmfsrc &>/dev/null; then
            log "GStreamer qtiqmmfsrc: Available (MIPI CSI support)"

            # Test camera 0
            info "Testing MIPI camera 0..."
            local CAM_TEST
            CAM_TEST="$(timeout 5 gst-launch-1.0 qtiqmmfsrc camera=0 num-buffers=1 ! \
                'video/x-raw(memory:GBM),format=NV12,width=640,height=480' ! fakesink 2>&1 || echo 'FAILED')"
            if echo "$CAM_TEST" | grep -qi "FAILED\|error"; then
                warn "MIPI camera 0: Not responding (check vision mezzanine connection)"
            else
                log "MIPI camera 0: Working"
                CAMERAS_FOUND=1
            fi
        else
            info "qtiqmmfsrc not available (MIPI cameras won't work via GStreamer)"
        fi
    fi

    # ---- Summary ----
    if [ "$CAMERAS_FOUND" -eq 0 ]; then
        warn "No cameras detected!"
        echo ""
        info "Camera setup options:"
        info "  USB Camera:"
        info "    1. Connect USB webcam to USB 3.0 port"
        info "    2. Verify: ls -l /dev/video*"
        info ""
        info "  MIPI CSI Camera (via Vision Mezzanine):"
        info "    1. Connect Vision Mezzanine board to mainboard"
        info "    2. Connect main camera (IMX577) to CAM2 connector"
        info "    3. Connect tracking camera (OV9282) to CAM1 connector"
        info "    4. Verify flex cables are properly seated"
        info "    5. Test: gst-launch-1.0 qtiqmmfsrc camera=0 ! video/x-raw,format=NV12,width=640,height=480 ! fakesink"
    else
        log "Camera(s) configured and ready"
    fi
}

# ============================================================
#  Audio Configuration
# ============================================================
setup_audio() {
    header "Audio Configuration"

    # ---- Detect audio system ----
    local AUDIO_SYSTEM="none"
    if command -v pulseaudio &>/dev/null; then
        AUDIO_SYSTEM="pulseaudio"
    elif command -v amixer &>/dev/null; then
        AUDIO_SYSTEM="alsa"
    elif command -v tinymix &>/dev/null; then
        AUDIO_SYSTEM="tinyalsa"
    fi
    info "Audio system: ${AUDIO_SYSTEM}"

    # ---- Speaker output configuration ----
    # Based on RB5 User Guide Section 4.6
    case "$AUDIO_SYSTEM" in
        alsa|pulseaudio)
            info "Configuring ALSA mixer for WSA speaker output..."
            {
                amixer cset name='WSA_CDC_DMA_RX_0 Channels' 'Two'
                amixer cset name='WSA RX0 MUX' 'AIF1_PB'
                amixer cset name='WSA RX1 MUX' 'AIF1_PB'
                amixer cset name='WSA_RX0 INP0' 'RX0'
                amixer cset name='WSA_RX1 INP0' 'RX1'
                amixer cset name='WSA_COMP1 Switch' 1
                amixer cset name='WSA_COMP2 Switch' 1
                amixer cset name='SpkrLeft COMP Switch' 1
                amixer cset name='SpkrLeft BOOST Switch' 1
                amixer cset name='SpkrLeft VISENSE Switch' 1
                amixer cset name='SpkrLeft SWR DAC_Port Switch' 1
                amixer cset name='SpkrRight COMP Switch' 1
                amixer cset name='SpkrRight BOOST Switch' 1
                amixer cset name='SpkrRight VISENSE Switch' 1
                amixer cset name='SpkrRight SWR DAC_Port Switch' 1
                amixer cset name='WSA_RX0 Digital Volume' 68
                amixer cset name='WSA_RX1 Digital Volume' 68
                amixer cset name='WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1' 1
            } 2>/dev/null || true
            log "ALSA speaker mixer configured"
            ;;
        tinyalsa)
            info "Configuring tinyALSA mixer for WSA speaker output..."
            {
                tinymix set 'WSA_CDC_DMA_RX_0 Channels' 'Two'
                tinymix set 'WSA RX0 MUX' 'AIF1_PB'
                tinymix set 'WSA RX1 MUX' 'AIF1_PB'
                tinymix set 'WSA_RX0 INP0' 'RX0'
                tinymix set 'WSA_RX1 INP0' 'RX1'
                tinymix set 'WSA_COMP1 Switch' 1
                tinymix set 'WSA_COMP2 Switch' 1
                tinymix set 'SpkrLeft COMP Switch' 1
                tinymix set 'SpkrLeft BOOST Switch' 1
                tinymix set 'SpkrLeft VISENSE Switch' 1
                tinymix set 'SpkrLeft SWR DAC_Port Switch' 1
                tinymix set 'SpkrRight COMP Switch' 1
                tinymix set 'SpkrRight BOOST Switch' 1
                tinymix set 'SpkrRight VISENSE Switch' 1
                tinymix set 'SpkrRight SWR DAC_Port Switch' 1
                tinymix set 'WSA_RX0 Digital Volume' 68
                tinymix set 'WSA_RX1 Digital Volume' 68
                tinymix set 'WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1' 1
            } 2>/dev/null || true
            log "tinyALSA speaker mixer configured"

            # tinyALSA DMIC recording (uses DMIC3, not DMIC2 like ALSA path)
            # Per User Guide page 66: tinyALSA DMIC requires 4 mixer controls
            # NOTE: Vision Mezzanine DIP2 Pin 2 must be ON for DMIC
            info "Configuring tinyALSA DMIC recording..."
            {
                tinymix set 'TX DMIC MUX2' 'DMIC3'
                tinymix set 'TX_CDC_DMA_TX_3 Channels' 'One'
                tinymix set 'TX_AIF1_CAP Mixer DEC2' 1
                tinymix set 'MultiMedia1 Mixer TX_CDC_DMA_TX_3' 1
            } 2>/dev/null || true
            log "tinyALSA DMIC configured"
            ;;
        *)
            warn "No audio system found. TTS will be silently disabled."
            ;;
    esac

    # ---- Microphone configuration (ALSA / PulseAudio path) ----
    info "Configuring onboard digital microphone..."
    if [ "$AUDIO_SYSTEM" = "alsa" ] || [ "$AUDIO_SYSTEM" = "pulseaudio" ]; then
        {
            amixer cset name='TX DEC2 MUX' 'MSM_DMIC'
            amixer cset name='TX DMIC MUX2' 'DMIC2'
            amixer cset name='TX_CDC_DMA_TX_3 Channels' 'One'
            amixer cset name='TX_CDC_DMA_TX_3 SampleRate' 'KHZ_48'
            amixer cset name='TX_CDC_DMA_TX_3 Format' 'S16_LE'
            amixer cset name='TX_AIF1_CAP Mixer DEC2' 1
            amixer cset name='TX_DEC2 Volume' 84
            amixer cset name='MultiMedia1 Mixer TX_CDC_DMA_TX_3' 1
        } 2>/dev/null || true
        log "DMIC configured"
    fi

    # ---- Start PulseAudio ----
    if command -v pulseaudio &>/dev/null; then
        pulseaudio --start 2>/dev/null || pulseaudio -D 2>/dev/null || true
        log "PulseAudio started"
    fi

    # ---- Install espeak for TTS ----
    if ! command -v espeak &>/dev/null; then
        info "Installing espeak for TTS..."
        if [ "$OS_VARIANT" = "ubuntu" ]; then
            apt-get install -y -qq espeak espeak-data 2>/dev/null || warn "espeak install failed"
        else
            warn "espeak not available on Linux Embedded."
            warn "TTS may not work. Consider USB audio + custom TTS."
        fi
    else
        log "espeak available"
    fi

    # ---- Test audio output ----
    info "Testing audio output..."
    if command -v aplay &>/dev/null; then
        # Generate a short beep test
        aplay -l 2>/dev/null | head -5
        info "Audio devices listed above. Run 'speaker-test -t sine -f 440 -l 1' to test."
    fi
}

# ============================================================
#  Display Configuration
# ============================================================
setup_display() {
    header "Display Configuration"

    # Check if HDMI/display is connected
    if [ "$OS_VARIANT" = "embedded" ]; then
        info "Linux Embedded: Weston launches automatically on boot."
        info "Set WAYLAND_DISPLAY=wayland-1 for display apps."
        export WAYLAND_DISPLAY=wayland-1
        export XDG_RUNTIME_DIR=/run/user/root
    else
        info "Ubuntu: Weston starts automatically."
        export XDG_RUNTIME_DIR=/run/user/root
    fi

    # Verify display (if connected)
    if [ -n "$(ls /dev/dri/card* 2>/dev/null)" ]; then
        log "Display driver present (/dev/dri/card*)"
    fi

    info "For headless operation (no monitor), use --no-display flag:"
    info "  python app/main.py --config app/config_rb5.yaml --no-display"
}

# ============================================================
#  Accelerator / QNN SDK Detection
# ============================================================
setup_accelerators() {
    header "Accelerator Detection"

    info "QRB5165 SoC capabilities:"
    info "  CPU: Kryo 585 (1x Cortex-A77 @ 2.84GHz + 3x A77 @ 2.42GHz + 4x A55 @ 1.80GHz)"
    info "  GPU: Adreno 650"
    info "  DSP: Hexagon DSP"
    info "  NPU: NPU230 (via QNN SDK)"

    # Check Hexagon DSP
    if [ -e /dev/adsprpc-smd ] || [ -d /dsp ]; then
        log "Hexagon DSP: Accessible"
    else
        warn "Hexagon DSP: Not detected (may need firmware)"
    fi

    # Check Adreno GPU (OpenCL)
    if [ -e /dev/kgsl-3d0 ]; then
        log "Adreno 650 GPU: Accessible (/dev/kgsl-3d0)"
    else
        info "Adreno GPU: Not detected via kgsl"
    fi

    # Check QNN SDK
    local QNN_ROOT="${QNN_SDK_ROOT:-/opt/qcom/aistack}"
    if [ -d "$QNN_ROOT" ]; then
        log "QNN SDK: Found at ${QNN_ROOT}"
        info "  ONNX Runtime can use QNNExecutionProvider for acceleration"

        # Verify QNN libraries
        if ls "${QNN_ROOT}/lib/"*.so &>/dev/null 2>&1; then
            log "QNN libraries present"
        fi
    else
        warn "QNN SDK: NOT FOUND"
        info "  For 3-5x inference speedup, install QNN SDK:"
        info "    1. Download from Qualcomm AI Hub or QPM"
        info "    2. Install to /opt/qcom/aistack"
        info "    3. Export: QNN_SDK_ROOT=/opt/qcom/aistack"
        info ""
        info "  Without QNN SDK, CPU inference is used (still ~15-25 FPS)"
    fi

    # Show ONNX Runtime providers
    if [ -f "${PROJECT_DIR}/.venv/bin/python" ]; then
        info "Available ONNX Runtime providers:"
        "${PROJECT_DIR}/.venv/bin/python" -c "
import onnxruntime as ort
for p in ort.get_available_providers():
    print(f'    {p}')
" 2>/dev/null || info "    (Python venv not yet set up)"
    fi
}

# ============================================================
#  Thermal Monitoring
# ============================================================
check_thermal() {
    header "Thermal Status"

    for zone in /sys/class/thermal/thermal_zone*; do
        if [ -f "${zone}/type" ] && [ -f "${zone}/temp" ]; then
            local TYPE TEMP_MC TEMP_C
            TYPE="$(cat "${zone}/type" 2>/dev/null || echo 'unknown')"
            TEMP_MC="$(cat "${zone}/temp" 2>/dev/null || echo '0')"
            TEMP_C="$(echo "scale=1; ${TEMP_MC}/1000" | bc 2>/dev/null || echo '?')"
            info "  ${TYPE}: ${TEMP_C}°C"
        fi
    done

    # Warning if hot
    local CPU_TEMP
    CPU_TEMP="$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo '0')"
    if [ "$CPU_TEMP" -gt 80000 ] 2>/dev/null; then
        warn "CPU temperature above 80°C! Consider adding fan/heatsink."
        warn "Order bolt-on fan from Qualcomm RB5 accessories."
    elif [ "$CPU_TEMP" -gt 60000 ] 2>/dev/null; then
        info "CPU temperature OK (< 80°C)"
    fi
}

# ============================================================
#  GStreamer Validation
# ============================================================
validate_gstreamer() {
    header "GStreamer Validation"

    if ! command -v gst-launch-1.0 &>/dev/null; then
        warn "GStreamer not installed!"
        if [ "$OS_VARIANT" = "ubuntu" ]; then
            info "Install: apt-get install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad"
        fi
        return
    fi

    local GST_VER
    GST_VER="$(gst-launch-1.0 --version | head -1)"
    log "GStreamer: ${GST_VER}"

    # Check key plugins
    local PLUGINS=("qtiqmmfsrc" "qtic2venc" "qtic2vdec" "waylandsink" "v4l2src" "pulsesink")
    for plugin in "${PLUGINS[@]}"; do
        if gst-inspect-1.0 "$plugin" &>/dev/null; then
            log "  ${plugin}: Available"
        else
            info "  ${plugin}: Not available"
        fi
    done
}

# ============================================================
#  Final Validation
# ============================================================
run_validation() {
    header "System Validation Summary"

    local PASS=0 FAIL=0 WARN_COUNT=0

    # Platform
    log "Platform: Qualcomm RB5 (${OS_VARIANT})"
    ((PASS++))

    # Network
    if ping -c 1 -W 3 8.8.8.8 &>/dev/null; then
        log "Network: Connected"
        ((PASS++))
    else
        warn "Network: No internet"
        ((WARN_COUNT++))
    fi

    # Camera
    if ls /dev/video* &>/dev/null; then
        log "Camera: Device(s) present"
        ((PASS++))
    else
        warn "Camera: No devices"
        ((FAIL++))
    fi

    # Audio
    if command -v espeak &>/dev/null; then
        log "TTS (espeak): Available"
        ((PASS++))
    else
        warn "TTS (espeak): Missing"
        ((WARN_COUNT++))
    fi

    if command -v aplay &>/dev/null || command -v tinyplay &>/dev/null; then
        log "Audio output: Available"
        ((PASS++))
    else
        warn "Audio output: Not found"
        ((FAIL++))
    fi

    # Python
    if command -v python3 &>/dev/null; then
        local PY_VER
        PY_VER="$(python3 --version)"
        log "Python: ${PY_VER}"
        ((PASS++))
    else
        warn "Python: Not found"
        ((FAIL++))
    fi

    # GStreamer
    if command -v gst-launch-1.0 &>/dev/null; then
        log "GStreamer: Available"
        ((PASS++))
    else
        warn "GStreamer: Missing"
        ((WARN_COUNT++))
    fi

    # QNN SDK
    if [ -d "${QNN_SDK_ROOT:-/opt/qcom/aistack}" ]; then
        log "QNN SDK: Available (GPU/NPU acceleration)"
        ((PASS++))
    else
        info "QNN SDK: Not installed (CPU-only inference)"
        ((WARN_COUNT++))
    fi

    echo ""
    echo -e "${BOLD}━━━ Results ━━━${NC}"
    echo -e "  ${GREEN}Pass: ${PASS}${NC}  ${YELLOW}Warnings: ${WARN_COUNT}${NC}  ${RED}Fail: ${FAIL}${NC}"

    if [ "$FAIL" -gt 0 ]; then
        echo ""
        warn "Critical issues found. Fix them before running the application."
    fi
}

# ============================================================
#  Main
# ============================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  Reception Greeter – RB5 Board Setup        ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""

    if [ "$(id -u)" -ne 0 ]; then
        error "Please run as root: sudo ./scripts/setup_rb5.sh"
    fi

    verify_platform
    detect_os_variant
    check_dip_switches
    setup_network
    setup_cameras
    setup_audio
    setup_display
    setup_accelerators
    check_thermal
    validate_gstreamer
    run_validation

    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║  RB5 Board Setup Complete!                  ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    info "Next: Run the main setup to install Python + dependencies:"
    info "  sudo ./setup.sh"
    echo ""
}

main "$@"
