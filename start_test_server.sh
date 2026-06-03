#!/bin/bash

echo "======================================"
echo "Wyoming Rocky TTS - Local Test Setup"
echo "======================================"
echo ""

# Check Python version
if ! python3 --version | grep -qE "3\.(9|10|11|12)"; then
    echo "❌ Python 3.9+ required"
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data
mkdir -p cache
mkdir -p config

# Check if Rocky voice exists
if [ ! -f "data/rocky_reference.wav" ]; then
    echo "❌ Rocky reference voice not found!"
    echo "   Downloading now..."
    cd data
    wget -O rocky_reference.wav "https://pedramamini.com/dropbox/rocky_training_audio_scrubbed.wav"
    cd ..
fi

echo "✓ Rocky voice found: data/rocky_reference.wav"

# Create local config if it doesn't exist
if [ ! -f "config/test_config.yaml" ]; then
    echo "Creating test configuration..."
    cat > config/test_config.yaml << 'EOF'
# Test Configuration for Local Development
wyoming_host: 0.0.0.0
wyoming_port: 10202
web_host: 0.0.0.0
web_port: 8088

# Paths (relative to project root)
speaker_wav: data/rocky_reference.wav
data_dir: data
cache_dir: cache

# TTS Settings
model_name: tts_models/multilingual/multi-dataset/your_tts
cache_enabled: true
warmup_text: System ready
style_mode: rules

# Audio Settings
audio_rate: 22050
ffmpeg_filters: highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16:TP=-1.5:LRA=11

# Processing
max_text_length: 500
normalize_numbers: true
normalize_units: true
log_level: INFO
EOF
    echo "✓ Test configuration created"
fi

# Create overrides file if it doesn't exist
if [ ! -f "data/overrides.yaml" ]; then
    cp config/overrides.yaml.template data/overrides.yaml 2>/dev/null || \
    cat > data/overrides.yaml << 'EOF'
# Pronunciation Overrides
Aj: Ajay
HA: Home Assistant
HACS: H A C S
EOF
    echo "✓ Overrides file created"
fi

# Set up config for Web UI (it expects config in ~/.rocky_tts/)
echo "Setting up Web UI configuration..."
mkdir -p "$HOME/.rocky_tts"
cp config/test_config.yaml "$HOME/.rocky_tts/config.yaml"
echo "✓ Web UI configuration set up"

# Check if we can create virtual environment
echo "Checking Python virtual environment..."
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating Python virtual environment..."
    if ! python3 -m venv venv 2>/dev/null; then
        echo "❌ Virtual environment creation failed."
        echo "   This usually means python3-venv is not installed."
        echo "   Trying to install system packages..."
        
        if command -v apt >/dev/null 2>&1; then
            echo "   Installing with apt..."
            apt update && apt install -y python3-venv python3-pip || {
                echo "❌ Failed to install packages. Try running as root or install manually:"
                echo "   sudo apt install python3-venv python3-pip"
                exit 1
            }
        else
            echo "❌ Please install python3-venv package manually"
            exit 1
        fi
        
        # Try creating venv again
        python3 -m venv venv || {
            echo "❌ Still cannot create virtual environment"
            exit 1
        }
    fi
    echo "✓ Virtual environment created"
fi

# Try to activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "⚠️  No virtual environment, using system Python"
fi

# Install dependencies with proper error handling
echo "Installing Python dependencies..."
BASIC_PACKAGES="pyyaml num2words fastapi uvicorn python-multipart"
TTS_PACKAGES="torch torchaudio wyoming TTS"

echo "Installing basic packages..."
if command -v pip >/dev/null 2>&1; then
    pip install -q $BASIC_PACKAGES 2>/dev/null || {
        echo "⚠️  Pip install failed, trying with --break-system-packages"
        pip install -q $BASIC_PACKAGES --break-system-packages || {
            echo "❌ Failed to install basic packages"
            echo "   Try manually: pip install $BASIC_PACKAGES"
        }
    }
else
    echo "❌ pip not found, trying to install..."
    if command -v apt >/dev/null 2>&1; then
        apt install -y python3-pip
        pip install -q $BASIC_PACKAGES --break-system-packages
    else
        echo "❌ Cannot install pip automatically"
        exit 1
    fi
fi

echo "✓ Basic dependencies installed"

echo "Installing TTS packages (this may take a while)..."
if pip install -q $TTS_PACKAGES 2>/dev/null || pip install -q $TTS_PACKAGES --break-system-packages 2>/dev/null; then
    echo "✓ TTS dependencies installed"
    TTS_AVAILABLE=true
else
    echo "⚠️  TTS dependencies failed to install - Wyoming TTS will not work"
    echo "   This is normal in resource-constrained environments"
    echo "   The Web UI will still work for text transformations"
    TTS_AVAILABLE=false
fi

echo ""
echo "======================================"
echo "Starting Rocky TTS Test Servers"
echo "======================================"
echo ""

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    
    # Kill specific PIDs if they exist
    if [ -n "$WEB_PID" ]; then
        kill $WEB_PID 2>/dev/null && echo "✓ Web UI stopped"
    fi
    
    if [ -n "$WYOMING_PID" ]; then
        kill $WYOMING_PID 2>/dev/null && echo "✓ Wyoming server stopped"
    fi
    
    # Also kill any remaining background jobs
    jobs -p | xargs -r kill 2>/dev/null
    
    wait 2>/dev/null
    echo "✓ All servers stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Try starting Wyoming TTS server (only if TTS is available)
if [ "$TTS_AVAILABLE" = true ]; then
    echo "🚀 Starting Wyoming TTS server on port 10202..."
    if [ -f "venv/bin/activate" ]; then
        # Use virtual environment if available
        source venv/bin/activate
        python3 -m src.wyoming_server --config config/test_config.yaml &>/dev/null &
    else
        # Fallback to system python
        python3 -m src.wyoming_server --config config/test_config.yaml &>/dev/null &
    fi
    WYOMING_PID=$!
    
    # Wait longer for TTS model to load
    echo "   Loading YourTTS model (this may take 10-15 seconds)..."
    sleep 10

    # Check if Wyoming server is still running
    if kill -0 $WYOMING_PID 2>/dev/null; then
        echo "✓ Wyoming TTS server started (PID: $WYOMING_PID)"
    else
        echo "⚠️  Wyoming TTS server failed to start"
        WYOMING_PID=""
    fi
else
    echo "⚠️  Skipping Wyoming TTS server (TTS dependencies not available)"
    WYOMING_PID=""
fi

# Wait a moment for Wyoming server to start
sleep 2

# Try starting Web UI
echo "🌐 Starting Web UI on port 8088..."
python3 -m src.web_ui --port 8088 --host 127.0.0.1 &>/dev/null &
WEB_PID=$!
sleep 1

# Check if Web UI is still running
if kill -0 $WEB_PID 2>/dev/null; then
    echo "✓ Web UI started (PID: $WEB_PID)"
else
    echo "❌ Web UI failed to start"
    echo "   Check that fastapi and uvicorn are installed"
    if [ -n "$WYOMING_PID" ]; then
        kill $WYOMING_PID 2>/dev/null
    fi
    exit 1
fi

# Wait a moment for Web UI to start
sleep 2

# Get local IP for remote access (with fallback)
if command -v ip >/dev/null 2>&1; then
    LOCAL_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' 2>/dev/null || echo "localhost")
elif command -v hostname >/dev/null 2>&1; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
else
    LOCAL_IP="localhost"
fi

echo ""
echo "======================================"
echo "Server Status:"
echo "======================================"

# Check if web UI is actually responding
if curl -s http://localhost:8088 >/dev/null 2>&1; then
    echo "✅ Web UI: Running and responding"
    WEB_RUNNING=true
else
    echo "❌ Web UI: Not responding"
    WEB_RUNNING=false
fi

# Check if Wyoming server is responding (TCP connection test with retry)
if [ "$TTS_AVAILABLE" = true ]; then
    echo "   Testing Wyoming TTS connection..."
    WYOMING_RESPONDING=false
    for attempt in 1 2 3; do
        if timeout 3 bash -c "</dev/tcp/localhost/10202" >/dev/null 2>&1; then
            WYOMING_RESPONDING=true
            break
        fi
        if [ $attempt -lt 3 ]; then
            echo "   Attempt $attempt failed, retrying..."
            sleep 2
        fi
    done
    
    if [ "$WYOMING_RESPONDING" = true ]; then
        echo "✅ Wyoming TTS: Running and responding"
        WYOMING_RUNNING=true
    else
        echo "⚠️  Wyoming TTS: Not responding (check logs above for errors)"
        WYOMING_RUNNING=false
    fi
else
    echo "⚠️  Wyoming TTS: Disabled (TTS dependencies not installed)"
    WYOMING_RUNNING=false
fi

echo ""
echo "======================================"
echo "Access URLs:"
echo "======================================"
echo ""

if [ "$WEB_RUNNING" = true ]; then
    echo "🌐 Web Interface (WORKING):"
    echo "   Local:  http://localhost:8088"
    echo "   Remote: http://$LOCAL_IP:8088"
else
    echo "❌ Web Interface: Failed to start"
fi

echo ""

if [ "$WYOMING_RUNNING" = true ]; then
    echo "🔧 Wyoming TTS (WORKING):"
    echo "   Local:  http://localhost:10202"
    echo "   Remote: http://$LOCAL_IP:10202"
else
    echo "⚠️  Wyoming TTS: Not available (requires full installation)"
fi

echo ""
echo "======================================"
echo "Quick Tests:"
echo "======================================"
echo ""
echo "Text transformation test:"
echo "   python3 test_simple.py"
echo ""

# Test OpenAI availability
if [ -f ".env" ]; then
    # Load .env file
    export $(grep -v '^#' .env | xargs)
    if [ -n "$OPENAI_API_KEY" ]; then
        echo "🤖 OpenAI Mode: Available"
        echo "   Test: python3 test_openai_simple.py"
    else
        echo "⚠️  OpenAI Mode: No API key in .env"
    fi
else
    echo "⚠️  OpenAI Mode: No .env file found"
fi
echo ""
echo "======================================"
echo ""
echo "🎯 Open http://localhost:8088 to test Rocky TTS!"
echo "📝 Use the web interface to test text transformations and audio generation"
echo ""
echo "Press Ctrl+C to stop all servers..."
echo ""

# Wait for user to stop with Ctrl+C
wait