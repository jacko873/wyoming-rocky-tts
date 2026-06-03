# Wyoming Rocky TTS

A Wyoming-protocol compatible TTS server for Home Assistant that generates speech using Coqui YourTTS with Rocky's alien helper voice from Project Hail Mary.

## Features

- **🎤 Wyoming Protocol Compatible**: Seamless Home Assistant integration
- **🗿 Rocky-Style Personality**: Fun alien helper personality with distinctive speech patterns
- **🔧 Advanced Text Normalization**: Handles numbers, temperatures, times, units, and more
- **📝 Pronunciation Overrides**: Customize how specific words and phrases are spoken
- **⚡ Smart Caching**: High-performance caching for frequently used phrases
- **🌐 Web Control Panel**: Complete management interface with testing tools
- **🤖 OpenAI Integration**: AI-powered creative text styling (optional)
- **🎵 Audio Processing**: FFmpeg integration for optimized audio output
- **📊 Performance Monitoring**: Real-time cache statistics and performance metrics

## Quick Install

First, check your system compatibility:
```bash
wget https://raw.githubusercontent.com/jacko873/wyoming-rocky-tts/main/check_system.sh
chmod +x check_system.sh
sudo ./check_system.sh
```

If all checks pass, run the installer:
```bash
curl -sSL https://raw.githubusercontent.com/jacko873/wyoming-rocky-tts/main/install.sh | sudo bash
```

Or download and run manually:
```bash
wget https://raw.githubusercontent.com/jacko873/wyoming-rocky-tts/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

## Requirements

- **OS**: Debian 12 or compatible Linux distribution
- **Memory**: At least 4GB RAM (for YourTTS model)
- **Storage**: 3GB+ free disk space
- **Network**: Port 10202 (Wyoming) and 8088 (Web UI) available
- **Python**: 3.11+ (automatically installed)
- **Dependencies**: FFmpeg, system audio libraries (auto-installed)

## Manual Installation

### 1. Clone Repository
```bash
git clone https://github.com/jacko873/wyoming-rocky-tts.git
cd wyoming-rocky-tts
```

### 2. Run Installer
```bash
sudo ./install.sh
```

The installer automatically:
- ✅ Installs system dependencies (Python 3.11, FFmpeg, audio libraries)
- ✅ Creates dedicated `rocky` user account
- ✅ Sets up Python virtual environment
- ✅ Installs all Python packages with dependency resolution
- ✅ Downloads Rocky reference voice sample
- ✅ Configures systemd services with proper permissions
- ✅ Starts and enables services
- ✅ Performs health checks

## Home Assistant Integration

After installation, add the Wyoming integration:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Wyoming Protocol** 
4. Configure:
   - **Host**: Your server's IP address
   - **Port**: `10202`
   - **Name**: Rocky TTS (optional)

The TTS entity will appear as `tts.rocky_yourtts`.

### Usage in Home Assistant
```yaml
# In automations or scripts
service: tts.speak
data:
  entity_id: tts.rocky_yourtts
  message: "The lights have been turned on successfully"

# The output will be Rocky-style: "Lights on. Good good good!"
```

## Configuration

### Main Configuration File
Edit `/home/rocky/.rocky_tts/config.yaml`:

```yaml
# Wyoming Server Settings
wyoming_port: 10202
wyoming_host: "0.0.0.0"

# Web UI Settings  
web_port: 8088
web_host: "0.0.0.0"

# Rocky Style Settings
style_mode: rules  # Options: off, rules, openai

# Audio Processing
audio_rate: 22050
ffmpeg_filters: highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16

# Performance Settings
cache_enabled: true
max_text_length: 500

# Model Configuration
model_name: "tts_models/multilingual/multi-dataset/your_tts"
speaker_wav: "/home/rocky/.rocky_tts/rocky_reference.wav"

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
```

### OpenAI Integration Setup

For AI-powered creative text styling:

1. **Get OpenAI API Key**: Visit [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Create .env file**:
```bash
sudo -u rocky nano /home/rocky/wyoming-rocky-tts/.env
```

Add your API key:
```bash
OPENAI_API_KEY=sk-your-key-here
```

3. **Update config.yaml**:
```yaml
style_mode: openai  # Enable OpenAI mode
```

4. **Restart service**:
```bash
sudo systemctl restart wyoming-rocky
```

### Pronunciation Overrides

Edit `/home/rocky/.rocky_tts/overrides.yaml`:

```yaml
# Custom pronunciations (original: spoken_as)
"AI": "A I"
"HA": "Home Assistant" 
"WiFi": "Wife Eye"
"PM2.5": "P M two point five"
"°F": "degrees fahrenheit"
"°C": "degrees celsius"
"kWh": "kilowatt hours"
"IoT": "I O T"
```

## Web Control Panel

Access the management interface at: `http://your-server:8088`

### Features:
- **📊 Service Status**: Real-time monitoring of Wyoming TTS server
- **🧪 Text Testing**: Try different style modes with live preview
- **📈 Cache Statistics**: View performance metrics and hit rates  
- **🎵 Audio Generation**: Test TTS with immediate playback
- **📝 Override Management**: Add/edit pronunciation overrides
- **⚙️ Configuration**: View and download current settings
- **🗑️ Cache Control**: Clear cache entries and manage storage

### Style Modes Available:
1. **Off**: No Rocky styling, direct text-to-speech
2. **Rules-based**: Pattern-based Rocky transformations
3. **🤖 OpenAI Mode**: AI-generated creative Rocky variations

## Rocky Style Examples

### Rules-Based Mode
```
Input:  "I don't understand what you mean"
Output: "I no understand what mean, question?"

Input:  "The lights have been turned on successfully"  
Output: "Lights on. Good good good"

Input:  "That's absolutely amazing!"
Output: "That amaze amaze amaze!"

Input:  "Unable to connect to the device"
Output: "Can no connect device"

Input:  "Task completed successfully"
Output: "Task done. Good good good"
```

### OpenAI Mode
```
Input:  "The temperature is 72 degrees"
Output: "Temperature seventy two seventy two, good warm!"

Input:  "All systems are operational"  
Output: "All system work work work, everything good!"

Input:  "Please wait while I process this"
Output: "Wait wait, I think think think..."
```

### Pattern Features
- **Simplified Grammar**: Drops articles (the, a, an)
- **Emphasis Repetition**: Important words repeated 2-3 times
- **Question Format**: Ends with "question?"
- **Positive Reinforcement**: "good good good" for successful actions
- **Rocky Personality**: Helpful, curious, direct communication style

## Text Normalization

Automatically processes:

| Input | Normalized Output |
|-------|-------------------|
| `72°F` | seventy two degrees fahrenheit |
| `3:45 PM` | three forty five P M |
| `$24.99` | twenty four dollars ninety nine cents |
| `30%` | thirty percent |
| `10 mph` | ten miles per hour |
| `3.14159` | three point one four one five nine |
| `WiFi 6E` | Wife Eye six E |
| `IPv4` | I P v four |

## Commands & Scripts

### Testing TTS
```bash
# Basic test
test-rocky-tts "Hello world"

# With specific style
test-rocky-tts "The temperature is 72°F" --style rules
test-rocky-tts "System ready" --style openai
test-rocky-tts "Direct output" --style off

# Save to file
test-rocky-tts "Test message" --output /tmp/test.wav
```

### Cache Management
```bash
# View cache statistics
rocky-cache-stats

# Clear all cached audio
rocky-clear-cache

# Monitor cache in real-time
watch -n 5 rocky-cache-stats
```

### Service Management
```bash
# Check status
sudo systemctl status wyoming-rocky

# View logs
sudo journalctl -u wyoming-rocky -f

# Restart service
sudo systemctl restart wyoming-rocky

# Enable auto-start
sudo systemctl enable wyoming-rocky
```

## API Documentation

### Wyoming Protocol
- **Port**: 10202
- **Protocol**: Wyoming TTS v1.0
- **Voice**: `rocky_yourtts`

### Web UI REST API

#### Status Endpoints
```http
GET /api/status                    # Service status
GET /api/cache/stats              # Cache statistics
```

#### Text Processing
```http
POST /api/test
Content-Type: multipart/form-data

text=Hello world&style_mode=openai

Response:
{
  "original": "Hello world",
  "styled": "Hello hello hello world",
  "normalized": "Hello hello hello world", 
  "cache_key": "abc123...",
  "mode": "openai"
}
```

#### Audio Synthesis
```http
POST /api/synthesize
Content-Type: application/json

{
  "text": "Hello world",
  "style_mode": "rules",
  "voice_speed": "150"
}

Response: audio/wav file
```

#### Override Management
```http
GET /api/overrides               # List all overrides
POST /api/overrides              # Add override
DELETE /api/overrides/{key}      # Delete override
```

#### Cache Operations
```http
POST /api/cache/clear           # Clear all cache
DELETE /api/cache/{key}         # Delete specific entry
```

## Performance Optimization

### Cache Tuning
Adjust cache settings in `config.yaml`:
```yaml
cache_enabled: true
max_text_length: 500  # Longer texts not cached
cache_dir: "/home/rocky/.rocky_tts/cache"
```

### Audio Quality vs Performance
```yaml
# High quality (slower)
audio_rate: 22050
ffmpeg_filters: highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16

# Performance optimized (faster)  
audio_rate: 16000
ffmpeg_filters: compand,loudnorm=I=-16
```

### Memory Management
```bash
# Monitor memory usage
htop -u rocky

# Check model loading
sudo journalctl -u wyoming-rocky | grep "Model loaded"

# Restart if memory issues
sudo systemctl restart wyoming-rocky
```

### Cache Performance Metrics
- **Cache Hit Rate**: Target >70% for optimal performance
- **Average Synthesis**: <2 seconds for new requests  
- **Cache Response**: <100ms for cached requests
- **Memory Usage**: ~2GB for YourTTS model

## Troubleshooting

### Installation Issues

**Python 3.11 not found**:
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**Permission denied**:
```bash
sudo chown -R rocky:rocky /home/rocky/
sudo chmod +x /home/rocky/wyoming-rocky-tts/scripts/*
```

### Service Issues

**Service won't start (203/EXEC error)**:
```bash
# Run the automated fix script
sudo ./fix_systemd_services.sh

# This script will:
# - Check Python executables in virtual environment
# - Create python3 symlink if needed
# - Update systemd service files
# - Test service commands
# - Restart services with diagnostics
```

**Manual service troubleshooting**:
```bash
# Check detailed logs
sudo journalctl -u wyoming-rocky -n 50 --no-pager

# Verify configuration
sudo -u rocky python3 -m src.config --validate

# Check dependencies
sudo -u rocky pip list | grep -E "(torch|TTS|wyoming)"

# Test service command manually
sudo -u rocky /home/rocky/wyoming-rocky-tts/venv/bin/python3 -m src.wyoming_server --config /home/rocky/.rocky_tts/config.yaml
```

**Model loading fails**:
```bash
# Verify model download
sudo -u rocky python3 -c "from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/your_tts')"

# Check available memory
free -h

# Restart with clean state
sudo systemctl stop wyoming-rocky
sudo rm -rf /home/rocky/.cache/tts/
sudo systemctl start wyoming-rocky
```

### Audio Issues

**No audio output**:
```bash
# Verify Rocky voice file
ls -la /home/rocky/.rocky_tts/rocky_reference.wav

# Test audio pipeline
test-rocky-tts "test" --debug

# Check FFmpeg
which ffmpeg
ffmpeg -version
```

**Poor audio quality**:
```bash
# Check audio filters in config.yaml
grep ffmpeg_filters /home/rocky/.rocky_tts/config.yaml

# Test without filters
test-rocky-tts "test" --no-filters
```

### Home Assistant Connection

**Can't connect from HA**:
```bash
# Verify service is listening
sudo ss -lntp | grep 10202

# Test Wyoming protocol
curl -v http://your-server:10202

# Check firewall
sudo ufw status
sudo ufw allow 10202/tcp
```

**TTS entity not appearing**:
- Restart Home Assistant
- Check HA logs: Settings > System > Logs
- Re-add Wyoming integration
- Verify server IP/port

### Cache Problems

**Cache not working**:
```bash
# Verify cache directory
ls -la /home/rocky/.rocky_tts/cache/

# Check permissions  
sudo chown -R rocky:rocky /home/rocky/.rocky_tts/

# Clear and rebuild
rocky-clear-cache
sudo systemctl restart wyoming-rocky
```

**High memory usage**:
```bash
# Check cache size
du -sh /home/rocky/.rocky_tts/cache/

# Set cache limits in config.yaml
max_cache_size_mb: 1000
```

## Development

### Project Structure
```
wyoming-rocky-tts/
├── src/
│   ├── wyoming_server.py      # Main Wyoming TTS server
│   ├── text_normalizer.py     # Text preprocessing and normalization  
│   ├── rocky_styler.py        # Rocky personality transformation
│   ├── cache_manager.py       # High-performance caching system
│   ├── config.py              # Configuration management
│   └── web_ui.py              # Web control panel
├── config/                     # Configuration templates
│   ├── config.yaml            # Main configuration template
│   └── test_config.yaml       # Testing configuration
├── systemd/                    # Service definitions
│   └── wyoming-rocky.service  # SystemD service file
├── scripts/                    # Helper utilities
│   ├── test-rocky-tts         # TTS testing script
│   ├── rocky-cache-stats      # Cache monitoring
│   └── rocky-clear-cache      # Cache management
├── data/                       # Voice samples and assets
│   └── download_rocky_voice.sh # Voice sample downloader
├── install.sh                  # Automated installer
├── start_test_server.sh        # Development testing
└── requirements.txt            # Python dependencies
```

### Local Development
```bash
# Setup development environment
cd /home/rocky/wyoming-rocky-tts
source venv/bin/activate

# Run individual components
python -m src.wyoming_server --config config/test_config.yaml
python -m src.web_ui --port 8088

# Run tests
python test_simple.py
python test_openai_simple.py

# Development mode with auto-reload
./start_test_server.sh
```

### Contributing
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

## Version History

### v2.1.0 (Current)
- ✅ Added OpenAI integration for creative text styling
- ✅ Improved web UI with style mode selection
- ✅ Enhanced caching performance (30x faster cache hits)
- ✅ Fixed Wyoming server status detection
- ✅ Added FFmpeg audio processing
- ✅ Updated installation script with better error handling
- ✅ Comprehensive documentation and troubleshooting

### v2.0.0
- ✅ Complete rewrite with Wyoming protocol
- ✅ Added web control panel
- ✅ Implemented smart caching system
- ✅ Enhanced Rocky personality engine
- ✅ Added pronunciation override system

## License

MIT License - See LICENSE file for details.

## Credits

- **Wyoming Protocol**: Rhasspy project for Home Assistant integration
- **Speech Synthesis**: Coqui TTS and YourTTS model
- **Rocky Character**: Inspired by Andy Weir's "Project Hail Mary"
- **Community**: Contributors and testers from Home Assistant community

## Support

For issues, questions, or contributions:

- **GitHub Issues**: [Report bugs or request features](https://github.com/jacko873/wyoming-rocky-tts/issues)
- **Home Assistant Forum**: Search for Wyoming Rocky TTS discussions
- **Logs**: Always include `journalctl -u wyoming-rocky -n 50` output for issues

---

*"Rocky help make Home Assistant talk good good good!"* 🗿