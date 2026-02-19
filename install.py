#!/usr/bin/env python3
"""
Reception Greeter - Cross-platform installer

Handles Windows insightface build issues by using --prefer-binary flag.
Works on Windows, macOS, and Linux.
"""

import subprocess
import sys
import platform
from pathlib import Path

REQUIREMENTS = [
    "opencv-python",
    "numpy",
    "insightface",
    "onnxruntime",
    "scipy",
    "pyttsx3",
    "PyYAML",
    "albumentations==1.4.24",
]


def run_command(cmd, description=""):
    """Run a shell command and return success status."""
    if description:
        print(f"\n{description}")
    print(f"  > {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def install_packages():
    """Install all required packages with OS-specific options."""
    os_name = platform.system()
    print(f"\n{'='*50}")
    print(f"Reception Greeter - Installation")
    print(f"Platform: {os_name} ({platform.release()})")
    print(f"Python: {sys.version.split()[0]}")
    print(f"{'='*50}\n")
    
    # Linux specific checks
    if os_name == "Linux":
        print("⚠ Linux detected")
        print("  If you haven't created a venv yet, run:")
        print("    python3 -m venv .venv")
        print("  If you get 'ensurepip is not available', install venv package:")
        print("    sudo apt-get install python3.12-venv")
        print("  Then activate it:")
        print("    source .venv/bin/activate\n")

    # Build pip install command
    cmd = [sys.executable, "-m", "pip", "install"]

    # Windows needs --prefer-binary for insightface
    if os_name == "Windows":
        print("⚠ Windows detected - using prebuilt binaries (--prefer-binary)")
        print("  This avoids C++ compiler requirements for insightface.\n")
        cmd.append("--prefer-binary")

    cmd.extend(REQUIREMENTS)

    # Run installation
    if not run_command(cmd, "Installing dependencies..."):
        print("\n❌ Installation failed!")
        print("\nTroubleshooting:")
        if os_name == "Windows":
            print("  • If insightface still fails, install Microsoft C++ Build Tools:")
            print("    https://visualstudio.microsoft.com/visual-cpp-build-tools/")
            print("  • Or downgrade to Python 3.10 for better compatibility")
        elif os_name == "Linux":
            print("  • Install build tools:")
            print("    sudo apt-get install python3-dev python3.12-dev build-essential")
            print("  • Or use prebuilt wheels:")
            print("    pip install --prefer-binary insightface opencv-python")
        print("  • Check that your virtual environment is activated")
        print("  • Check your internet connection")
        return False

    print("\n✅ Installation successful!")

    # Verify imports
    print("\nVerifying imports...")
    try:
        import insightface
        import cv2
        import onnxruntime
        print("  ✅ insightface")
        print("  ✅ opencv-python")
        print("  ✅ onnxruntime")
    except ImportError as e:
        print(f"  ❌ {e}")
        return False

    print(f"\n{'='*50}")
    print("✅ All dependencies installed successfully!")
    print(f"{'='*50}\n")
    print("Next steps:")
    print("  1. Download face models:")
    print("     python tools/download_models.py")
    print("  2. Run the application:")
    print("     python app/main.py --config app/config.yaml")
    return True


if __name__ == "__main__":
    success = install_packages()
    sys.exit(0 if success else 1)
