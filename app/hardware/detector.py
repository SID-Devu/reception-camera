"""
Hardware auto-detection module.

Detects platform (Raspberry Pi, Qualcomm RB5, x86/ARM generic),
CPU architecture, available accelerators (GPU, NPU, DSP), memory,
thermal state, and returns an optimised HardwareProfile.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    RASPBERRY_PI_3 = "rpi3"
    RASPBERRY_PI_4 = "rpi4"
    RASPBERRY_PI_5 = "rpi5"
    RASPBERRY_PI_UNKNOWN = "rpi"
    QUALCOMM_RB5 = "qrb5"
    JETSON = "jetson"
    GENERIC_ARM = "arm"
    GENERIC_X86 = "x86"
    UNKNOWN = "unknown"


class AcceleratorType(Enum):
    NVIDIA_GPU = "nvidia_gpu"
    QUALCOMM_NPU = "qnn"          # Qualcomm Neural Network SDK
    QUALCOMM_DSP = "hexagon_dsp"  # Hexagon DSP
    MALI_GPU = "mali_gpu"         # ARM Mali
    VIDEOCORE = "videocore"       # RPi VideoCore GPU
    XNNPACK = "xnnpack"           # Cross-platform ARM SIMD
    CPU = "cpu"


@dataclass
class HardwareProfile:
    """Detected hardware configuration with optimised defaults."""
    platform: PlatformType = PlatformType.UNKNOWN
    arch: str = ""                        # e.g. "aarch64", "x86_64", "armv7l"
    os_name: str = ""                     # "Linux", "Windows", "Darwin"
    cpu_model: str = ""
    cpu_cores: int = 1
    total_ram_mb: int = 0
    accelerators: List[AcceleratorType] = field(default_factory=list)
    has_camera_csi: bool = False          # CSI ribbon camera detected
    gpu_mem_mb: int = 0                   # dedicated GPU/VideoCore memory
    thermal_throttled: bool = False

    # ---- Optimised config overrides (filled by profile logic) ----
    recommended_model_pack: str = "buffalo_l"
    recommended_det_size: int = 640
    recommended_detect_every_n: int = 3
    recommended_resolution: tuple = (1280, 720)
    recommended_fps: int = 30
    recommended_providers: List[str] = field(default_factory=lambda: ["CPUExecutionProvider"])
    recommended_use_gpu: bool = False

    def summary(self) -> str:
        accel = ", ".join(a.value for a in self.accelerators) or "none"
        return (
            f"Platform={self.platform.value}  Arch={self.arch}  OS={self.os_name}  "
            f"CPU={self.cpu_model}  Cores={self.cpu_cores}  RAM={self.total_ram_mb}MB  "
            f"Accelerators=[{accel}]  CSI={self.has_camera_csi}  "
            f"Throttled={self.thermal_throttled}  "
            f"Model={self.recommended_model_pack}  DetSize={self.recommended_det_size}  "
            f"Resolution={self.recommended_resolution}  FPS={self.recommended_fps}"
        )


# ====================================================================== #
#  Detection helpers
# ====================================================================== #

def _read_file_safe(path: str) -> str:
    """Read a file, returning empty string on any error."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""


def _run_cmd(cmd: List[str], timeout: int = 5) -> str:
    """Run a command and capture stdout."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _detect_platform() -> PlatformType:
    """Identify the SBC / platform."""
    os_name = platform.system()

    if os_name == "Windows":
        return PlatformType.GENERIC_X86

    # ---- Raspberry Pi ----
    model_file = _read_file_safe("/proc/device-tree/model")
    if "raspberry pi" in model_file.lower():
        if "pi 5" in model_file.lower():
            return PlatformType.RASPBERRY_PI_5
        if "pi 4" in model_file.lower():
            return PlatformType.RASPBERRY_PI_4
        if "pi 3" in model_file.lower():
            return PlatformType.RASPBERRY_PI_3
        return PlatformType.RASPBERRY_PI_UNKNOWN

    # ---- Qualcomm RB5 ----
    # RB5 uses Qualcomm QRB5165 SoC – check /proc/cpuinfo and device-tree
    cpuinfo = _read_file_safe("/proc/cpuinfo")
    dt_compatible = _read_file_safe("/proc/device-tree/compatible")
    if any(tag in (cpuinfo + dt_compatible).lower() for tag in [
        "qrb5165", "rb5", "qualcomm robotics", "sm8250", "qcs8250"
    ]):
        return PlatformType.QUALCOMM_RB5

    # ---- NVIDIA Jetson ----
    if "tegra" in cpuinfo.lower() or Path("/etc/nv_tegra_release").exists():
        return PlatformType.JETSON

    # ---- Generic ARM ----
    machine = platform.machine().lower()
    if machine in ("aarch64", "armv7l", "armv8l", "arm64"):
        return PlatformType.GENERIC_ARM

    return PlatformType.GENERIC_X86


def _detect_cpu_model() -> str:
    os_name = platform.system()
    if os_name == "Linux":
        info = _read_file_safe("/proc/cpuinfo")
        for line in info.splitlines():
            if line.startswith("model name") or line.startswith("Model"):
                return line.split(":", 1)[-1].strip()
    elif os_name == "Windows":
        return platform.processor() or "unknown"
    elif os_name == "Darwin":
        return _run_cmd(["sysctl", "-n", "machdep.cpu.brand_string"]) or "Apple Silicon"
    return "unknown"


def _detect_ram_mb() -> int:
    os_name = platform.system()
    if os_name == "Linux":
        mem = _read_file_safe("/proc/meminfo")
        for line in mem.splitlines():
            if line.startswith("MemTotal"):
                kb = int(re.search(r"(\d+)", line).group(1))
                return kb // 1024
    elif os_name == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulonglong),
                    ("ullAvailPhys", c_ulonglong),
                    ("ullTotalPageFile", c_ulonglong),
                    ("ullAvailPageFile", c_ulonglong),
                    ("ullTotalVirtual", c_ulonglong),
                    ("ullAvailVirtual", c_ulonglong),
                    ("ullAvailExtendedVirtual", c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys / (1024 * 1024))
        except Exception:
            pass
    return 0


def _detect_accelerators(plat: PlatformType) -> List[AcceleratorType]:
    accels = []
    os_name = platform.system()

    # ---- NVIDIA GPU ----
    if _run_cmd(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]):
        accels.append(AcceleratorType.NVIDIA_GPU)
    elif os_name == "Linux" and Path("/dev/nvidia0").exists():
        accels.append(AcceleratorType.NVIDIA_GPU)

    # ---- Qualcomm NPU / DSP ----
    if plat == PlatformType.QUALCOMM_RB5:
        # QRB5165 has Hexagon 698 DSP and Adreno 650 GPU
        if Path("/dev/adsprpc-smd").exists() or Path("/dsp").exists():
            accels.append(AcceleratorType.QUALCOMM_DSP)
        # QNN SDK presence
        if os.environ.get("QNN_SDK_ROOT") or Path("/opt/qcom/aistack").exists():
            accels.append(AcceleratorType.QUALCOMM_NPU)
        # Adreno GPU via OpenCL
        if Path("/dev/kgsl-3d0").exists():
            accels.append(AcceleratorType.MALI_GPU)  # reuse as generic GPU

    # ---- RPi VideoCore ----
    if plat in (PlatformType.RASPBERRY_PI_3, PlatformType.RASPBERRY_PI_4,
                PlatformType.RASPBERRY_PI_5, PlatformType.RASPBERRY_PI_UNKNOWN):
        if Path("/dev/vchiq").exists() or Path("/opt/vc").exists():
            accels.append(AcceleratorType.VIDEOCORE)

    # ---- XNNPACK (always available on ARM) ----
    machine = platform.machine().lower()
    if machine in ("aarch64", "armv7l", "armv8l", "arm64"):
        accels.append(AcceleratorType.XNNPACK)

    accels.append(AcceleratorType.CPU)
    return accels


def _detect_csi_camera(plat: PlatformType) -> bool:
    """Check if a CSI ribbon camera is connected (RPi / RB5)."""
    if plat in (PlatformType.RASPBERRY_PI_3, PlatformType.RASPBERRY_PI_4,
                PlatformType.RASPBERRY_PI_5, PlatformType.RASPBERRY_PI_UNKNOWN):
        # libcamera / v4l2 CSI
        if Path("/dev/video0").exists():
            # Could be USB or CSI – check for bcm2835
            v4l = _read_file_safe("/sys/class/video4linux/video0/name")
            if "unicam" in v4l.lower() or "bcm" in v4l.lower() or "pisp" in v4l.lower():
                return True
        # libcamera detection
        out = _run_cmd(["libcamera-hello", "--list-cameras"], timeout=3)
        if "Available cameras" in out and "No cameras" not in out:
            return True

    if plat == PlatformType.QUALCOMM_RB5:
        # RB5 uses V4L2 for MIPI CSI cameras
        for i in range(4):
            name = _read_file_safe(f"/sys/class/video4linux/video{i}/name")
            if "msm" in name.lower() or "cam" in name.lower():
                return True
    return False


def _check_thermal(plat: PlatformType) -> bool:
    """Check if device is thermally throttled."""
    if plat in (PlatformType.RASPBERRY_PI_3, PlatformType.RASPBERRY_PI_4,
                PlatformType.RASPBERRY_PI_5, PlatformType.RASPBERRY_PI_UNKNOWN):
        throttle = _run_cmd(["vcgencmd", "get_throttled"])
        if throttle and "0x0" not in throttle:
            return True
        temp_str = _read_file_safe("/sys/class/thermal/thermal_zone0/temp")
        if temp_str:
            try:
                temp_c = int(temp_str) / 1000
                return temp_c > 80
            except ValueError:
                pass
    if plat == PlatformType.QUALCOMM_RB5:
        temp_str = _read_file_safe("/sys/class/thermal/thermal_zone0/temp")
        if temp_str:
            try:
                return int(temp_str) / 1000 > 85
            except ValueError:
                pass
    return False


def _apply_profile(hw: HardwareProfile) -> None:
    """Set recommended config values based on detected hardware."""

    if hw.platform == PlatformType.RASPBERRY_PI_3:
        # Very constrained: 1GB RAM, Cortex-A53
        hw.recommended_model_pack = "buffalo_s"
        hw.recommended_det_size = 320
        hw.recommended_detect_every_n = 6
        hw.recommended_resolution = (640, 480)
        hw.recommended_fps = 15
        hw.recommended_providers = ["CPUExecutionProvider"]

    elif hw.platform == PlatformType.RASPBERRY_PI_4:
        # 2-8 GB RAM, Cortex-A72, decent
        hw.recommended_model_pack = "buffalo_s"
        hw.recommended_det_size = 480
        hw.recommended_detect_every_n = 4
        hw.recommended_resolution = (800, 600)
        hw.recommended_fps = 20
        hw.recommended_providers = ["CPUExecutionProvider"]

    elif hw.platform == PlatformType.RASPBERRY_PI_5:
        # Cortex-A76, 4-8GB, fastest Pi
        hw.recommended_model_pack = "buffalo_l"
        hw.recommended_det_size = 640
        hw.recommended_detect_every_n = 3
        hw.recommended_resolution = (1280, 720)
        hw.recommended_fps = 25
        hw.recommended_providers = ["CPUExecutionProvider"]

    elif hw.platform == PlatformType.RASPBERRY_PI_UNKNOWN:
        hw.recommended_model_pack = "buffalo_s"
        hw.recommended_det_size = 480
        hw.recommended_detect_every_n = 5
        hw.recommended_resolution = (640, 480)
        hw.recommended_fps = 15
        hw.recommended_providers = ["CPUExecutionProvider"]

    elif hw.platform == PlatformType.QUALCOMM_RB5:
        # QRB5165: Kryo 585 (8 cores), Adreno 650, Hexagon DSP, 8GB
        hw.recommended_model_pack = "buffalo_l"
        hw.recommended_det_size = 640
        hw.recommended_detect_every_n = 2
        hw.recommended_resolution = (1280, 720)
        hw.recommended_fps = 30
        providers = []
        if AcceleratorType.QUALCOMM_NPU in hw.accelerators:
            providers.append("QNNExecutionProvider")
        providers.append("CPUExecutionProvider")
        hw.recommended_providers = providers
        hw.recommended_use_gpu = AcceleratorType.QUALCOMM_NPU in hw.accelerators

    elif hw.platform == PlatformType.JETSON:
        hw.recommended_model_pack = "buffalo_l"
        hw.recommended_det_size = 640
        hw.recommended_detect_every_n = 2
        hw.recommended_resolution = (1280, 720)
        hw.recommended_fps = 30
        hw.recommended_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        hw.recommended_use_gpu = True

    elif hw.platform == PlatformType.GENERIC_ARM:
        # Unknown ARM board
        hw.recommended_model_pack = "buffalo_s"
        hw.recommended_det_size = 480
        hw.recommended_detect_every_n = 4
        hw.recommended_resolution = (800, 600)
        hw.recommended_fps = 20
        hw.recommended_providers = ["CPUExecutionProvider"]

    else:
        # x86 desktop / server – full power
        hw.recommended_model_pack = "buffalo_l"
        hw.recommended_det_size = 640
        hw.recommended_detect_every_n = 3
        hw.recommended_resolution = (1280, 720)
        hw.recommended_fps = 30
        if AcceleratorType.NVIDIA_GPU in hw.accelerators:
            hw.recommended_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            hw.recommended_use_gpu = True
        else:
            hw.recommended_providers = ["CPUExecutionProvider"]

    # ---- Thermal throttling: reduce workload ----
    if hw.thermal_throttled:
        hw.recommended_det_size = min(hw.recommended_det_size, 320)
        hw.recommended_detect_every_n = max(hw.recommended_detect_every_n, 6)
        hw.recommended_fps = min(hw.recommended_fps, 15)
        logger.warning("Device is thermally throttled – reducing workload")

    # ---- Low RAM guard ----
    if 0 < hw.total_ram_mb < 2048:
        hw.recommended_model_pack = "buffalo_s"
        hw.recommended_det_size = min(hw.recommended_det_size, 320)
        logger.warning("Low RAM (%dMB) – forcing lightweight model", hw.total_ram_mb)


# ====================================================================== #
#  Public API
# ====================================================================== #

def detect_hardware() -> HardwareProfile:
    """
    Run full hardware detection and return an optimised HardwareProfile.

    Call this once at startup before initialising the pipeline.
    """
    hw = HardwareProfile()
    hw.os_name = platform.system()
    hw.arch = platform.machine()
    hw.cpu_cores = os.cpu_count() or 1

    hw.platform = _detect_platform()
    hw.cpu_model = _detect_cpu_model()
    hw.total_ram_mb = _detect_ram_mb()
    hw.accelerators = _detect_accelerators(hw.platform)
    hw.has_camera_csi = _detect_csi_camera(hw.platform)
    hw.thermal_throttled = _check_thermal(hw.platform)

    _apply_profile(hw)

    logger.info("Hardware detected: %s", hw.summary())
    return hw
