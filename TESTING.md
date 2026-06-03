# Wyoming Rocky TTS - Testing Guide v2.1

This document provides comprehensive testing procedures for all components of Wyoming Rocky TTS v2.1.

## Quick Verification Checklist

After installation, verify these components are working:

### ✅ Basic Installation Check
```bash
# Check services are running
sudo systemctl status wyoming-rocky
sudo systemctl status wyoming-rocky-web

# Check ports are listening
ss -lntp | grep 10202  # Wyoming TTS
ss -lntp | grep 8088   # Web UI

# Test basic functionality
test-rocky-tts "Hello world"
rocky-cache-stats
```

### ✅ Component Tests

#### 1. Text Normalization & Rocky Styling
```bash
# Test basic Rocky transformations
test-rocky-tts "I don't understand what you mean"
# Expected: "No understand what mean, question?"

test-rocky-tts "The lights have been turned on successfully"
# Expected: "Lights on. Good good good"

test-rocky-tts "That's absolutely amazing!"
# Expected: "That amaze amaze amaze!"
```

#### 2. Text Normalization
```bash
# Test number and unit handling
test-rocky-tts "The temperature is 72°F"
# Expected: "Temperature seventy two degrees fahrenheit"

test-rocky-tts "It's 3:45 PM and 30% humidity"
# Expected: "three forty five P M and thirty percent humidity"
```

#### 3. OpenAI Integration (if configured)
```bash
# Test OpenAI mode
python3 test_openai_simple.py

# Expected output shows different results:
# Rules: "Lights on. Good good good"  
# OpenAI: Creative variation like "Lights on successful!"
```

#### 4. Web UI Interface
1. Open browser: `http://your-server:8088`
2. Test text transformation with different modes:
   - Off: No Rocky styling
   - Rules: Pattern-based transformations
   - OpenAI: AI-generated variations (if configured)
3. Test audio generation and playback
4. Verify cache statistics display
5. Test pronunciation override management

#### 5. Wyoming Protocol Integration
```bash
# Test Wyoming server connectivity
curl -v http://localhost:10202

# Expected: Connection successful (may show protocol info)
```

## Detailed Test Scripts

### Test 1: Complete Text Processing Pipeline
```bash
# Save as: test_complete_pipeline.py
source venv/bin/activate
python3 test_simple.py
```

### Test 2: Cache Performance Test
```bash
# Test cache performance
rocky-clear-cache
time test-rocky-tts "Test message"  # First run (cold)
time test-rocky-tts "Test message"  # Second run (cached)

# Check cache statistics
rocky-cache-stats
```

### Test 3: OpenAI Integration Test
```bash
# Test OpenAI integration (requires .env with API key)
python3 test_openai_simple.py

# Expected: Shows different outputs for rules vs OpenAI mode
```

## Performance Benchmarks

### Expected Performance Metrics

| Component | Metric | Target | Notes |
|-----------|--------|--------|-------|
| **Text Processing** | Rocky styling | <50ms | Rules-based mode |
| **Text Processing** | OpenAI styling | <3s | Includes API call |
| **Text Normalization** | Number/unit processing | <10ms | Regex-based |
| **Cache Performance** | Cache hit response | <100ms | Cached audio retrieval |
| **TTS Synthesis** | New audio generation | <5s | YourTTS model processing |
| **Memory Usage** | Total RAM usage | ~2GB | Includes YourTTS model |
| **Cache Hit Rate** | Production usage | >70% | After initial warmup |

### Performance Testing Commands

```bash
# Test text processing speed
time test-rocky-tts "The lights are turned on successfully"

# Test cache performance
rocky-clear-cache
time test-rocky-tts "Test message"  # First run (cold)
time test-rocky-tts "Test message"  # Second run (cached)

# Monitor memory usage
htop -u rocky

# Check cache hit rates
rocky-cache-stats
```

## Integration Testing

### Home Assistant Integration Test

1. **Add Wyoming Integration**:
   - Go to Settings → Devices & Services
   - Add Integration → Wyoming Protocol
   - Host: your-server-ip, Port: 10202

2. **Test TTS Service**:
   ```yaml
   # In Home Assistant Developer Tools → Services
   service: tts.speak
   target:
     entity_id: media_player.your_speaker
   data:
     entity_id: tts.rocky_yourtts
     message: "The lights have been turned on successfully"
   ```

3. **Expected Result**: 
   - Audio plays with Rocky's voice saying "Lights on. Good good good"

### API Integration Tests

#### Web UI API Tests
```bash
# Test status endpoint
curl -s http://localhost:8088/api/status | jq

# Test text processing - Rules mode
curl -s -X POST -F "text=Hello world" -F "style_mode=rules" \
  http://localhost:8088/api/test | jq

# Test text processing - OpenAI mode
curl -s -X POST -F "text=Hello world" -F "style_mode=openai" \
  http://localhost:8088/api/test | jq

# Test cache stats
curl -s http://localhost:8088/api/cache/stats | jq
```

#### Audio Synthesis Test
```bash
# Test audio generation
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"text":"Hello Rocky", "style_mode":"rules", "voice_speed":"150"}' \
  http://localhost:8088/api/synthesize \
  -o test_audio.wav

# Verify audio file was created
file test_audio.wav
ls -la test_audio.wav
```

## Troubleshooting Test Scenarios

### Common Issues and Tests

#### 1. Service Won't Start
```bash
# Check detailed logs
sudo journalctl -u wyoming-rocky -n 100 --no-pager

# Verify configuration loads
sudo -u rocky test-rocky-tts "Configuration test"
```

#### 2. Model Loading Fails
```bash
# Test model download manually
sudo -u rocky python3 -c "
import sys
sys.path.append('/home/rocky/wyoming-rocky-tts')
from TTS.api import TTS
print('Downloading YourTTS model...')
tts = TTS('tts_models/multilingual/multi-dataset/your_tts')
print('Model loaded successfully')
"
```

#### 3. Audio Quality Issues
```bash
# Check FFmpeg is working
ffmpeg -version
which ffmpeg

# Test basic audio generation
test-rocky-tts "Audio quality test"
```

#### 4. Cache Problems
```bash
# Test cache directory permissions
ls -la /home/rocky/.rocky_tts/cache/
sudo -u rocky touch /home/rocky/.rocky_tts/cache/test_file
rm /home/rocky/.rocky_tts/cache/test_file

# Verify cache functionality
rocky-clear-cache
rocky-cache-stats
```

#### 5. OpenAI Integration Issues
```bash
# Check if .env file exists and has API key
ls -la .env
grep "OPENAI_API_KEY" .env

# Test OpenAI connectivity
python3 test_openai_simple.py

# Check logs for OpenAI errors
sudo journalctl -u wyoming-rocky | grep -i openai
```

## Security Testing

### Basic Security Checks
```bash
# Verify service runs as non-root user
ps aux | grep wyoming-rocky

# Check file permissions
ls -la /home/rocky/.rocky_tts/
ls -la /home/rocky/wyoming-rocky-tts/

# Verify network bindings
ss -lntp | grep -E "(10202|8088)"
```

## Load Testing

### Basic Load Tests
```bash
# Concurrent text processing test
for i in {1..10}; do
  test-rocky-tts "Load test message $i" &
done
wait

# Cache stress test
for i in {1..50}; do
  test-rocky-tts "Cache test message $((i % 10))"
done

# Check performance after load
rocky-cache-stats
```

## Web UI Testing

### Manual Web UI Tests

1. **Access Web Interface**: `http://your-server:8088`

2. **Service Status Panel**:
   - Verify Wyoming TTS shows "Running"
   - Check port numbers are correct
   - Confirm style mode is displayed

3. **Text Transformation Testing**:
   - Enter test text: "The lights are turned on successfully"
   - Test each style mode:
     - **Off**: Should show original text
     - **Rules**: Should show "Lights on. Good good good"
     - **OpenAI**: Should show creative variation (if configured)

4. **Audio Generation**:
   - Click "Generate & Play Audio"
   - Verify audio player appears and works
   - Test different voice speeds

5. **Cache Management**:
   - View cache statistics
   - Test "Clear All Cache" functionality
   - Verify cache entries are listed

6. **Pronunciation Overrides**:
   - Add new override: "HA" → "Home Assistant"
   - Test in text transformation
   - Delete override and verify removal

### Automated Web UI Tests
```bash
# Test all style modes via API
for mode in "off" "rules" "openai"; do
  echo "Testing $mode mode:"
  curl -s -X POST -F "text=Hello world test" -F "style_mode=$mode" \
    http://localhost:8088/api/test | jq '.styled'
done

# Test cache operations
echo "Testing cache operations:"
curl -s -X POST http://localhost:8088/api/cache/clear
curl -s http://localhost:8088/api/cache/stats | jq
```

## OpenAI Integration Testing

### Prerequisites
```bash
# Verify OpenAI package is installed
pip list | grep openai

# Check for .env file with API key
test -f .env && echo "✓ .env file exists" || echo "✗ No .env file"

# Verify API key is loaded
python3 -c "
import os
from pathlib import Path

env_file = Path('.env')
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if 'OPENAI_API_KEY' in line and '=' in line:
                print('✓ API key found in .env')
                break
        else:
            print('✗ No API key in .env')
else:
    print('✗ No .env file')
"
```

### OpenAI Test Cases
```bash
# Test different text types with OpenAI mode
test_texts=(
    "The lights have been turned on successfully"
    "I don't understand what you're asking"
    "The temperature is perfect right now"
    "Everything is working correctly"
    "Please wait while I process this request"
)

for text in "${test_texts[@]}"; do
    echo "Testing: $text"
    curl -s -X POST -F "text=$text" -F "style_mode=openai" \
      http://localhost:8088/api/test | jq '.styled'
    echo "---"
done
```

## Final Verification Checklist

Before considering installation complete, verify:

- [ ] ✅ Wyoming TTS service starts and stays running
- [ ] ✅ Web UI accessible and functional at port 8088
- [ ] ✅ Basic Rocky text transformations work correctly
- [ ] ✅ Audio generation produces valid WAV files
- [ ] ✅ Cache system improves performance on repeated requests
- [ ] ✅ Home Assistant Wyoming integration connects successfully
- [ ] ✅ OpenAI integration works (if configured with API key)
- [ ] ✅ Service logs show no critical errors
- [ ] ✅ Memory usage remains stable under load
- [ ] ✅ All helper scripts function correctly
- [ ] ✅ Web UI shows all three style modes working
- [ ] ✅ Cache statistics display correctly
- [ ] ✅ Pronunciation overrides can be added/removed

## Test Environment Specifications

**Minimum Test Environment**:
- OS: Debian 12 or Ubuntu 22.04+
- RAM: 4GB (minimum for YourTTS model)
- Storage: 3GB free space
- Network: Ports 10202, 8088 accessible

**Recommended Test Environment**:
- OS: Debian 12 LXC container
- RAM: 6GB (for comfortable operation)
- Storage: 5GB free space
- CPU: 4+ cores (for faster model processing)

## Regression Testing

### Before Each Release
```bash
# 1. Test installer syntax
bash -n install.sh

# 2. Run basic functionality tests
source venv/bin/activate
python3 test_simple.py

# 3. Test OpenAI integration (if configured)
python3 test_openai_simple.py

# 4. Check all services start correctly
sudo systemctl restart wyoming-rocky
sudo systemctl restart wyoming-rocky-web
sleep 10
systemctl is-active --quiet wyoming-rocky && echo "✓ Wyoming TTS running"
systemctl is-active --quiet wyoming-rocky-web && echo "✓ Web UI running"

# 5. Test web UI API endpoints
curl -s http://localhost:8088/api/status | jq .running
curl -s http://localhost:8088/api/cache/stats | jq .total_entries

# 6. Performance verification
time test-rocky-tts "Performance test"
```

---

*"Testing good good good! Rocky help make sure everything work!"* 🗿

For additional testing scenarios or troubleshooting assistance, refer to the main README.md or submit an issue on GitHub.