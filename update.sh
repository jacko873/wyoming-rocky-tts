#!/bin/sh

set -e

# Quick updater for Wyoming Rocky TTS:
# pulls the latest version, updates dependencies, restarts services.
#
# Usage: sudo ./update.sh [--clear-cache]
# (POSIX sh compatible — works with sh, dash, or bash)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status()  { printf "${GREEN}✓${NC} %s\n" "$1"; }
print_warning() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
print_error()   { printf "${RED}✗${NC} %s\n" "$1"; }
print_info()    { printf "${BLUE}ℹ${NC} %s\n" "$1"; }

# Must match install.sh
ROCKY_USER="rocky"
APP_DIR="/home/${ROCKY_USER}/wyoming-rocky-tts"
DATA_DIR="/home/${ROCKY_USER}/.rocky_tts"
CACHE_DIR="${DATA_DIR}/cache"
VENV_DIR="${APP_DIR}/venv"
WYOMING_PORT="${ROCKY_WYOMING_PORT:-10202}"
SERVICES="wyoming-rocky wyoming-rocky-web"

CLEAR_CACHE=false
if [ "$1" = "--clear-cache" ]; then
    CLEAR_CACHE=true
fi

if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root (use sudo)"
    echo "Usage: sudo ./update.sh [--clear-cache]"
    exit 1
fi

if [ ! -d "$APP_DIR/.git" ]; then
    print_error "No git repository at $APP_DIR — run install.sh first"
    exit 1
fi

# Pull latest version
print_info "Pulling latest version..."
OLD_REV=$(su - "$ROCKY_USER" -c "git -C '$APP_DIR' rev-parse --short HEAD")
if ! su - "$ROCKY_USER" -c "git -C '$APP_DIR' pull --ff-only"; then
    print_error "git pull failed (local changes in the way?)"
    print_info "Inspect with: su - $ROCKY_USER -c 'git -C $APP_DIR status'"
    exit 1
fi
NEW_REV=$(su - "$ROCKY_USER" -c "git -C '$APP_DIR' rev-parse --short HEAD")

if [ "$OLD_REV" = "$NEW_REV" ]; then
    print_status "Already up to date ($NEW_REV) — restarting services anyway"
else
    print_status "Updated $OLD_REV -> $NEW_REV"
    su - "$ROCKY_USER" -c "git -C '$APP_DIR' log --oneline $OLD_REV..$NEW_REV" | sed 's/^/    /'
fi

# Update Python dependencies (fast no-op when nothing changed)
print_info "Updating Python dependencies..."
if ! su - "$ROCKY_USER" -c "'$VENV_DIR/bin/pip' install -q -r '$APP_DIR/requirements.txt'"; then
    print_warning "pip install failed — continuing with existing packages"
fi

# Update systemd units if the repo versions changed
UNITS_CHANGED=false
for unit in "$APP_DIR"/systemd/*.service; do
    [ -f "$unit" ] || continue
    name=$(basename "$unit")
    if ! cmp -s "$unit" "/etc/systemd/system/$name"; then
        cp "$unit" "/etc/systemd/system/$name"
        UNITS_CHANGED=true
        print_status "Updated systemd unit: $name"
    fi
done
if [ "$UNITS_CHANGED" = true ]; then
    systemctl daemon-reload
fi

# Optionally clear the audio cache
if [ "$CLEAR_CACHE" = true ]; then
    print_info "Clearing audio cache..."
    rm -f "$CACHE_DIR"/*.wav "$CACHE_DIR"/cache.db
    print_status "Cache cleared"
fi

# Restart services
for svc in $SERVICES; do
    if systemctl cat "${svc}.service" >/dev/null 2>&1; then
        print_info "Restarting ${svc}..."
        systemctl restart "$svc"
    else
        print_warning "Service ${svc} not installed, skipping"
    fi
done

# Wait for the Wyoming server to come up (model load can take minutes on CPU)
print_info "Waiting for Wyoming server on port ${WYOMING_PORT} (model loading can take a few minutes)..."
WAITED=0
TIMEOUT=600
while ! ss -tln | grep -q ":${WYOMING_PORT} "; do
    if ! systemctl is-active --quiet wyoming-rocky; then
        print_error "wyoming-rocky service died during startup. Last log lines:"
        journalctl -u wyoming-rocky -n 25 --no-pager
        exit 1
    fi
    if [ "$WAITED" -ge "$TIMEOUT" ]; then
        print_error "Timed out after ${TIMEOUT}s waiting for port ${WYOMING_PORT}"
        print_info "Check logs with: journalctl -u wyoming-rocky -f"
        exit 1
    fi
    sleep 5
    WAITED=$((WAITED + 5))
    printf "."
done
echo ""
print_status "Wyoming server is listening on port ${WYOMING_PORT}"

# Protocol smoke test if available
if [ -f "$APP_DIR/test_wyoming_connection.py" ]; then
    print_info "Running Wyoming protocol check..."
    if su - "$ROCKY_USER" -c "cd '$APP_DIR' && '$VENV_DIR/bin/python' test_wyoming_connection.py localhost $WYOMING_PORT"; then
        print_status "Protocol check passed"
    else
        print_error "Protocol check failed — see output above"
        exit 1
    fi
fi

echo ""
print_status "Update complete ($NEW_REV)"
