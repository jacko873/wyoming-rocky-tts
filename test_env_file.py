#!/usr/bin/env python3

import os
from pathlib import Path

# Load .env file manually for testing
env_file = Path(".env")
if env_file.exists():
    print("✅ Found .env file")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                print(f"Loaded: {key.strip()} = {value.strip()[:10]}...")
else:
    print("❌ No .env file found")

# Check if API key is loaded
api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key loaded: {'YES' if api_key else 'NO'}")
if api_key:
    print(f"Key starts with: {api_key[:15]}...")

# Now test the Rocky styler
from src.config import Config
from src.rocky_styler import RockyStyler

config = Config.load(Path('config/test_config.yaml'))
styler = RockyStyler('openai', config)

print(f"Styler mode: {styler.mode}")
print(f"Has OpenAI client: {hasattr(styler, 'openai_client')}")

if hasattr(styler, 'openai_client'):
    print("🎉 OpenAI mode is ready!")
else:
    print("⚠️  Still in rules mode")