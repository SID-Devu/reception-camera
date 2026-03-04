#!/usr/bin/env bash
# ============================================================
# Reception Greeter – Edge Device Setup (Legacy Wrapper)
# ============================================================
# This script is DEPRECATED in favor of the unified setup.sh
# at the project root. It now acts as a thin redirect.
#
# For the full auto-setup experience:
#   cd /path/to/reception-camera
#   sudo ./setup.sh
#
# For RB5-specific board-level configuration:
#   sudo ./scripts/setup_rb5.sh
#
# For post-setup validation:
#   ./scripts/validate.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}[!] This script has been superseded by the unified setup.sh${NC}"
echo ""
echo "  Available setup scripts:"
echo "    setup.sh            – Full auto-setup (all platforms)"
echo "    scripts/setup_rb5.sh  – RB5 board-level config (audio, camera, network)"
echo "    scripts/deploy_rb5.sh – Deploy from host to RB5 via ADB/SSH"
echo "    scripts/validate.sh   – Post-setup health check"
echo ""

# Forward to the new unified setup.sh
if [ -f "${PROJECT_DIR}/setup.sh" ]; then
    echo -e "${GREEN}[+] Forwarding to setup.sh...${NC}"
    echo ""
    exec bash "${PROJECT_DIR}/setup.sh" "$@"
else
    echo -e "${RED}[x] setup.sh not found at project root!${NC}"
    echo "    Please re-clone: git clone https://github.com/SID-Devu/reception-camera.git"
    exit 1
fi
