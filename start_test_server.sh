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

echo ""
echo "======================================"
echo "Setup Instructions:"
echo "======================================"
echo ""
echo "1. Create Python virtual environment:"
echo "   python3 -m venv venv"
echo "   source venv/bin/activate"
echo ""
echo "2. Install dependencies:"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Start the Wyoming TTS server:"
echo "   python -m src.wyoming_server --config config/test_config.yaml"
echo ""
echo "4. In another terminal, start the Web UI:"
echo "   python -m src.web_ui --port 8088"
echo ""
echo "5. Open browser to test:"
echo "   http://localhost:8088"
echo ""
echo "======================================"
echo "Quick Test (without full TTS model):"
echo "======================================"
echo ""
echo "For quick testing of text transformations only:"
echo "   python test_simple.py"
echo ""
echo "======================================"