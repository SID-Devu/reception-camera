# Qualcomm RB5 Deployment Guide

> Complete guide to deploying **Reception Greeter** on the Qualcomm Robotics RB5 Development Kit (QRB5165).

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (One-Command Setup)](#quick-start)
3. [Board Preparation](#board-preparation)
4. [Deploy from Host Machine](#deploy-from-host-machine)
5. [On-Board Setup](#on-board-setup)
6. [Camera Configuration](#camera-configuration)
7. [Audio Configuration](#audio-configuration)
8. [Network Configuration](#network-configuration)
9. [QNN SDK / AI Acceleration](#qnn-sdk--ai-acceleration)
10. [Service Management](#service-management)
11. [Troubleshooting](#troubleshooting)
12. [Hardware Reference](#hardware-reference)

---

## Prerequisites

### Hardware
- Qualcomm Robotics RB5 Development Kit
- USB-C cable (debug port → host machine)
- Power adapter (12V DC, barrel jack)
- USB webcam **or** Vision Mezzanine board with MIPI cameras
- (Optional) HDMI monitor + cable
- (Optional) Ethernet cable

### Software on Host Machine
- ADB (Android SDK Platform Tools)
  - **Linux:** `sudo apt install android-tools-adb`
  - **macOS:** `brew install android-platform-tools`
  - **Windows:** [Download Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- Git

### RB5 OS
The setup supports both OS variants:
- **Linux Ubuntu** — Build ID contains `UBUN` (more familiar apt-based workflow)
- **Linux Embedded** — Built-in ROS2, optimized for robotics

---

## Quick Start

### Option A: Clone directly on the RB5

```bash
# Connect to RB5 via ADB
adb root
adb shell

# On the RB5:
cd /opt
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
chmod +x setup.sh scripts/*.sh
sudo ./setup.sh
```

That's it. The setup script will:
1. Detect the platform (QRB5165)
2. Detect OS variant (Ubuntu vs Embedded)
3. Install system dependencies
4. Create Python virtual environment
5. Install Python packages (with QNN ONNX Runtime if available)
6. Download AI models (insightface buffalo_l)
7. Configure camera, audio, display
8. Install systemd service for auto-start

### Option B: Deploy from Host (ADB Push)

```bash
# On your development machine:
git clone https://github.com/SID-Devu/reception-camera.git
cd reception-camera
chmod +x scripts/deploy_rb5.sh
./scripts/deploy_rb5.sh
```

### Option C: Deploy from Host (SSH)

```bash
./scripts/deploy_rb5.sh --ssh root@192.168.1.100
```

---

## Board Preparation

### First-Time Flashing

If the RB5 has no OS or you need to reflash:

1. **Install PCAT** on a Linux host machine (download from Thundercomm)
2. **Enter QDL Mode:** 
   - Power off, press and hold **F_DL** key on the board
   - Connect USB-C while holding F_DL
   - Release after 3 seconds
3. **Flash Image** using PCAT:
   - Select the firmware image (`QRB5165.UBUN.xxx` for Ubuntu)
   - Click Flash and wait ~10 minutes
4. **Reboot** the board

### DIP Switch Settings

Located at **DIP_SW_0** on the board:

| Pin | Function          | Recommended | Notes |
|-----|-------------------|-------------|-------|
| 1   | Onboard DMIC      | **ON**      | Enable digital microphone |
| 2   | Debug UART        | ON          | For serial debugging |
| 3   | Auto Power-Up     | **ON**      | Board boots on power connect |
| 4   | DSI0 / HDMI       | **OFF**     | OFF = DSI0 routed to HDMI bridge (LT9611UCX); ON = DSI0 to HS1 connector |
| 5   | SPI Select        | **OFF**     | OFF = SPI to onboard IMU; ON = SPI to LS3 connector |
| 6   | IMU External Clk  | OFF         | Default |

> **Important:** Pin 3 ON ensures the board auto-starts after power loss (essential for kiosk/reception deployment).
>
> **Vision Mezzanine DIP2:** If using DMIC audio recording with the Vision Mezzanine attached, set DIP2 Pin 2 to ON.

### Verify ADB Connection

```bash
# On host machine:
adb devices
# Should show: <serial>    device

adb root    # Get root access
adb shell   # Open terminal on RB5
```

---

## Deploy from Host Machine

The `deploy_rb5.sh` script handles everything:

```bash
# Full deploy: push files + run setup
./scripts/deploy_rb5.sh

# Push code only (no setup):
./scripts/deploy_rb5.sh --push-only

# Run setup on existing code:
./scripts/deploy_rb5.sh --setup-only

# Check board status:
./scripts/deploy_rb5.sh --status

# Interactive shell:
./scripts/deploy_rb5.sh --shell
```

### What deploy_rb5.sh does:
1. Verifies ADB connection
2. Creates tarball (excluding `.git`, `.venv`, `__pycache__`, etc.)
3. Pushes to `/opt/reception-camera` on the RB5
4. Extracts and sets permissions
5. Runs `setup.sh` on the board

---

## On-Board Setup

### Full Setup
```bash
sudo ./setup.sh
```

### RB5-Specific Board Configuration
```bash
sudo ./scripts/setup_rb5.sh
```

This runs RB5-specific configuration:
- OS variant detection
- DIP switch guidance
- Camera validation (USB + MIPI CSI)
- Audio mixer configuration (ALSA/tinyALSA)
- Display setup (Weston/Wayland)
- QNN SDK detection
- GStreamer plugin validation
- Thermal monitoring

### Post-Setup Validation
```bash
./scripts/validate.sh          # Full check
./scripts/validate.sh --quick  # Fast check
./scripts/validate.sh --fix    # Auto-fix issues
./scripts/validate.sh --json   # JSON output
```

---

## Camera Configuration

### USB Camera (Easiest)
Just plug in a USB webcam to the USB 3.0 port:
```bash
ls -l /dev/video*          # Should show video devices
v4l2-ctl --list-devices   # List with names
```

### MIPI CSI Camera (Vision Mezzanine)

1. **Attach Vision Mezzanine** to the mainboard (60-pin connector)
2. **Connect cameras:**
   - **Main camera (IMX577)** → CAM2 connector (CSI2) — 4K capable
   - **Tracking camera (OV9282)** → CAM1 connector (CSI1) — 720p

3. **Test with GStreamer:**
```bash
# Camera index mapping (Vision Mezzanine):
#   camera=0 -> IMX577 (4K main camera, CAM2/CSI2 connector)
#   camera=1 -> OV9282 (720p tracking camera, CAM1/CSI1 connector)

# 720p preview to Wayland display:
export XDG_RUNTIME_DIR=/run/user/root
gst-launch-1.0 qtiqmmfsrc camera=0 ! \
  'video/x-raw(memory:GBM),format=NV12,width=1280,height=720,framerate=30/1' ! \
  waylandsink

# 4K capture to file:
gst-launch-1.0 qtiqmmfsrc camera=0 ! \
  'video/x-raw(memory:GBM),format=NV12,width=3840,height=2160,framerate=30/1' ! \
  qtic2venc ! h264parse ! mp4mux ! filesink location=test_4k.mp4

# Headless test (no display):
gst-launch-1.0 qtiqmmfsrc camera=0 num-buffers=10 ! fakesink
```

### Configuration File
The app uses `app/config_rb5.yaml` with these camera settings:
```yaml
camera:
  resolution: [1280, 720]
  fps: 30
  use_gstreamer: true
  gstreamer_pipeline: "qtiqmmfsrc camera=0 ! video/x-raw,format=NV12,width=1280,height=720,framerate=30/1 ! videoconvert ! appsink"
```

---

## Audio Configuration

### Speaker Output (ALSA Mixer)

The setup script auto-configures speakers. Manual setup:

```bash
# WSA speaker configuration (from RB5 User Guide):
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

# Volume (0-84):
amixer cset name='WSA_RX0 Digital Volume' 68
amixer cset name='WSA_RX1 Digital Volume' 68

# Route audio:
amixer cset name='WSA_CDC_DMA_RX_0 Audio Mixer MultiMedia1' 1

# Test:
gst-launch-1.0 audiotestsrc wave=sine freq=440 ! alsasink
```

### Microphone (DMIC)

Ensure DIP_SW_0 Pin 1 is **ON**, then:

```bash
# DMIC Configuration (ALSA path - 8 commands per User Guide):
amixer cset name='TX DEC2 MUX' 'MSM_DMIC'
amixer cset name='TX DMIC MUX2' 'DMIC2'
amixer cset name='TX_CDC_DMA_TX_3 Channels' 'One'
amixer cset name='TX_CDC_DMA_TX_3 SampleRate' 'KHZ_48'
amixer cset name='TX_CDC_DMA_TX_3 Format' 'S16_LE'
amixer cset name='TX_AIF1_CAP Mixer DEC2' 1
amixer cset name='TX_DEC2 Volume' 84
amixer cset name='MultiMedia1 Mixer TX_CDC_DMA_TX_3' 1

# tinyALSA DMIC alternative (4 commands, uses DMIC3 not DMIC2):
# tinymix set 'TX DMIC MUX2' 'DMIC3'
# tinymix set 'TX_CDC_DMA_TX_3 Channels' 'One'
# tinymix set 'TX_AIF1_CAP Mixer DEC2' 1
# tinymix set 'MultiMedia1 Mixer TX_CDC_DMA_TX_3' 1

# Record test:
tinycap /tmp/test.wav -D 0 -d 7 -r 48000 -b 16 -T 5
```

### TTS (Text-to-Speech)

Install espeak for greeting announcements:
```bash
apt-get install -y espeak espeak-data
pulseaudio --start
espeak "Welcome to the office"  # Test
```

---

## Network Configuration

### Ethernet (Recommended for reliability)
Just connect an Ethernet cable to the RJ45 port:
```bash
ifconfig eth0   # Should show IP address
```

### Wi-Fi

**Method 1: Via setup.sh**
```bash
sudo ./setup.sh --wifi-ssid "OfficeWiFi" --wifi-psk "password123"
```

**Method 2: Manual wpa_supplicant**
```bash
cat > /data/misc/wifi/wpa_supplicant.conf << 'EOF'
network={
    ssid="OfficeWiFi"
    key_mgmt=WPA-PSK
    psk="password123"
    pairwise=TKIP CCMP
    group=TKIP CCMP
}
EOF
reboot
```

**Method 3: Open network**
```bash
cat > /data/misc/wifi/wpa_supplicant.conf << 'EOF'
network={
    ssid="GuestWiFi"
    key_mgmt=NONE
}
EOF
reboot
```

---

## QNN SDK / AI Acceleration

The QRB5165 has powerful AI accelerators:
- **Hexagon DSP (NPU230)** — Best for fixed quantized models
- **Adreno 650 GPU** — Good for FP16 inference
- **Kryo 585 CPU** — Fallback, still decent (~15-25 FPS)

### Install QNN SDK

1. Download from [Qualcomm AI Hub](https://aihub.qualcomm.com) or QPM
2. Install:
```bash
mkdir -p /opt/qcom/aistack
# Extract QNN SDK to /opt/qcom/aistack
export QNN_SDK_ROOT=/opt/qcom/aistack
```

3. Install ONNX Runtime with QNN:
```bash
pip install onnxruntime-qnn   # Or compile from source
```

### Performance Comparison (Approximate)

| Provider | FPS (720p) | Notes |
|----------|-----------|-------|
| QNNExecutionProvider (DSP) | 35-50 | Best, requires quantized model |
| QNNExecutionProvider (GPU) | 25-40 | Good FP16 performance |
| CPUExecutionProvider | 15-25 | No SDK needed |

The app auto-detects the best provider in `config_rb5.yaml`.

---

## Service Management

### Systemd Service

```bash
# Start
sudo systemctl start reception-greeter

# Stop
sudo systemctl stop reception-greeter

# Restart
sudo systemctl restart reception-greeter

# View status
sudo systemctl status reception-greeter

# View live logs
journalctl -u reception-greeter -f

# Disable auto-start
sudo systemctl disable reception-greeter

# Enable auto-start
sudo systemctl enable reception-greeter
```

### Manual Run

```bash
cd /opt/reception-camera
source .venv/bin/activate
python app/main.py --config app/config_rb5.yaml
```

### Run with Display (HDMI Connected)

```bash
export XDG_RUNTIME_DIR=/run/user/root
# For Linux Embedded also:
export WAYLAND_DISPLAY=wayland-1

python app/main.py --config app/config_rb5.yaml
```

---

## Troubleshooting

### ADB not connecting
```bash
# On host: restart ADB server
adb kill-server
adb start-server
adb devices

# Check USB cable is in the DEBUG port (not charging port)
```

### No camera feed
```bash
# Check devices
ls -l /dev/video*
v4l2-ctl --list-devices

# Test USB camera
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=10 ! fakesink

# Test MIPI camera
gst-launch-1.0 qtiqmmfsrc camera=0 num-buffers=10 ! fakesink

# If MIPI fails: check Vision Mezzanine flex cable connection
```

### No audio
```bash
# List audio devices
aplay -l
cat /proc/asound/cards

# Run speaker setup
sudo ./scripts/setup_rb5.sh  # Configures ALSA mixer

# Test
speaker-test -t sine -f 440 -l 1
```

### High temperature / throttling
```bash
# Check temp
cat /sys/class/thermal/thermal_zone*/temp

# If > 80°C:
# - Add heatsink (QRB5165 gets hot under AI load)
# - Add fan (bolt-on fan available from Thundercomm)
# - Reduce resolution in config: 640x480 instead of 1280x720
```

### Out of disk space
```bash
df -h
# Clean old data
python scripts/cleanup_old_data.py --days 30
# Or manually
rm -rf data/logs/*.log
```

### Service fails to start
```bash
# Check logs
journalctl -u reception-greeter -n 50 --no-pager

# Common issues:
# - Missing model: python tools/download_models.py
# - Camera in use: kill other camera processes
# - Permission: ensure data/ is writable
```

---

## Hardware Reference

### QRB5165 SoC Specifications

| Component | Specification |
|-----------|---------------|
| CPU | Kryo 585: 1x A77 @2.84GHz + 3x A77 @2.42GHz + 4x A55 @1.80GHz |
| GPU | Adreno 650 |
| DSP | Hexagon DSP |
| NPU | NPU230 (via QNN SDK) |
| RAM | 8 GB LPDDR5 |
| Storage | 128 GB UFS |
| Camera ISP | Spectra 480, up to 200 MP |
| Video | 8K30 / 4K120 encode/decode (H.265) |
| Connectivity | Wi-Fi 6, Bluetooth 5.2, Gigabit Ethernet |
| USB | USB 3.1 + USB-C (debug) |
| Display | HDMI (LT9611UCX bridge), 4K at 60 Hz |

### Board Connectors

| Connector | Location | Usage |
|-----------|----------|-------|
| USB-C (Debug) | Edge | ADB, fastboot, charging |
| USB 3.0 Type-A | Edge | USB webcam, peripherals |
| RJ45 Ethernet | Edge | Wired network |
| HDMI | Edge | Display output |
| 60-pin Header | Top | Vision Mezzanine |
| DC Barrel Jack | Edge | 12V power |
| MicroSD | Bottom | Extra storage |

### Reference Documents
- [RB5 Development Kit User Guide (80-88500-5 Rev. AF)](https://developer.qualcomm.com/hardware/robotics-rb5)
- [QNN SDK Documentation](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-50)
- [Qualcomm AI Hub](https://aihub.qualcomm.com)

---

## File Map (Setup Scripts)

| Script | Purpose | Run Where |
|--------|---------|-----------|
| `setup.sh` | Universal auto-setup (all platforms) | On device |
| `scripts/setup_rb5.sh` | RB5 board-level config (audio, camera, network) | On RB5 |
| `scripts/deploy_rb5.sh` | Deploy from host via ADB or SSH | On host machine |
| `scripts/validate.sh` | Post-setup health check | On device |
| `scripts/setup_edge_device.sh` | Legacy wrapper → redirects to setup.sh | On device |
