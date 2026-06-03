# Wyoming Rocky TTS - Testing Guide

## Quick Tests

### Basic Rocky Transformations
```bash
python3 test_simple.py
```
No dependencies required - tests core Rocky speech patterns.

### Comprehensive Pattern Tests
```bash
python3 test_rocky_examples.py
```
Tests all transformation rules and edge cases.

### Full System Test
```bash
python3 test_local.py
```
Complete test suite (requires pyyaml and num2words).

## Testing the Installation

### 1. Test on Local Machine (Development)

```bash
# Clone the repo
git clone https://github.com/jacko873/wyoming-rocky-tts.git
cd wyoming-rocky-tts

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python test_local.py
```

### 2. Test on Debian 12 LXC (Production)

```bash
# As root on fresh Debian 12
curl -sSL https://raw.githubusercontent.com/jacko873/wyoming-rocky-tts/main/install.sh | bash

# After installation, test with:
test-rocky-tts "Hello, this is a test"
rocky-cache-stats
systemctl status wyoming-rocky
```

### 3. Test with Home Assistant

After installation:

1. Add Wyoming integration in Home Assistant
2. Test with service call:
```yaml
service: tts.speak
data:
  entity_id: media_player.living_room
  message: "The temperature is 72 degrees"
  language: en
  options:
    voice: rocky
```

## Test Cases

### Text Normalization
- Numbers: `72` → `seventy two`
- Temperature: `72°F` → `seventy two degrees fahrenheit`
- Percentage: `30%` → `thirty percent`
- Time: `3:45 PM` → `three forty five P M`
- Units: `10 mph` → `ten miles per hour`

### Rocky Style
- Simple: `"I don't understand"` → `"I no understand"`
- Emphasis: `"That's amazing"` → `"That amaze amaze amaze"`
- Questions: `"What do you mean?"` → `"What mean, question?"`
- Actions: `"Turned on the lights"` → `"Lights on. Good good good"`

### Cache System
- First request: generates audio
- Repeated request: returns cached audio
- Cache stats: tracks hits and storage

### Web UI (Port 8088)
- Service status display
- Test text processing pipeline
- Cache management
- Pronunciation overrides
- Audio generation

## Performance Testing

### Memory Usage
```bash
# Monitor during model load
htop -u rocky
```

Expected: ~2GB RAM for YourTTS model

### Response Time
```bash
# Time synthesis
time test-rocky-tts "Quick test"
```

Expected: 
- First run: 5-10 seconds (model loading)
- Subsequent: 1-3 seconds
- Cached: <100ms

## Troubleshooting Tests

### Check Services
```bash
systemctl status wyoming-rocky
systemctl status wyoming-rocky-web
journalctl -u wyoming-rocky -n 50
```

### Check Ports
```bash
ss -lntp | grep -E "10202|8088"
netstat -tlpn | grep -E "10202|8088"
```

### Test Wyoming Protocol
```bash
curl -X POST http://localhost:10202/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Test message", "voice": "rocky"}'
```

### Test Web UI API
```bash
# Check status
curl http://localhost:8088/api/status

# Test text processing
curl -X POST http://localhost:8088/api/test \
  -F "text=Hello world" \
  -F "use_style=true"
```

## Expected Test Results

✅ **Passing Tests:**
- Installer script syntax valid
- Rocky style transformations working
- Cache manager operations
- Module imports (with dependencies)
- Text normalization
- Configuration save/load

⚠️ **May Need Dependencies:**
- Full text normalizer (needs num2words)
- Config YAML operations (needs pyyaml)
- TTS synthesis (needs full install)

## Continuous Testing

Before pushing updates:

```bash
# Check syntax
bash -n install.sh

# Run basic tests
python3 test_simple.py

# Check git status
git status

# Run full tests if dependencies available
python3 test_local.py
```