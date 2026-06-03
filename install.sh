#!/bin/bash

set -e  # Exit on any error

echo "=============================================="
echo "Wyoming Rocky TTS Installer v2.1"
echo "for Debian 12 & compatible Linux distributions"
echo "=============================================="
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
    echo "Usage: sudo ./install.sh"
    exit 1
fi

# Check OS compatibility
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" = "debian" ] && [ "$VERSION_ID" = "12" ]; then
        print_status "Debian 12 detected - optimal compatibility"
    elif [ "$ID" = "ubuntu" ] && [ "${VERSION_ID%%.*}" -ge "22" ]; then
        print_status "Ubuntu $VERSION_ID detected - good compatibility"
    else
        print_warning "OS: $PRETTY_NAME"
        print_warning "This installer is optimized for Debian 12. Some features may not work correctly."
        read -p "Continue installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    print_error "Cannot determine OS version. Debian 12 required."
    exit 1
fi

# Configuration with environment variable overrides
GITHUB_REPO="${GITHUB_REPO:-https://github.com/jacko873/wyoming-rocky-tts.git}"
ROCKY_USER="rocky"
APP_DIR="/home/${ROCKY_USER}/wyoming-rocky-tts"
DATA_DIR="/home/${ROCKY_USER}/.rocky_tts"
CACHE_DIR="${DATA_DIR}/cache"  # Store cache in user directory for proper permissions
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="wyoming-rocky"
WYOMING_PORT="${ROCKY_WYOMING_PORT:-10202}"
WEB_PORT="${ROCKY_WEB_PORT:-8088}"
INSTALL_OPENAI="${INSTALL_OPENAI:-true}"  # Install OpenAI by default

echo ""
print_info "Installation Configuration:"
echo "  Repository: ${GITHUB_REPO}"
echo "  Install directory: ${APP_DIR}"
echo "  Data directory: ${DATA_DIR}"
echo "  Cache directory: ${CACHE_DIR}"
echo "  Wyoming port: ${WYOMING_PORT}"
echo "  Web UI port: ${WEB_PORT}"
echo "  OpenAI support: ${INSTALL_OPENAI}"
echo ""

# Memory check
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_MEM" -lt 3500 ]; then
    print_warning "Low memory detected: ${TOTAL_MEM}MB (recommended: 4GB+)"
    print_warning "TTS model loading may fail or be very slow"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Disk space check
AVAILABLE=$(df / | tail -1 | awk '{print $4}')
if [ "$AVAILABLE" -lt 3000000 ]; then  # 3GB in KB
    print_error "Insufficient disk space. At least 3GB free required."
    exit 1
fi

# Update system packages
echo ""
print_info "Updating system packages..."
apt update -qq
if ! apt upgrade -y; then
    print_error "System update failed. Please fix package issues and retry."
    exit 1
fi

# Install system dependencies with error checking
echo ""
print_info "Installing system dependencies..."
DEPS=(
    "python3.11" "python3.11-venv" "python3.11-dev"
    "python3-pip" "python3-setuptools" "python3-wheel"
    "git" "curl" "wget" "unzip"
    "ffmpeg" "sox" "libsox-dev" "libsox-fmt-all"
    "build-essential" "cmake" "pkg-config"
    "libssl-dev" "libffi-dev" "libxml2-dev" "libxslt1-dev"
    "zlib1g-dev" "libjpeg-dev" "libpng-dev"
    "libopenblas-dev" "liblapack-dev" "gfortran"
    "libasound2-dev" "portaudio19-dev" "libportaudio2"
    "sqlite3" "libsqlite3-dev"
    "espeak-ng" "espeak-ng-data"
)

# Install dependencies in batches to avoid overwhelming the system
for dep in "${DEPS[@]}"; do
    if ! dpkg -l "$dep" >/dev/null 2>&1; then
        if ! apt install -y "$dep"; then
            print_warning "Failed to install $dep, continuing..."
        fi
    fi
done

# Verify critical dependencies
print_info "Verifying critical dependencies..."
CRITICAL=("python3.11" "git" "ffmpeg" "sox")
for dep in "${CRITICAL[@]}"; do
    if ! command -v "$dep" >/dev/null 2>&1; then
        print_error "Critical dependency '$dep' not found. Installation cannot continue."
        exit 1
    fi
done
print_status "All critical dependencies verified"

# Create Rocky user account
echo ""
print_info "Creating Rocky user account..."
if ! id -u "$ROCKY_USER" >/dev/null 2>&1; then
    if useradd -m -s /bin/bash "$ROCKY_USER"; then
        print_status "User '$ROCKY_USER' created successfully"
    else
        print_error "Failed to create user '$ROCKY_USER'"
        exit 1
    fi
else
    print_status "User '$ROCKY_USER' already exists"
fi

# Create directory structure with proper permissions
echo ""
print_info "Creating directory structure..."
mkdir -p "$DATA_DIR" "$CACHE_DIR"
if ! chown -R "$ROCKY_USER:$ROCKY_USER" "/home/$ROCKY_USER"; then
    print_error "Failed to set directory permissions"
    exit 1
fi
print_status "Directory structure created"

# Clone or update repository
echo ""
print_info "Setting up repository..."
if [ -d "$APP_DIR/.git" ]; then
    print_info "Repository exists, updating..."
    cd "$APP_DIR"
    if ! su - "$ROCKY_USER" -c "cd '$APP_DIR' && git pull"; then
        print_warning "Git pull failed, continuing with existing files..."
    fi
else
    print_info "Cloning repository..."
    if ! su - "$ROCKY_USER" -c "git clone '$GITHUB_REPO' '$APP_DIR'"; then
        print_error "Failed to clone repository"
        exit 1
    fi
fi

# Ensure proper ownership
chown -R "$ROCKY_USER:$ROCKY_USER" "$APP_DIR"
print_status "Repository setup complete"

# Create and setup Python virtual environment
echo ""
print_info "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    if ! su - "$ROCKY_USER" -c "python3.11 -m venv '$VENV_DIR'"; then
        print_error "Failed to create virtual environment"
        exit 1
    fi
    print_status "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Upgrade pip and setuptools in venv
if ! su - "$ROCKY_USER" -c "'$VENV_DIR/bin/pip' install --upgrade pip setuptools wheel"; then
    print_error "Failed to upgrade pip in virtual environment"
    exit 1
fi

# Install Python dependencies with retry logic
echo ""
print_info "Installing Python dependencies (this will take several minutes)..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if su - "$ROCKY_USER" -c "cd '$APP_DIR' && '$VENV_DIR/bin/pip' install -r requirements.txt"; then
        print_status "Python dependencies installed successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            print_warning "Dependency installation failed, retrying ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 5
        else
            print_error "Failed to install Python dependencies after $MAX_RETRIES attempts"
            print_error "Try running: sudo -u $ROCKY_USER '$VENV_DIR/bin/pip' install -r '$APP_DIR/requirements.txt'"
            exit 1
        fi
    fi
done

# Install OpenAI support if requested
if [ "$INSTALL_OPENAI" = "true" ]; then
    echo ""
    print_info "Installing OpenAI integration..."
    if ! su - "$ROCKY_USER" -c "'$VENV_DIR/bin/pip' install openai"; then
        print_warning "OpenAI installation failed - OpenAI features will not be available"
    else
        print_status "OpenAI integration installed"
    fi
fi

# Download Rocky reference voice
echo ""
print_info "Setting up Rocky reference voice..."
VOICE_FILE="${DATA_DIR}/rocky_reference.wav"
if [ ! -f "$VOICE_FILE" ]; then
    print_info "Downloading Rocky reference voice sample..."
    if wget -O "$VOICE_FILE" "https://pedramamini.com/dropbox/rocky_training_audio_scrubbed.wav" 2>/dev/null; then
        chown "$ROCKY_USER:$ROCKY_USER" "$VOICE_FILE"
        VOICE_SIZE=$(du -h "$VOICE_FILE" | cut -f1)
        print_status "Rocky voice downloaded successfully ($VOICE_SIZE)"
    else
        print_warning "Failed to download Rocky reference voice"
        print_warning "You can manually place a WAV file at: $VOICE_FILE"
    fi
else
    print_status "Rocky reference voice already exists"
fi

# Setup configuration files
echo ""
print_info "Configuring Rocky TTS..."

# Create main config if it doesn't exist
CONFIG_FILE="${DATA_DIR}/config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "${APP_DIR}/config/config.yaml" ]; then
        cp "${APP_DIR}/config/config.yaml" "$CONFIG_FILE"
    else
        # Create a basic config file
        cat > "$CONFIG_FILE" << EOF
# Wyoming Rocky TTS Configuration
wyoming_port: ${WYOMING_PORT}
wyoming_host: "0.0.0.0"
web_port: ${WEB_PORT}
web_host: "0.0.0.0"

# Rocky Style Settings
style_mode: rules  # Options: off, rules, openai

# Audio Settings
audio_rate: 22050
ffmpeg_filters: "highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16"

# Cache Settings
cache_enabled: true
cache_dir: "${CACHE_DIR}"
max_text_length: 500

# Model Settings
model_name: "tts_models/multilingual/multi-dataset/your_tts"
speaker_wav: "${VOICE_FILE}"
data_dir: "${DATA_DIR}"

# OpenAI Integration (Optional)
openai_api_key_env: "OPENAI_API_KEY"
openai_model: "gpt-4"
rocky_style_prompt: |
  You are Rocky, an alien from Project Hail Mary. Transform the text to match Rocky's speech patterns:
  - Use simple grammar, sometimes dropping articles (the, a, an)
  - Repeat words for emphasis (amaze amaze amaze, good good good)
  - End questions with "question?"
  - Use "no" instead of "don't" sometimes
  - Keep Rocky's helpful, curious personality
  - Don't add explanations, just transform the text

# Performance Settings
warmup_text: "System ready..."
EOF
    fi
    
    # Update config with correct paths
    sed -i "s|/home/rocky/|/home/${ROCKY_USER}/|g" "$CONFIG_FILE"
    sed -i "s|wyoming_port: .*|wyoming_port: ${WYOMING_PORT}|" "$CONFIG_FILE"
    sed -i "s|web_port: .*|web_port: ${WEB_PORT}|" "$CONFIG_FILE"
    print_status "Main configuration created"
else
    print_status "Configuration file already exists"
fi

# Create pronunciation overrides if they don't exist
OVERRIDES_FILE="${DATA_DIR}/overrides.yaml"
if [ ! -f "$OVERRIDES_FILE" ]; then
    cat > "$OVERRIDES_FILE" << 'EOF'
# Pronunciation Overrides
# Format: "original": "spoken as"
"AI": "A I"
"HA": "Home Assistant"
"WiFi": "Wife Eye"
"PM2.5": "P M two point five"
"°F": "degrees fahrenheit"
"°C": "degrees celsius"
"kWh": "kilowatt hours"
"IoT": "I O T"
"IPv4": "I P v four"
"IPv6": "I P v six"
"USB": "U S B"
"LED": "L E D"
"CPU": "C P U"
"RAM": "R A M"
"SSD": "S S D"
"URL": "U R L"
"API": "A P I"
"HTTP": "H T T P"
"HTTPS": "H T T P S"
EOF
    print_status "Pronunciation overrides created"
else
    print_status "Pronunciation overrides already exist"
fi

# Set proper ownership for all config files
chown -R "$ROCKY_USER:$ROCKY_USER" "$DATA_DIR"

# Install systemd service
echo ""
print_info "Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Wyoming Rocky TTS Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${ROCKY_USER}
Group=${ROCKY_USER}
WorkingDirectory=${APP_DIR}
Environment=PATH=${VENV_DIR}/bin:\$PATH
Environment=PYTHONPATH=${APP_DIR}
ExecStart=${VENV_DIR}/bin/python -m src.wyoming_server --config ${DATA_DIR}/config.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=${DATA_DIR} ${CACHE_DIR} ${APP_DIR}
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

[Install]
WantedBy=multi-user.target
EOF

# Install web UI service
WEB_SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}-web.service"
cat > "$WEB_SERVICE_FILE" << EOF
[Unit]
Description=Wyoming Rocky TTS Web UI
After=network.target ${SERVICE_NAME}.service
Wants=network-online.target

[Service]
Type=simple
User=${ROCKY_USER}
Group=${ROCKY_USER}
WorkingDirectory=${APP_DIR}
Environment=PATH=${VENV_DIR}/bin:\$PATH
Environment=PYTHONPATH=${APP_DIR}
ExecStart=${VENV_DIR}/bin/python -m src.web_ui --port ${WEB_PORT} --host 0.0.0.0
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=${DATA_DIR} ${CACHE_DIR} ${APP_DIR}
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictRealtime=yes

[Install]
WantedBy=multi-user.target
EOF

print_status "Systemd services created"

# Install helper scripts
echo ""
print_info "Installing helper scripts..."
SCRIPT_DIR="/usr/local/bin"

# Test script
cat > "${SCRIPT_DIR}/test-rocky-tts" << EOF
#!/bin/bash
# Rocky TTS Test Script
cd ${APP_DIR}
source venv/bin/activate
exec python3 -c "
import sys
sys.path.append('${APP_DIR}')
from src.config import Config
from src.rocky_styler import RockyStyler
from src.text_normalizer import TextNormalizer
from pathlib import Path

config = Config.load(Path('${DATA_DIR}/config.yaml'))
styler = RockyStyler(config.style_mode, config)
normalizer = TextNormalizer(Path('${DATA_DIR}/overrides.yaml'))

text = sys.argv[1] if len(sys.argv) > 1 else 'Hello Rocky'
styled = styler.apply_style(text)
normalized = normalizer.normalize(styled)

print(f'Original: {text}')
print(f'Rocky Style: {styled}')
print(f'Normalized: {normalized}')
" "\$@"
EOF

# Cache stats script
cat > "${SCRIPT_DIR}/rocky-cache-stats" << EOF
#!/bin/bash
cd ${APP_DIR}
source venv/bin/activate
exec python3 -c "
import sys
sys.path.append('${APP_DIR}')
from src.cache_manager import CacheManager
from pathlib import Path

cache = CacheManager(Path('${CACHE_DIR}'))
stats = cache.get_stats()
print(f\"Cache Statistics:\")
print(f\"  Total entries: {stats['total_entries']}\")
print(f\"  Total hits: {stats['total_hits']}\")
print(f\"  Cache size: {stats.get('cache_size_mb', 0):.1f} MB\")
print(f\"  Avg synthesis time: {stats.get('avg_synthesis_ms', 0):.0f} ms\")
if stats['total_entries'] > 0:
    hit_rate = (stats['total_hits'] / stats['total_entries']) * 100
    print(f\"  Hit rate: {hit_rate:.1f}%\")
"
EOF

# Cache clear script
cat > "${SCRIPT_DIR}/rocky-clear-cache" << EOF
#!/bin/bash
cd ${APP_DIR}
source venv/bin/activate
echo "Clearing Rocky TTS cache..."
python3 -c "
import sys
sys.path.append('${APP_DIR}')
from src.cache_manager import CacheManager
from pathlib import Path

cache = CacheManager(Path('${CACHE_DIR}'))
cache.clear()
print('Cache cleared successfully')
"
EOF

# Make scripts executable
chmod +x "${SCRIPT_DIR}/test-rocky-tts"
chmod +x "${SCRIPT_DIR}/rocky-cache-stats"
chmod +x "${SCRIPT_DIR}/rocky-clear-cache"
print_status "Helper scripts installed"

# Reload systemd and enable services
echo ""
print_info "Configuring services..."
systemctl daemon-reload

if systemctl enable "${SERVICE_NAME}"; then
    print_status "Wyoming TTS service enabled"
else
    print_error "Failed to enable Wyoming TTS service"
fi

if systemctl enable "${SERVICE_NAME}-web"; then
    print_status "Web UI service enabled"
else
    print_error "Failed to enable Web UI service"
fi

# Start services with error handling
echo ""
print_info "Starting services..."
if systemctl start "${SERVICE_NAME}"; then
    print_status "Wyoming TTS service started"
else
    print_error "Failed to start Wyoming TTS service"
    print_info "Check logs: journalctl -u ${SERVICE_NAME} -n 50"
fi

sleep 2  # Brief pause between service starts

if systemctl start "${SERVICE_NAME}-web"; then
    print_status "Web UI service started"
else
    print_error "Failed to start Web UI service"
    print_info "Check logs: journalctl -u ${SERVICE_NAME}-web -n 50"
fi

# Wait for services to initialize
echo ""
print_info "Waiting for services to initialize (this may take up to 60 seconds)..."
WAIT_TIME=0
MAX_WAIT=60

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if systemctl is-active --quiet "${SERVICE_NAME}" && systemctl is-active --quiet "${SERVICE_NAME}-web"; then
        break
    fi
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
    echo -n "."
done
echo ""

# Comprehensive health checks
echo ""
print_info "Running health checks..."
echo "=================================="

# Service status
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    print_status "Wyoming TTS service is active"
else
    print_error "Wyoming TTS service is not active"
    systemctl status "${SERVICE_NAME}" --no-pager -l
fi

if systemctl is-active --quiet "${SERVICE_NAME}-web"; then
    print_status "Web UI service is active"
else
    print_error "Web UI service is not active"
    systemctl status "${SERVICE_NAME}-web" --no-pager -l
fi

# Port availability
if command -v ss >/dev/null && ss -lntp 2>/dev/null | grep -q ":${WYOMING_PORT}"; then
    print_status "Wyoming port ${WYOMING_PORT} is listening"
else
    print_warning "Wyoming port ${WYOMING_PORT} may not be listening yet"
fi

if command -v ss >/dev/null && ss -lntp 2>/dev/null | grep -q ":${WEB_PORT}"; then
    print_status "Web UI port ${WEB_PORT} is listening"
else
    print_warning "Web UI port ${WEB_PORT} may not be listening yet"
fi

# File checks
if [ -f "$VOICE_FILE" ]; then
    print_status "Rocky reference voice file exists"
else
    print_error "Rocky reference voice file missing: $VOICE_FILE"
fi

if [ -f "$CONFIG_FILE" ]; then
    print_status "Configuration file exists"
else
    print_error "Configuration file missing: $CONFIG_FILE"
fi

# Test basic functionality
echo ""
print_info "Testing basic functionality..."
if su - "$ROCKY_USER" -c "timeout 30 test-rocky-tts 'Installation test' >/dev/null 2>&1"; then
    print_status "Basic text processing test passed"
else
    print_warning "Basic text processing test failed (this may be normal during model loading)"
fi

# Get network information
IP_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
if [ -z "$IP_ADDR" ]; then
    IP_ADDR="<your-server-ip>"
fi

# Create OpenAI setup instructions
OPENAI_INSTRUCTIONS=""
if [ "$INSTALL_OPENAI" = "true" ]; then
    OPENAI_INSTRUCTIONS="
${GREEN}OpenAI Integration Setup (Optional):${NC}
1. Get an API key from: https://platform.openai.com/api-keys
2. Create .env file: sudo -u $ROCKY_USER nano $APP_DIR/.env
3. Add: OPENAI_API_KEY=sk-your-key-here
4. Update config.yaml: style_mode: openai
5. Restart: sudo systemctl restart $SERVICE_NAME
"
fi

# Final installation summary
echo ""
echo "=============================================="
print_status "Rocky TTS Installation Complete!"
echo "=============================================="
echo ""
echo -e "${BLUE}Service Endpoints:${NC}"
echo "  Wyoming TTS:   http://${IP_ADDR}:${WYOMING_PORT}"
echo "  Web UI:        http://${IP_ADDR}:${WEB_PORT}"
echo ""
echo -e "${BLUE}Home Assistant Integration:${NC}"
echo "1. Go to Settings → Devices & Services"
echo "2. Click 'Add Integration'"
echo "3. Search for 'Wyoming Protocol'"
echo "4. Configure:"
echo "   - Host: ${IP_ADDR}"
echo "   - Port: ${WYOMING_PORT}"
echo ""
echo -e "${BLUE}Testing Commands:${NC}"
echo "  test-rocky-tts 'Hello world'"
echo "  test-rocky-tts 'The lights are on' --style rules"
echo "  rocky-cache-stats"
echo "  rocky-clear-cache"
echo ""
echo -e "${BLUE}Service Management:${NC}"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  sudo systemctl restart ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
echo ""
echo -e "${BLUE}Configuration Files:${NC}"
echo "  Main config:     ${CONFIG_FILE}"
echo "  Pronunciations:  ${OVERRIDES_FILE}"
echo "  Cache location:  ${CACHE_DIR}"
echo ""
echo -e "$OPENAI_INSTRUCTIONS"
echo -e "${BLUE}Documentation:${NC}"
echo "  ${GITHUB_REPO}"
echo ""
echo -e "${GREEN}Rocky says: \"Installation good good good! Ready to help Home Assistant!\"${NC} 🗿"
echo "=============================================="