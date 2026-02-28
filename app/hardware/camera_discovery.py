"""
Camera auto-discovery module.

Scans for all available camera sources:
- USB cameras (V4L2 on Linux, DirectShow on Windows)
- CSI ribbon cameras (RPi libcamera, Qualcomm RB5 V4L2)
- RTSP / ONVIF network cameras (CCTV / IP cameras)
- GStreamer pipeline construction for edge devices

Returns a ranked list of CameraInfo objects, best source first.
"""

from __future__ import annotations

import glob
import logging
import os
import platform
import re
import socket
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import cv2

logger = logging.getLogger(__name__)


class CameraType(Enum):
    USB = "usb"
    CSI = "csi"           # RPi Camera Module / MIPI CSI
    RTSP = "rtsp"         # Network IP / CCTV camera
    GSTREAMER = "gstreamer"
    VIRTUAL = "virtual"   # e.g. /dev/video created by v4l2loopback


@dataclass
class CameraInfo:
    """Describes a discovered camera."""
    camera_type: CameraType
    source: object                  # int index, RTSP URL, or GStreamer pipeline string
    name: str = "Unknown Camera"
    resolution: tuple = (0, 0)      # detected native resolution (0,0 if unknown)
    is_working: bool = False        # True if we confirmed frames can be read
    priority: int = 100             # lower is better (used for sorting)
    device_path: str = ""           # e.g. /dev/video0

    def __repr__(self) -> str:
        return (
            f"CameraInfo(type={self.camera_type.value}, source={self.source!r}, "
            f"name={self.name!r}, res={self.resolution}, ok={self.is_working})"
        )


# ====================================================================== #
#  USB camera discovery
# ====================================================================== #

def _discover_usb_linux() -> List[CameraInfo]:
    """Enumerate USB cameras on Linux via /sys/class/video4linux."""
    cameras: List[CameraInfo] = []
    for dev_dir in sorted(glob.glob("/sys/class/video4linux/video*")):
        idx_str = os.path.basename(dev_dir).replace("video", "")
        try:
            idx = int(idx_str)
        except ValueError:
            continue

        name_path = os.path.join(dev_dir, "name")
        name = Path(name_path).read_text().strip() if os.path.exists(name_path) else f"video{idx}"

        # Skip non-capture devices (metadata nodes, codec nodes)
        caps_path = f"/sys/class/video4linux/video{idx}/device/capabilities"
        if os.path.exists(caps_path):
            caps = Path(caps_path).read_text().strip()
            # 0x1 = VIDEO_CAPTURE
            try:
                if not (int(caps, 16) & 0x1):
                    continue
            except ValueError:
                pass

        # Classify CSI vs USB
        device_link = os.path.realpath(os.path.join(dev_dir, "device"))
        is_csi = any(k in name.lower() for k in ("unicam", "bcm", "pisp", "msm_camera", "csi"))
        if "usb" in device_link.lower() or not is_csi:
            cam_type = CameraType.USB
            priority = 10
        else:
            cam_type = CameraType.CSI
            priority = 5  # Prefer CSI

        cameras.append(CameraInfo(
            camera_type=cam_type,
            source=idx,
            name=name,
            device_path=f"/dev/video{idx}",
            priority=priority,
        ))

    return cameras


def _discover_usb_windows() -> List[CameraInfo]:
    """Enumerate USB cameras on Windows by probing indices 0..9."""
    cameras: List[CameraInfo] = []
    for idx in range(10):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            cameras.append(CameraInfo(
                camera_type=CameraType.USB,
                source=idx,
                name=f"DirectShow Camera {idx}",
                resolution=(w, h),
                is_working=True,
                priority=10 + idx,
            ))
        else:
            cap.release()
    return cameras


# ====================================================================== #
#  CSI camera discovery (Raspberry Pi)
# ====================================================================== #

def _discover_csi_rpi() -> List[CameraInfo]:
    """Discover RPi camera module via libcamera."""
    cameras: List[CameraInfo] = []

    # Try libcamera-hello --list-cameras
    try:
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout + result.stderr
        # Parse output like: "0 : imx219 [3280x2464 10-bit RGGB] (/base/soc/...)"
        for m in re.finditer(r"(\d+)\s*:\s*(\S+)\s*\[(\d+)x(\d+)", output):
            idx = int(m.group(1))
            name = m.group(2)
            w, h = int(m.group(3)), int(m.group(4))
            cameras.append(CameraInfo(
                camera_type=CameraType.CSI,
                source=idx,
                name=f"RPi CSI: {name}",
                resolution=(w, h),
                is_working=True,  # listed by libcamera = functional
                priority=1,       # highest priority
            ))
    except Exception:
        pass

    return cameras


# ====================================================================== #
#  RTSP / ONVIF network camera discovery
# ====================================================================== #

def _discover_rtsp_cameras(rtsp_urls: Optional[List[str]] = None) -> List[CameraInfo]:
    """
    Discover RTSP / network cameras.

    1. Check user-provided RTSP URLs from config
    2. Scan common local network ports for RTSP (554) via quick socket probe
    """
    cameras: List[CameraInfo] = []

    # ---- User-provided URLs ----
    if rtsp_urls:
        for url in rtsp_urls:
            cameras.append(CameraInfo(
                camera_type=CameraType.RTSP,
                source=url,
                name=f"RTSP: {url}",
                priority=20,
            ))

    # ---- Network scan for RTSP on port 554 (local subnet) ----
    try:
        # Get local IP to derive subnet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        base_ip = ".".join(local_ip.split(".")[:3])
        logger.info("Scanning subnet %s.0/24 for RTSP cameras on port 554...", base_ip)

        for last_octet in range(1, 255):
            ip = f"{base_ip}.{last_octet}"
            if ip == local_ip:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.15)  # very short timeout for speed
                if sock.connect_ex((ip, 554)) == 0:
                    # RTSP port is open – likely a camera
                    # Try common RTSP paths
                    for path in ["", "/stream1", "/live", "/cam/realmonitor", "/h264/ch1/main/av_stream"]:
                        url = f"rtsp://{ip}:554{path}"
                        cameras.append(CameraInfo(
                            camera_type=CameraType.RTSP,
                            source=url,
                            name=f"Network Camera @ {ip}",
                            priority=25,
                        ))
                        break  # one entry per IP is enough for discovery
                sock.close()
            except Exception:
                pass
    except Exception:
        logger.debug("Subnet RTSP scan skipped (no network)")

    return cameras


# ====================================================================== #
#  GStreamer pipeline builders
# ====================================================================== #

def build_gstreamer_pipeline(
    camera_info: CameraInfo,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    platform_type: str = "rpi",
) -> Optional[str]:
    """
    Build an optimised GStreamer pipeline string for OpenCV.

    Returns None if GStreamer is not needed (plain USB on x86).
    """
    if camera_info.camera_type == CameraType.CSI:
        if platform_type.startswith("rpi"):
            # RPi: use libcamera via libcamerasrc  (requires OpenCV with GStreamer)
            return (
                f"libcamerasrc camera-name=/base/soc/i2c0mux/i2c@1/imx* ! "
                f"video/x-raw,width={width},height={height},framerate={fps}/1,format=NV12 ! "
                f"videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
            )
        if platform_type == "qrb5":
            # QRB5: use qtiqmmfsrc
            return (
                f"qtiqmmfsrc camera=0 ! "
                f"video/x-raw,format=NV12,width={width},height={height},framerate={fps}/1 ! "
                f"videoconvert ! video/x-raw,format=BGR ! appsink drop=1"
            )

    if camera_info.camera_type == CameraType.RTSP:
        url = camera_info.source
        return (
            f"rtspsrc location={url} latency=100 ! "
            f"rtph264depay ! h264parse ! avdec_h264 ! "
            f"videoconvert ! video/x-raw,format=BGR ! "
            f"videoscale ! video/x-raw,width={width},height={height} ! "
            f"appsink drop=1"
        )

    return None  # Plain USB, no GStreamer needed


# ====================================================================== #
#  Camera validation
# ====================================================================== #

def _validate_camera(cam: CameraInfo) -> CameraInfo:
    """Quick test to check if we can actually read a frame."""
    if cam.is_working:
        return cam  # already validated

    try:
        source = cam.source
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            ok, frame = cap.read()
            if ok and frame is not None:
                cam.is_working = True
                cam.resolution = (frame.shape[1], frame.shape[0])
        cap.release()
    except Exception as e:
        logger.debug("Camera validation failed for %s: %s", cam.source, e)

    return cam


# ====================================================================== #
#  Public API
# ====================================================================== #

def discover_cameras(
    rtsp_urls: Optional[List[str]] = None,
    validate: bool = True,
    scan_network: bool = True,
) -> List[CameraInfo]:
    """
    Discover all available cameras, ranked by priority (best first).

    Parameters
    ----------
    rtsp_urls : list of str, optional
        Explicit RTSP URLs to include (from config or user).
    validate : bool
        If True, test each camera by reading a frame.
    scan_network : bool
        If True, scan local subnet for RTSP cameras on port 554.

    Returns
    -------
    list of CameraInfo
        Sorted by priority (lower number = better).
    """
    os_name = platform.system()
    cameras: List[CameraInfo] = []

    logger.info("Starting camera discovery...")

    # ---- Platform-specific discovery ----
    if os_name == "Linux":
        cameras.extend(_discover_usb_linux())
        cameras.extend(_discover_csi_rpi())
    elif os_name == "Windows":
        cameras.extend(_discover_usb_windows())
    elif os_name == "Darwin":
        # macOS: probe indices
        for idx in range(5):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
                cameras.append(CameraInfo(
                    camera_type=CameraType.USB,
                    source=idx,
                    name=f"Camera {idx}",
                    resolution=(w, h),
                    is_working=True,
                    priority=10 + idx,
                ))
            else:
                cap.release()

    # ---- RTSP / network cameras ----
    if rtsp_urls or scan_network:
        cameras.extend(_discover_rtsp_cameras(rtsp_urls if rtsp_urls else ([] if not scan_network else None)))

    # ---- Validate ----
    if validate:
        cameras = [_validate_camera(c) for c in cameras]

    # ---- Sort by priority (lower = better), working cameras first ----
    cameras.sort(key=lambda c: (not c.is_working, c.priority))

    if cameras:
        logger.info("Discovered %d camera(s):", len(cameras))
        for c in cameras:
            status = "OK" if c.is_working else "FAIL"
            logger.info("  [%s] %s  type=%s  source=%s  res=%s",
                        status, c.name, c.camera_type.value, c.source, c.resolution)
    else:
        logger.warning("No cameras discovered!")

    return cameras
