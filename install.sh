#!/bin/bash

set -e

echo "=============================================="
echo "Wyoming Rocky TTS Installer for Debian 12"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root"
    exit 1
fi

# Check Debian version
if ! grep -q "^ID=debian" /etc/os-release || ! grep -q "VERSION_ID=\"12\"" /etc/os-release; then
    echo "Warning: This installer is designed for Debian 12"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Configuration
GITHUB_REPO="${GITHUB_REPO:-https://github.com/jacko873/wyoming-rocky-tts.git}"
ROCKY_USER="rocky"
APP_DIR="/home/${ROCKY_USER}/wyoming-rocky-tts"
DATA_DIR="/home/${ROCKY_USER}/.rocky_tts"
CACHE_DIR="/var/cache/wyoming-rocky"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="wyoming-rocky"
WYOMING_PORT="${WYOMING_PORT:-10202}"
WEB_PORT="${WEB_PORT:-8088}"

echo "Configuration:"
echo "  GitHub repo: ${GITHUB_REPO}"
echo "  Install dir: ${APP_DIR}"
echo "  Data dir: ${DATA_DIR}"
echo "  Cache dir: ${CACHE_DIR}"
echo "  Wyoming port: ${WYOMING_PORT}"
echo "  Web UI port: ${WEB_PORT}"
echo ""

# Update system
echo "Updating system packages..."
apt update
apt upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    ffmpeg \
    build-essential \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    wget \
    curl \
    sqlite3 \
    sox \
    libsox-dev \
    libsox-fmt-all \
    espeak-ng

# Create user
echo "Creating Rocky user..."
if ! id -u "$ROCKY_USER" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$ROCKY_USER"
    echo "User $ROCKY_USER created"
else
    echo "User $ROCKY_USER already exists"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$DATA_DIR"
mkdir -p "$CACHE_DIR"
chown -R "$ROCKY_USER:$ROCKY_USER" "$DATA_DIR"
chown -R "$ROCKY_USER:$ROCKY_USER" "$CACHE_DIR"

# Clone or update repository
echo "Fetching repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Repository exists, updating..."
    cd "$APP_DIR"
    su - "$ROCKY_USER" -c "cd $APP_DIR && git pull"
else
    echo "Cloning repository..."
    su - "$ROCKY_USER" -c "git clone $GITHUB_REPO $APP_DIR"
fi

chown -R "$ROCKY_USER:$ROCKY_USER" "$APP_DIR"

# Create Python virtual environment
echo "Setting up Python environment..."
if [ ! -d "$VENV_DIR" ]; then
    su - "$ROCKY_USER" -c "python3.11 -m venv $VENV_DIR"
fi

# Upgrade pip
su - "$ROCKY_USER" -c "$VENV_DIR/bin/pip install --upgrade pip setuptools wheel"

# Install Python dependencies
echo "Installing Python dependencies (this may take a while)..."
su - "$ROCKY_USER" -c "cd $APP_DIR && $VENV_DIR/bin/pip install -r requirements.txt"

# Download Rocky reference voice if not present
if [ ! -f "${DATA_DIR}/rocky_reference.wav" ]; then
    echo "Downloading Rocky reference voice..."
    wget -O "${DATA_DIR}/rocky_reference.wav" \
        "https://pedramamini.com/dropbox/rocky_training_audio_scrubbed.wav" \
        || echo "Warning: Could not download reference voice. Please provide your own."
    echo "Rocky voice downloaded ($(du -h ${DATA_DIR}/rocky_reference.wav | cut -f1))"
fi

# Copy configuration templates if needed
echo "Setting up configuration..."
if [ ! -f "${DATA_DIR}/config.yaml" ]; then
    cp "${APP_DIR}/config/config.yaml.template" "${DATA_DIR}/config.yaml"
    # Update paths in config
    sed -i "s|/home/rocky/|/home/${ROCKY_USER}/|g" "${DATA_DIR}/config.yaml"
    sed -i "s|wyoming_port: .*|wyoming_port: ${WYOMING_PORT}|" "${DATA_DIR}/config.yaml"
    sed -i "s|web_port: .*|web_port: ${WEB_PORT}|" "${DATA_DIR}/config.yaml"
fi

if [ ! -f "${DATA_DIR}/overrides.yaml" ]; then
    cp "${APP_DIR}/config/overrides.yaml.template" "${DATA_DIR}/overrides.yaml"
fi

chown -R "$ROCKY_USER:$ROCKY_USER" "${DATA_DIR}"

# Install systemd services
echo "Installing systemd services..."
cp "${APP_DIR}/systemd/wyoming-rocky.service" "/etc/systemd/system/"
cp "${APP_DIR}/systemd/wyoming-rocky-web.service" "/etc/systemd/system/"

# Update service files with correct paths
sed -i "s|/home/rocky/|/home/${ROCKY_USER}/|g" "/etc/systemd/system/wyoming-rocky.service"
sed -i "s|/home/rocky/|/home/${ROCKY_USER}/|g" "/etc/systemd/system/wyoming-rocky-web.service"

# Install helper scripts
echo "Installing helper scripts..."
for script in test-rocky-tts rocky-cache-stats rocky-clear-cache; do
    if [ -f "${APP_DIR}/scripts/${script}" ]; then
        cp "${APP_DIR}/scripts/${script}" "/usr/local/bin/"
        chmod +x "/usr/local/bin/${script}"
        # Update paths in scripts
        sed -i "s|/home/rocky/|/home/${ROCKY_USER}/|g" "/usr/local/bin/${script}"
    fi
done

# Reload systemd
systemctl daemon-reload

# Enable services
echo "Enabling services..."
systemctl enable "${SERVICE_NAME}"
systemctl enable "${SERVICE_NAME}-web"

# Start services
echo "Starting services..."
systemctl restart "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}-web"

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 15

# Run health checks
echo ""
echo "Running health checks..."
echo "------------------------"

if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "✓ Wyoming service is running"
else
    echo "✗ Wyoming service failed to start"
    echo "  Check logs: journalctl -u ${SERVICE_NAME} -n 50"
fi

if systemctl is-active --quiet "${SERVICE_NAME}-web"; then
    echo "✓ Web UI service is running"
else
    echo "✗ Web UI service failed to start"
    echo "  Check logs: journalctl -u ${SERVICE_NAME}-web -n 50"
fi

# Check if ports are listening
if ss -lntp 2>/dev/null | grep -q ":${WYOMING_PORT}"; then
    echo "✓ Wyoming port ${WYOMING_PORT} is listening"
else
    echo "✗ Wyoming port ${WYOMING_PORT} is not listening"
fi

if ss -lntp 2>/dev/null | grep -q ":${WEB_PORT}"; then
    echo "✓ Web UI port ${WEB_PORT} is listening"
else
    echo "✗ Web UI port ${WEB_PORT} is not listening"
fi

# Get IP address
IP_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)

# Final instructions
echo ""
echo "=============================================="
echo "Installation Complete!"
echo "=============================================="
echo ""
echo "Wyoming TTS Server: http://${IP_ADDR}:${WYOMING_PORT}"
echo "Web UI: http://${IP_ADDR}:${WEB_PORT}"
echo ""
echo "To add to Home Assistant:"
echo "1. Go to Settings → Devices & Services"
echo "2. Click 'Add Integration'"
echo "3. Search for 'Wyoming Protocol'"
echo "4. Enter:"
echo "   - Host: ${IP_ADDR}"
echo "   - Port: ${WYOMING_PORT}"
echo ""
echo "The TTS entity will appear as 'tts.rocky_yourtts' or similar"
echo ""
echo "Service commands:"
echo "  systemctl status ${SERVICE_NAME}"
echo "  systemctl restart ${SERVICE_NAME}"
echo "  journalctl -u ${SERVICE_NAME} -f"
echo ""
echo "Test commands:"
echo "  test-rocky-tts 'Hello world'"
echo "  rocky-cache-stats"
echo "  rocky-clear-cache"
echo ""
echo "Web UI: http://${IP_ADDR}:${WEB_PORT}"
echo ""
echo "Documentation: ${GITHUB_REPO}"
echo "=============================================="