"""
Hardware auto-detection and configuration for Reception Greeter.

Supports: Raspberry Pi (3/4/5), Qualcomm Robotics RB5, generic x86/ARM,
USB cameras, CSI cameras, RTSP/CCTV cameras, and audio output devices.
"""

from app.hardware.detector import HardwareProfile, detect_hardware
from app.hardware.camera_discovery import CameraInfo, discover_cameras
from app.hardware.audio_discovery import AudioDevice, discover_audio_outputs

__all__ = [
    "HardwareProfile",
    "detect_hardware",
    "CameraInfo",
    "discover_cameras",
    "AudioDevice",
    "discover_audio_outputs",
]
