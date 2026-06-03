#!/bin/bash

# System Requirements Check Script for Wyoming Rocky TTS
# Run this before installation to verify your system is ready

echo "=============================================="
echo "Wyoming Rocky TTS - System Requirements Check"
echo "=============================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARN++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

# Check if running as root
echo "Checking system requirements..."
echo "--------------------------------"

if [ "$EUID" -eq 0 ]; then 
    check_pass "Running as root"
else
    check_fail "Not running as root (required for installation)"
fi

# Check OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "OS: $PRETTY_NAME"
    if [ "$ID" = "debian" ] && [ "$VERSION_ID" = "12" ]; then
        check_pass "Debian 12 detected (optimal)"
    elif [ "$ID" = "ubuntu" ] && [ "${VERSION_ID%%.*}" -ge "22" ]; then
        check_pass "Ubuntu $VERSION_ID detected (compatible)"
    else
        check_warn "OS may not be fully compatible (Debian 12 recommended)"
    fi
else
    check_fail "Cannot determine OS version"
fi

# Check memory
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
echo "Memory: ${TOTAL_MEM}MB"
if [ "$TOTAL_MEM" -ge 4000 ]; then
    check_pass "Sufficient memory (4GB+ recommended)"
elif [ "$TOTAL_MEM" -ge 3000 ]; then
    check_warn "Low memory - may work but could be slow"
else
    check_fail "Insufficient memory (need at least 3GB)"
fi

# Check disk space
AVAILABLE=$(df / | tail -1 | awk '{print int($4/1024)}')
echo "Free disk space: ${AVAILABLE}MB"
if [ "$AVAILABLE" -ge 3000 ]; then
    check_pass "Sufficient disk space"
else
    check_fail "Insufficient disk space (need at least 3GB)"
fi

# Check network
if ping -c 1 google.com >/dev/null 2>&1; then
    check_pass "Internet connection available"
else
    check_fail "No internet connection (required for downloads)"
fi

# Check if git is installed
if command -v git >/dev/null 2>&1; then
    check_pass "Git is installed"
else
    check_warn "Git not installed (will be installed)"
fi

# Check Python 3.11
if command -v python3.11 >/dev/null 2>&1; then
    check_pass "Python 3.11 is installed"
    
    # Check venv module
    if python3.11 -m venv --help >/dev/null 2>&1; then
        check_pass "Python 3.11 venv module available"
    else
        check_warn "Python 3.11 venv module missing (will be installed)"
    fi
else
    check_warn "Python 3.11 not installed (will be installed)"
fi

# Check if Python 3.11 is available in repos
if apt-cache show python3.11 >/dev/null 2>&1; then
    check_pass "Python 3.11 available in repositories"
else
    check_warn "Python 3.11 not in repos (PPA will be added)"
fi

# Check FFmpeg
if command -v ffmpeg >/dev/null 2>&1; then
    check_pass "FFmpeg is installed"
else
    check_warn "FFmpeg not installed (will be installed)"
fi

# Check ports
PORT_10202=$(ss -lntp 2>/dev/null | grep :10202)
PORT_8088=$(ss -lntp 2>/dev/null | grep :8088)

if [ -z "$PORT_10202" ]; then
    check_pass "Port 10202 is available"
else
    check_fail "Port 10202 is already in use"
fi

if [ -z "$PORT_8088" ]; then
    check_pass "Port 8088 is available"
else
    check_fail "Port 8088 is already in use"
fi

# Check if rocky user exists
if id -u rocky >/dev/null 2>&1; then
    check_warn "User 'rocky' already exists"
else
    check_pass "User 'rocky' will be created"
fi

# Summary
echo ""
echo "=============================================="
echo "Summary:"
echo "  Passed: $PASS checks"
echo "  Warnings: $WARN checks (can be fixed during install)"
echo "  Failed: $FAIL checks"
echo ""

if [ $FAIL -eq 0 ]; then
    if [ $WARN -eq 0 ]; then
        echo -e "${GREEN}✓ System is ready for installation!${NC}"
    else
        echo -e "${YELLOW}⚠ System has minor issues but installation should work${NC}"
    fi
    echo ""
    echo "Run the installer with:"
    echo "  curl -sSL https://raw.githubusercontent.com/jacko873/wyoming-rocky-tts/main/install.sh | sudo bash"
else
    echo -e "${RED}✗ System is not ready for installation${NC}"
    echo ""
    echo "Please fix the failed checks before proceeding."
    if [ "$EUID" -ne 0 ]; then
        echo "Most importantly, run this script as root: sudo ./check_system.sh"
    fi
fi
echo "=============================================="