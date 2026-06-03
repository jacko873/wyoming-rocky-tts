#!/usr/bin/env python3

import os
from pathlib import Path
from src.config import Config
from src.rocky_styler import RockyStyler

# Test with API key - replace with your actual key
api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()

if api_key:
    os.environ['OPENAI_API_KEY'] = api_key
    print("✅ API key set for testing")
else:
    print("⚠️  No API key provided - will test fallback behavior")

config = Config.load(Path('config/test_config.yaml'))
test_text = "The lights have been turned on successfully and everything is working great!"

print(f"\nInput: {test_text}")

# Rules mode
rules_styler = RockyStyler("rules", config)
rules_result = rules_styler.apply_style(test_text)
print(f"Rules mode: {rules_result}")

# OpenAI mode
openai_styler = RockyStyler("openai", config) 
openai_result = openai_styler.apply_style(test_text)
print(f"OpenAI mode: {openai_result}")

if rules_result == openai_result:
    print("\n⚠️  OpenAI mode fell back to rules")
else:
    print("\n✅ OpenAI mode working - generated different output!")