#!/usr/bin/env python3

import os
from pathlib import Path
from src.config import Config
from src.rocky_styler import RockyStyler

# Load .env file if it exists
env_file = Path(".env")
if env_file.exists():
    print("Loading .env file...")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                print(f"Loaded: {key.strip()}")

print("Testing OpenAI vs Rules mode...")
print(f"API Key available: {'OPENAI_API_KEY' in os.environ}")

config = Config.load(Path('config/test_config.yaml'))
test_text = "The lights have been turned on successfully and everything is working great!"

print(f"\nInput: {test_text}")

# Rules mode
rules_styler = RockyStyler("rules", config)
rules_result = rules_styler.apply_style(test_text)
print(f"Rules mode: {rules_result}")

# OpenAI mode (will fallback to rules if no API key)
openai_styler = RockyStyler("openai", config) 
openai_result = openai_styler.apply_style(test_text)
print(f"OpenAI mode: {openai_result}")

if rules_result == openai_result:
    print("\n⚠️  OpenAI mode fell back to rules (likely no API key or OpenAI error)")
else:
    print("\n✅ OpenAI mode working - different output than rules!")