#!/bin/bash

# Script to diagnose and fix systemd service issues for Wyoming Rocky TTS
# Run as root: sudo ./fix_systemd_services.sh

set -e

echo "========================================"
echo "Wyoming Rocky TTS - Service Fix Script"
echo "========================================"
echo ""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
ROCKY_USER="rocky"
APP_DIR="/home/${ROCKY_USER}/wyoming-rocky-tts"
DATA_DIR="/home/${ROCKY_USER}/.rocky_tts"
VENV_DIR="${APP_DIR}/venv"

echo "Checking system configuration..."
echo "================================"

# Check if directories exist
if [ -d "$APP_DIR" ]; then
    print_status "Application directory exists: $APP_DIR"
else
    print_error "Application directory missing: $APP_DIR"
    exit 1
fi

if [ -d "$VENV_DIR" ]; then
    print_status "Virtual environment exists: $VENV_DIR"
else
    print_error "Virtual environment missing: $VENV_DIR"
    exit 1
fi

# Check Python executables
echo ""
echo "Checking Python executables..."
echo "=============================="

# Check for python3 in venv
if [ -f "${VENV_DIR}/bin/python3" ]; then
    if [ -x "${VENV_DIR}/bin/python3" ]; then
        print_status "python3 exists and is executable"
        PYTHON_VERSION=$("${VENV_DIR}/bin/python3" --version 2>&1)
        print_info "Version: $PYTHON_VERSION"
    else
        print_warning "python3 exists but is not executable"
        print_info "Fixing permissions..."
        chmod +x "${VENV_DIR}/bin/python3"
        print_status "Fixed python3 permissions"
    fi
else
    print_warning "python3 not found in venv"
    
    # Check if python exists and create symlink
    if [ -f "${VENV_DIR}/bin/python" ]; then
        print_info "Creating python3 symlink from python..."
        ln -sf "${VENV_DIR}/bin/python" "${VENV_DIR}/bin/python3"
        chmod +x "${VENV_DIR}/bin/python3"
        print_status "Created python3 symlink"
    else
        print_error "No Python executable found in venv"
        print_error "Virtual environment is broken. Please recreate it."
        exit 1
    fi
fi

# Test Python modules
echo ""
echo "Testing Python modules..."
echo "========================"

# Test Wyoming server module
print_info "Testing wyoming_server module..."
if su - "${ROCKY_USER}" -c "cd '$APP_DIR' && '${VENV_DIR}/bin/python3' -c 'import src.wyoming_server' 2>&1"; then
    print_status "Wyoming server module imports successfully"
else
    print_error "Wyoming server module import failed"
    print_info "Checking for missing dependencies..."
    su - "${ROCKY_USER}" -c "'${VENV_DIR}/bin/pip' list | grep -E '(wyoming|TTS|torch)'"
fi

# Test web UI module
print_info "Testing web_ui module..."
if su - "${ROCKY_USER}" -c "cd '$APP_DIR' && '${VENV_DIR}/bin/python3' -c 'import src.web_ui' 2>&1"; then
    print_status "Web UI module imports successfully"
else
    print_error "Web UI module import failed"
fi

# Update systemd service files
echo ""
echo "Updating systemd service files..."
echo "================================="

# Create updated Wyoming TTS service
cat > /etc/systemd/system/wyoming-rocky.service << EOF
[Unit]
Description=Wyoming Rocky TTS Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${ROCKY_USER}
Group=${ROCKY_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${APP_DIR}"
Environment="HOME=/home/${ROCKY_USER}"
ExecStart=${VENV_DIR}/bin/python3 -m src.wyoming_server --config ${DATA_DIR}/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings - relaxed for compatibility
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=no
ReadWritePaths=${DATA_DIR} ${APP_DIR} /tmp
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

[Install]
WantedBy=multi-user.target
EOF

print_status "Wyoming TTS service file updated"

# Create updated Web UI service
cat > /etc/systemd/system/wyoming-rocky-web.service << EOF
[Unit]
Description=Wyoming Rocky TTS Web UI
After=network.target wyoming-rocky.service
Wants=network-online.target

[Service]
Type=simple
User=${ROCKY_USER}
Group=${ROCKY_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${APP_DIR}"
Environment="HOME=/home/${ROCKY_USER}"
ExecStart=${VENV_DIR}/bin/python3 -m src.web_ui --port 8088 --host 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings - relaxed for compatibility
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=no
ReadWritePaths=${DATA_DIR} ${APP_DIR} /tmp
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

[Install]
WantedBy=multi-user.target
EOF

print_status "Web UI service file updated"

# Test service commands manually
echo ""
echo "Testing service commands..."
echo "=========================="

print_info "Testing Wyoming server command..."
if su - "${ROCKY_USER}" -c "cd '$APP_DIR' && timeout 5 '${VENV_DIR}/bin/python3' -m src.wyoming_server --config '${DATA_DIR}/config.yaml' 2>&1 | head -20"; then
    print_status "Wyoming server starts successfully"
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        print_status "Wyoming server starts (timed out after 5s - normal)"
    else
        print_warning "Wyoming server may have issues (exit code: $EXIT_CODE)"
    fi
fi

print_info "Testing Web UI command..."
if su - "${ROCKY_USER}" -c "cd '$APP_DIR' && timeout 2 '${VENV_DIR}/bin/python3' -m src.web_ui --port 8088 --host 0.0.0.0 2>&1 | head -10"; then
    print_status "Web UI starts successfully"
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        print_status "Web UI starts (timed out after 2s - normal)"
    else
        print_warning "Web UI may have issues (exit code: $EXIT_CODE)"
    fi
fi

# Reload systemd
echo ""
echo "Reloading systemd..."
echo "==================="
systemctl daemon-reload
print_status "Systemd configuration reloaded"

# Stop existing services if running
echo ""
echo "Stopping existing services..."
echo "============================"
systemctl stop wyoming-rocky 2>/dev/null || true
systemctl stop wyoming-rocky-web 2>/dev/null || true
print_status "Services stopped"

# Start services
echo ""
echo "Starting services..."
echo "==================="

if systemctl start wyoming-rocky; then
    print_status "Wyoming TTS service started"
    sleep 3
    
    if systemctl is-active --quiet wyoming-rocky; then
        print_status "Wyoming TTS service is running"
    else
        print_error "Wyoming TTS service stopped after starting"
        echo ""
        echo "Recent logs:"
        journalctl -u wyoming-rocky -n 20 --no-pager
    fi
else
    print_error "Failed to start Wyoming TTS service"
    echo ""
    echo "Error details:"
    systemctl status wyoming-rocky --no-pager -l
    echo ""
    echo "Recent logs:"
    journalctl -u wyoming-rocky -n 20 --no-pager
fi

if systemctl start wyoming-rocky-web; then
    print_status "Web UI service started"
    sleep 2
    
    if systemctl is-active --quiet wyoming-rocky-web; then
        print_status "Web UI service is running"
    else
        print_error "Web UI service stopped after starting"
        echo ""
        echo "Recent logs:"
        journalctl -u wyoming-rocky-web -n 20 --no-pager
    fi
else
    print_error "Failed to start Web UI service"
    echo ""
    echo "Error details:"
    systemctl status wyoming-rocky-web --no-pager -l
    echo ""
    echo "Recent logs:"
    journalctl -u wyoming-rocky-web -n 20 --no-pager
fi

# Final status check
echo ""
echo "========================================"
echo "Final Status Check"
echo "========================================"

if systemctl is-active --quiet wyoming-rocky; then
    echo -e "${GREEN}✓ Wyoming TTS service: RUNNING${NC}"
else
    echo -e "${RED}✗ Wyoming TTS service: NOT RUNNING${NC}"
fi

if systemctl is-active --quiet wyoming-rocky-web; then
    echo -e "${GREEN}✓ Web UI service: RUNNING${NC}"
else
    echo -e "${RED}✗ Web UI service: NOT RUNNING${NC}"
fi

# Check ports
echo ""
echo "Port status:"
if ss -lntp 2>/dev/null | grep -q ":10202"; then
    echo -e "${GREEN}✓ Port 10202 (Wyoming): LISTENING${NC}"
else
    echo -e "${YELLOW}⚠ Port 10202 (Wyoming): NOT LISTENING${NC}"
fi

if ss -lntp 2>/dev/null | grep -q ":8088"; then
    echo -e "${GREEN}✓ Port 8088 (Web UI): LISTENING${NC}"
else
    echo -e "${YELLOW}⚠ Port 8088 (Web UI): NOT LISTENING${NC}"
fi

echo ""
echo "========================================"
echo "Troubleshooting Commands:"
echo "========================================"
echo "View Wyoming TTS logs:    journalctl -u wyoming-rocky -f"
echo "View Web UI logs:         journalctl -u wyoming-rocky-web -f"
echo "Test Wyoming command:     sudo -u $ROCKY_USER $VENV_DIR/bin/python3 -m src.wyoming_server --config $DATA_DIR/config.yaml"
echo "Test Web UI command:      sudo -u $ROCKY_USER $VENV_DIR/bin/python3 -m src.web_ui --port 8088"
echo ""