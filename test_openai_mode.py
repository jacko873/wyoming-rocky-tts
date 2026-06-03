#!/usr/bin/env python3

import os
from pathlib import Path
from src.config import Config
from src.rocky_styler import RockyStyler

def test_openai_mode():
    """Test script for OpenAI mode styling"""
    
    print("=== Testing OpenAI Mode for Rocky TTS ===\n")
    
    # Check if API key is set
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
        return False
    
    print(f"✅ OpenAI API key found: {api_key[:8]}...")
    
    # Load config
    try:
        config = Config.load(Path('config/test_config.yaml'))
        print(f"✅ Config loaded - OpenAI model: {config.openai_model}")
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Test cases
    test_cases = [
        "Hello! How are you doing today?",
        "The lights have been turned on successfully", 
        "I don't understand what you want me to do",
        "This is absolutely amazing and wonderful!",
        "The temperature is 72 degrees fahrenheit",
        "Can you please help me with this problem?"
    ]
    
    print("\n=== Comparing Rules vs OpenAI Mode ===\n")
    
    # Test both modes
    for test_text in test_cases:
        print(f"Input: {test_text}")
        
        # Rules mode
        rules_styler = RockyStyler("rules", config)
        rules_result = rules_styler.apply_style(test_text)
        print(f"Rules: {rules_result}")
        
        # OpenAI mode
        openai_styler = RockyStyler("openai", config) 
        openai_result = openai_styler.apply_style(test_text)
        print(f"OpenAI: {openai_result}")
        
        print("-" * 50)
    
    return True

if __name__ == "__main__":
    success = test_openai_mode()
    if not success:
        exit(1)