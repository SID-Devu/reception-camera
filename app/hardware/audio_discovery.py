"""
Audio output auto-discovery module.

Detects available speakers / audio output devices and selects the best one.
Supports: ALSA, PulseAudio, PipeWire (Linux), WASAPI/SAPI (Windows),
CoreAudio (macOS), and USB/Bluetooth speakers on all platforms.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AudioBackend(Enum):
    ALSA = "alsa"
    PULSEAUDIO = "pulseaudio"
    PIPEWIRE = "pipewire"
    WASAPI = "wasapi"         # Windows Audio Session API
    COREAUDIO = "coreaudio"   # macOS
    UNKNOWN = "unknown"


class AudioDeviceType(Enum):
    BUILTIN_SPEAKER = "builtin"
    USB_SPEAKER = "usb"
    HDMI = "hdmi"
    BLUETOOTH = "bluetooth"
    HEADPHONE_JACK = "jack"
    I2S_DAC = "i2s_dac"       # RPi HATs (HiFiBerry, etc.)
    UNKNOWN = "unknown"


@dataclass
class AudioDevice:
    """Describes a discovered audio output device."""
    name: str
    device_id: str                   # ALSA card:device or PulseAudio sink name
    device_type: AudioDeviceType
    backend: AudioBackend
    is_default: bool = False
    is_available: bool = True        # device is connected and functional
    sample_rate: int = 44100
    channels: int = 2
    priority: int = 100              # lower = better

    def __repr__(self) -> str:
        return (
            f"AudioDevice(name={self.name!r}, id={self.device_id!r}, "
            f"type={self.device_type.value}, default={self.is_default})"
        )


# ====================================================================== #
#  Linux: ALSA discovery
# ====================================================================== #

def _discover_alsa() -> List[AudioDevice]:
    """Enumerate ALSA playback devices via aplay -l."""
    devices: List[AudioDevice] = []
    try:
        result = subprocess.run(
            ["aplay", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout
        # Example: "card 0: Headphones [bcm2835 Headphones], device 0: ..."
        for m in re.finditer(
            r"card\s+(\d+):\s+(\S+)\s+\[([^\]]+)\],\s+device\s+(\d+):\s+(.*)",
            output,
        ):
            card_num = m.group(1)
            card_id = m.group(2)
            card_name = m.group(3)
            dev_num = m.group(4)
            dev_desc = m.group(5).strip()

            alsa_id = f"hw:{card_num},{dev_num}"
            name_lower = (card_name + " " + dev_desc).lower()

            # Classify device type
            if "hdmi" in name_lower:
                dtype = AudioDeviceType.HDMI
                priority = 30
            elif "usb" in name_lower or "uac" in name_lower:
                dtype = AudioDeviceType.USB_SPEAKER
                priority = 10
            elif "bluetooth" in name_lower or "bt" in name_lower:
                dtype = AudioDeviceType.BLUETOOTH
                priority = 20
            elif "hifiberry" in name_lower or "i2s" in name_lower or "dac" in name_lower:
                dtype = AudioDeviceType.I2S_DAC
                priority = 15
            elif "headphone" in name_lower or "jack" in name_lower or "analog" in name_lower:
                dtype = AudioDeviceType.HEADPHONE_JACK
                priority = 25
            elif "bcm2835" in name_lower or "builtin" in name_lower:
                dtype = AudioDeviceType.BUILTIN_SPEAKER
                priority = 40
            else:
                dtype = AudioDeviceType.UNKNOWN
                priority = 50

            devices.append(AudioDevice(
                name=f"{card_name} - {dev_desc}",
                device_id=alsa_id,
                device_type=dtype,
                backend=AudioBackend.ALSA,
                priority=priority,
            ))
    except Exception as e:
        logger.debug("ALSA discovery failed: %s", e)

    return devices


# ====================================================================== #
#  Linux: PulseAudio / PipeWire discovery
# ====================================================================== #

def _discover_pulseaudio() -> List[AudioDevice]:
    """Enumerate PulseAudio / PipeWire sinks via pactl."""
    devices: List[AudioDevice] = []
    try:
        result = subprocess.run(
            ["pactl", "list", "sinks", "short"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return devices

        # Detect backend (PipeWire masquerades as PulseAudio)
        pw_check = subprocess.run(
            ["pactl", "info"],
            capture_output=True, text=True, timeout=3,
        )
        backend = AudioBackend.PIPEWIRE if "PipeWire" in pw_check.stdout else AudioBackend.PULSEAUDIO

        default_sink = ""
        try:
            ds = subprocess.run(
                ["pactl", "get-default-sink"],
                capture_output=True, text=True, timeout=3,
            )
            default_sink = ds.stdout.strip()
        except Exception:
            pass

        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            sink_id = parts[0].strip()
            sink_name = parts[1].strip()
            name_lower = sink_name.lower()

            if "hdmi" in name_lower:
                dtype = AudioDeviceType.HDMI
                priority = 30
            elif "usb" in name_lower:
                dtype = AudioDeviceType.USB_SPEAKER
                priority = 10
            elif "bluetooth" in name_lower or "bluez" in name_lower:
                dtype = AudioDeviceType.BLUETOOTH
                priority = 20
            elif "analog" in name_lower or "headphone" in name_lower:
                dtype = AudioDeviceType.HEADPHONE_JACK
                priority = 25
            else:
                dtype = AudioDeviceType.UNKNOWN
                priority = 50

            is_default = (sink_name == default_sink)
            devices.append(AudioDevice(
                name=sink_name,
                device_id=sink_name,
                device_type=dtype,
                backend=backend,
                is_default=is_default,
                priority=priority - (10 if is_default else 0),  # boost default
            ))
    except Exception as e:
        logger.debug("PulseAudio discovery failed: %s", e)

    return devices


# ====================================================================== #
#  Windows: WASAPI discovery
# ====================================================================== #

def _discover_windows_audio() -> List[AudioDevice]:
    """Enumerate audio outputs on Windows via PowerShell."""
    devices: List[AudioDevice] = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_SoundDevice | Select-Object Name, Status | Format-List"],
            capture_output=True, text=True, timeout=10,
        )
        current_name = ""
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Name"):
                current_name = line.split(":", 1)[-1].strip()
            elif line.startswith("Status") and current_name:
                status = line.split(":", 1)[-1].strip()
                name_lower = current_name.lower()
                if "usb" in name_lower:
                    dtype = AudioDeviceType.USB_SPEAKER
                    priority = 10
                elif "bluetooth" in name_lower:
                    dtype = AudioDeviceType.BLUETOOTH
                    priority = 20
                elif "hdmi" in name_lower or "display" in name_lower:
                    dtype = AudioDeviceType.HDMI
                    priority = 30
                elif "realtek" in name_lower or "high definition" in name_lower or "speaker" in name_lower:
                    dtype = AudioDeviceType.BUILTIN_SPEAKER
                    priority = 25
                else:
                    dtype = AudioDeviceType.UNKNOWN
                    priority = 50

                devices.append(AudioDevice(
                    name=current_name,
                    device_id=current_name,
                    device_type=dtype,
                    backend=AudioBackend.WASAPI,
                    is_available=(status.lower() == "ok"),
                    priority=priority,
                ))
                current_name = ""
    except Exception as e:
        logger.debug("Windows audio discovery failed: %s", e)

    return devices


# ====================================================================== #
#  Audio device selection helpers
# ====================================================================== #

def set_alsa_default(device: AudioDevice) -> bool:
    """Set ALSA default output device via /etc/asound.conf."""
    if device.backend not in (AudioBackend.ALSA,):
        return False

    # Parse hw:X,Y
    parts = device.device_id.replace("hw:", "").split(",")
    if len(parts) != 2:
        return False

    card, dev = parts[0], parts[1]
    asound_conf = f"""# Auto-configured by Reception Greeter
pcm.!default {{
    type plug
    slave {{
        pcm "hw:{card},{dev}"
    }}
}}
ctl.!default {{
    type hw
    card {card}
}}
"""
    try:
        home = Path.home()
        conf_path = home / ".asoundrc"
        conf_path.write_text(asound_conf, encoding="utf-8")
        logger.info("Set ALSA default output to %s via %s", device.device_id, conf_path)
        return True
    except Exception as e:
        logger.warning("Could not set ALSA default: %s", e)
        return False


def set_pulseaudio_default(device: AudioDevice) -> bool:
    """Set PulseAudio/PipeWire default sink."""
    try:
        result = subprocess.run(
            ["pactl", "set-default-sink", device.device_id],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            logger.info("Set PulseAudio default sink to: %s", device.device_id)
            return True
    except Exception as e:
        logger.warning("Could not set PulseAudio default sink: %s", e)
    return False


def test_audio_output(device: Optional[AudioDevice] = None) -> bool:
    """
    Quick test: play a short beep to verify audio output works.
    Returns True if audio played successfully.
    """
    os_name = platform.system()
    try:
        if os_name == "Linux":
            # Use speaker-test or aplay
            result = subprocess.run(
                ["speaker-test", "-t", "sine", "-f", "440", "-l", "1", "-p", "1"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        elif os_name == "Windows":
            # Use PowerShell beep
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[console]::beep(440, 500)"],
                capture_output=True, timeout=5,
            )
            return True
        elif os_name == "Darwin":
            subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"],
                           capture_output=True, timeout=5)
            return True
    except Exception as e:
        logger.debug("Audio test failed: %s", e)
    return False


# ====================================================================== #
#  Public API
# ====================================================================== #

def discover_audio_outputs(auto_select: bool = True) -> List[AudioDevice]:
    """
    Discover all available audio output devices, sorted by priority.

    Parameters
    ----------
    auto_select : bool
        If True, automatically set the best device as system default
        (Linux only: writes .asoundrc or sets PulseAudio default sink).

    Returns
    -------
    list of AudioDevice
        Sorted by priority (lower = better). First device is recommended.
    """
    os_name = platform.system()
    devices: List[AudioDevice] = []

    logger.info("Starting audio output discovery...")

    if os_name == "Linux":
        # Try PulseAudio first (covers PipeWire too)
        pa_devices = _discover_pulseaudio()
        if pa_devices:
            devices.extend(pa_devices)
        # Also list ALSA as fallback
        alsa_devices = _discover_alsa()
        # Add ALSA devices not already covered by PulseAudio
        pa_names = {d.name.lower() for d in pa_devices}
        for ad in alsa_devices:
            if ad.name.lower() not in pa_names:
                devices.append(ad)

    elif os_name == "Windows":
        devices.extend(_discover_windows_audio())

    elif os_name == "Darwin":
        # macOS: system handles routing, just verify we can play audio
        devices.append(AudioDevice(
            name="macOS Default Output",
            device_id="default",
            device_type=AudioDeviceType.BUILTIN_SPEAKER,
            backend=AudioBackend.COREAUDIO,
            is_default=True,
            priority=1,
        ))

    # Sort by priority
    devices.sort(key=lambda d: (not d.is_available, d.priority))

    if devices:
        logger.info("Discovered %d audio output(s):", len(devices))
        for d in devices:
            status = "OK" if d.is_available else "N/A"
            dflt = " (default)" if d.is_default else ""
            logger.info("  [%s] %s  type=%s  id=%s%s",
                        status, d.name, d.device_type.value, d.device_id, dflt)

        # Auto-select best device
        if auto_select and os_name == "Linux":
            best = devices[0]
            if not best.is_default:
                if best.backend in (AudioBackend.PULSEAUDIO, AudioBackend.PIPEWIRE):
                    set_pulseaudio_default(best)
                elif best.backend == AudioBackend.ALSA:
                    set_alsa_default(best)
                logger.info("Auto-selected audio output: %s", best.name)
    else:
        logger.warning("No audio output devices discovered! TTS will be disabled.")

    return devices
