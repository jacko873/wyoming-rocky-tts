# Wyoming Rocky TTS

A Wyoming-protocol compatible TTS server for Home Assistant that generates speech using Coqui YourTTS with a Rocky-inspired alien helper voice style.

## Features

- **Wyoming Protocol Compatible**: Integrates seamlessly with Home Assistant
- **Rocky-Style Personality**: Adds a fun alien helper personality to TTS responses
- **Advanced Text Normalization**: Handles numbers, temperatures, times, units, and more
- **Pronunciation Overrides**: Customize how specific words and phrases are spoken
- **Smart Caching**: Caches generated audio for frequently used phrases
- **Web UI**: Control panel for configuration, testing, and management
- **OpenAI Integration**: Optional OpenAI-powered text styling

## Quick Install

Run this installer as root on a fresh Debian 12 LXC container:

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/wyoming-rocky-tts/main/install.sh | bash
```

Or download and run:

```bash
wget https://raw.githubusercontent.com/yourusername/wyoming-rocky-tts/main/install.sh
chmod +x install.sh
./install.sh
```

## Manual Installation

### Prerequisites

- Debian 12 (or compatible Linux distribution)
- Python 3.11
- Root access for initial setup
- At least 4GB RAM (for TTS model)
- 2GB+ free disk space

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wyoming-rocky-tts.git
cd wyoming-rocky-tts
```

2. Run the installer:
```bash
sudo ./install.sh
```

The installer will:
- Install system dependencies
- Create a dedicated `rocky` user
- Set up Python virtual environment
- Install all Python packages
- Download the Rocky reference voice
- Configure systemd services
- Start the services

## Home Assistant Integration

After installation, add the Wyoming integration in Home Assistant:

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Wyoming Protocol**
4. Enter:
   - Host: Your server's IP address
   - Port: 10202

The TTS entity will appear as `tts.rocky_yourtts` or similar.

## Configuration

### Main Configuration

Edit `/home/rocky/.rocky_tts/config.yaml`:

```yaml
# Wyoming Settings
wyoming_port: 10202

# Style Settings
style_mode: rules  # Options: off, rules, openai

# Audio Settings
audio_rate: 22050
ffmpeg_filters: highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16
```

### Pronunciation Overrides

Edit `/home/rocky/.rocky_tts/overrides.yaml`:

```yaml
# Format: "original": "spoken as"
Aj: Ajay
HA: Home Assistant
"PM2.5": P M two point five
```

### Environment Variables

Optional environment variables:

```bash
ROCKY_WYOMING_PORT=10202
ROCKY_WEB_PORT=8088
ROCKY_STYLE_MODE=rules
OPENAI_API_KEY=your_key_here  # For OpenAI styling
```

## Web UI

Access the control panel at: `http://your-server:8088`

Features:
- Service status monitoring
- Text processing pipeline testing
- Cache management and statistics
- Pronunciation override editor
- Audio generation testing
- Configuration viewer

## Rocky Style Examples

The Rocky personality transforms text with:

### Simplified Grammar
- "I don't understand" → "I no understand"
- "The lights are turned on" → "Lights on. Good good good"

### Emphasis Through Repetition
- "That's amazing" → "That amaze amaze amaze"
- "Done" → "Done. Good good good"

### Question Format
- "What do you mean?" → "What mean, question?"
- "Would you like me to do that?" → "You want me do this, question?"

## Text Normalization

Automatically handles:

- **Numbers**: 72 → seventy two
- **Temperatures**: 72°F → seventy two degrees fahrenheit
- **Percentages**: 30% → thirty percent
- **Times**: 3:45 PM → three forty five P M
- **Units**: 10 mph → ten miles per hour
- **Decimals**: 3.14 → three point one four

## Commands

### Test TTS
```bash
test-rocky-tts "Hello world"
test-rocky-tts "The temperature is 72°F" --style rules
```

### Cache Management
```bash
rocky-cache-stats     # View cache statistics
rocky-clear-cache     # Clear all cached audio
```

### Service Control
```bash
systemctl status wyoming-rocky
systemctl restart wyoming-rocky
journalctl -u wyoming-rocky -f  # View logs
```

## API Endpoints

### Wyoming Protocol
- Port: 10202
- Protocol: Wyoming TTS

### Web UI API
- `GET /api/status` - Service status
- `GET /api/cache/stats` - Cache statistics
- `POST /api/test` - Test text processing
- `POST /api/synthesize` - Generate audio
- `GET /api/overrides` - List pronunciation overrides
- `POST /api/overrides` - Add override

## Troubleshooting

### Service Won't Start
```bash
journalctl -u wyoming-rocky -n 50
systemctl status wyoming-rocky
```

### No Audio Output
- Check if model loaded: Look for "Model loaded" in logs
- Verify speaker WAV exists: `/home/rocky/.rocky_tts/rocky_reference.wav`
- Test with: `test-rocky-tts "test"`

### Cache Issues
```bash
rocky-clear-cache
systemctl restart wyoming-rocky
```

### Home Assistant Can't Connect
- Verify service is running: `systemctl status wyoming-rocky`
- Check port is open: `ss -lntp | grep 10202`
- Test locally: `curl http://localhost:10202`

## Performance Tuning

### Cache Settings
Adjust in config.yaml:
```yaml
cache_enabled: true
max_text_length: 500
```

### Model Settings
For faster processing on CPU:
```yaml
audio_rate: 16000  # Lower sample rate
```

### Memory Usage
The YourTTS model requires ~2GB RAM. Monitor with:
```bash
htop -u rocky
```

## Development

### Project Structure
```
wyoming-rocky-tts/
├── src/
│   ├── wyoming_server.py    # Main Wyoming server
│   ├── text_normalizer.py   # Text normalization
│   ├── rocky_styler.py      # Rocky personality
│   ├── cache_manager.py     # Cache system
│   ├── config.py            # Configuration
│   └── web_ui.py            # Web interface
├── config/                   # Configuration templates
├── systemd/                  # Service files
├── scripts/                  # Helper scripts
├── data/                     # Voice samples
└── requirements.txt          # Python dependencies
```

### Running in Development
```bash
cd /home/rocky/wyoming-rocky-tts
source venv/bin/activate
python -m src.wyoming_server --config config/config.yaml
```

## License

MIT License - See LICENSE file for details

## Credits

- Based on Wyoming Protocol by Rhasspy
- Uses Coqui TTS for speech synthesis
- Rocky character inspired by community contributions

## Support

For issues or questions:
- Open an issue on GitHub
- Check Home Assistant forums
- Review logs with `journalctl -u wyoming-rocky -f`