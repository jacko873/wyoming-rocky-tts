#!/usr/bin/env python3

import logging
import os
from pathlib import Path
from src.config import Config
from src.rocky_styler import RockyStyler

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=== OpenAI Test with Detailed Logging ===")

# Check environment
api_key = os.getenv('OPENAI_API_KEY', 'NOT_SET')
print(f"API Key in environment: {'YES' if api_key != 'NOT_SET' else 'NO'}")
if api_key != 'NOT_SET':
    print(f"API Key starts with: {api_key[:10]}...")

# Load config
config = Config.load(Path('config/test_config.yaml'))
print(f"Config style_mode: {config.style_mode}")

# Test text
test_text = "Hello! The lights have been turned on successfully."
print(f"Test text: {test_text}")

print("\n=== Creating Rocky Styler ===")
styler = RockyStyler(config.style_mode, config)

print(f"Final styler mode: {styler.mode}")
print(f"Has OpenAI client: {hasattr(styler, 'openai_client')}")

print("\n=== Applying Style ===")
result = styler.apply_style(test_text)
print(f"Result: {result}")