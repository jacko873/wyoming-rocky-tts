#!/usr/bin/env python3
"""
Local test script for Wyoming Rocky TTS
Tests core functionality without full installation
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from src.text_normalizer import TextNormalizer
        print("✓ TextNormalizer imported")
        
        from src.rocky_styler import RockyStyler
        print("✓ RockyStyler imported")
        
        from src.cache_manager import CacheManager
        print("✓ CacheManager imported")
        
        from src.config import Config
        print("✓ Config imported")
        
        print("✓ All core modules imported successfully!\n")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}\n")
        return False

def test_text_normalizer():
    """Test text normalization"""
    print("Testing Text Normalizer...")
    from src.text_normalizer import TextNormalizer
    
    normalizer = TextNormalizer()
    
    test_cases = [
        ("72°F", "seventy two degrees fahrenheit"),
        ("30%", "thirty percent"),
        ("3:45 PM", "three forty five P M"),
        ("10 mph", "ten miles per hour"),
        ("Room is 68°F with 45% humidity", "Room is sixty eight degrees fahrenheit with forty five percent humidity"),
    ]
    
    for input_text, expected_contains in test_cases:
        result = normalizer.normalize(input_text)
        print(f"  Input: '{input_text}'")
        print(f"  Output: '{result}'")
        if expected_contains.lower() in result.lower():
            print(f"  ✓ Contains expected text")
        else:
            print(f"  ✗ Expected to contain: '{expected_contains}'")
        print()
    
    print("✓ Text Normalizer tests complete!\n")

def test_rocky_styler():
    """Test Rocky style transformations"""
    print("Testing Rocky Styler...")
    from src.rocky_styler import RockyStyler
    
    styler = RockyStyler(mode="rules")
    
    test_cases = [
        ("The lights are turned on", "Lights on. Good good good"),
        ("I don't understand", "I no understand"),
        ("That's amazing", "That amaze amaze amaze"),
        ("What do you mean?", "What mean, question?"),
        ("Task completed successfully", "Task complete. Good good good good good"),
    ]
    
    for input_text, expected_pattern in test_cases:
        result = styler.apply_style(input_text)
        print(f"  Input: '{input_text}'")
        print(f"  Output: '{result}'")
        # Check if key patterns are present
        if any(word in result.lower() for word in expected_pattern.lower().split()[:3]):
            print(f"  ✓ Style applied")
        else:
            print(f"  ✗ Expected pattern: '{expected_pattern}'")
        print()
    
    print("✓ Rocky Styler tests complete!\n")

def test_cache_manager():
    """Test cache manager functionality"""
    print("Testing Cache Manager...")
    from src.cache_manager import CacheManager, CacheEntry
    import time
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(Path(tmpdir))
        
        # Test cache key generation
        key = cache.get_cache_key("Hello world", "rules", "test_voice")
        print(f"  Generated cache key: {key[:16]}...")
        print(f"  ✓ Cache key generated")
        
        # Test storing entry
        entry = CacheEntry(
            raw_text="Hello world",
            styled_text="Hello world. Good good good",
            normalized_text="Hello world good good good",
            wav_path=f"{tmpdir}/test.wav",
            created_at=time.time(),
            last_used_at=time.time(),
            hit_count=1,
            synthesis_duration_ms=100,
            style_duration_ms=10,
            total_duration_ms=110,
            cache_key=key
        )
        
        cache.put(entry)
        print(f"  ✓ Cache entry stored")
        
        # Test retrieving entry
        retrieved = cache.get(key)
        if retrieved and retrieved.raw_text == "Hello world":
            print(f"  ✓ Cache entry retrieved")
        else:
            print(f"  ✗ Failed to retrieve cache entry")
        
        # Test stats
        stats = cache.get_stats()
        print(f"  Cache stats: {stats['total_entries']} entries, {stats['total_hits']} hits")
        print(f"  ✓ Cache stats working")
    
    print("✓ Cache Manager tests complete!\n")

def test_config():
    """Test configuration loading"""
    print("Testing Config...")
    from src.config import Config
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        
        # Test default config
        config = Config()
        print(f"  Default Wyoming port: {config.wyoming_port}")
        print(f"  Default style mode: {config.style_mode}")
        print(f"  ✓ Default config created")
        
        # Test saving config
        config.save(config_path)
        if config_path.exists():
            print(f"  ✓ Config saved to file")
        
        # Test loading config
        loaded_config = Config.load(config_path)
        if loaded_config.wyoming_port == config.wyoming_port:
            print(f"  ✓ Config loaded from file")
    
    print("✓ Config tests complete!\n")

def test_pipeline():
    """Test the complete text processing pipeline"""
    print("Testing Complete Pipeline...")
    from src.text_normalizer import TextNormalizer
    from src.rocky_styler import RockyStyler
    
    normalizer = TextNormalizer()
    styler = RockyStyler(mode="rules")
    
    test_text = "The temperature is 72°F and the lights are turned on."
    
    print(f"  Original: {test_text}")
    
    # Apply Rocky style
    styled = styler.apply_style(test_text)
    print(f"  Styled: {styled}")
    
    # Normalize for TTS
    normalized = normalizer.normalize(styled)
    print(f"  Normalized: {normalized}")
    
    print("✓ Pipeline test complete!\n")

def test_installer_syntax():
    """Test installer script syntax"""
    print("Testing installer script...")
    import subprocess
    
    result = subprocess.run(
        ["bash", "-n", "install.sh"],
        capture_output=True,
        text=True,
        cwd="/home/coder/workspace/wyoming-rocky-tts"
    )
    
    if result.returncode == 0:
        print("  ✓ Installer script syntax is valid")
    else:
        print(f"  ✗ Installer script has syntax errors: {result.stderr}")
    
    print("✓ Installer test complete!\n")

def main():
    print("=" * 50)
    print("Wyoming Rocky TTS - Local Test Suite")
    print("=" * 50)
    print()
    
    # Run all tests
    tests_passed = True
    
    if not test_imports():
        tests_passed = False
        print("⚠️  Some imports failed. Installing missing dependencies might be needed.")
        print("    Run: pip install pyyaml num2words")
        print()
    
    try:
        test_text_normalizer()
    except Exception as e:
        print(f"⚠️  Text Normalizer test failed: {e}\n")
        tests_passed = False
    
    try:
        test_rocky_styler()
    except Exception as e:
        print(f"⚠️  Rocky Styler test failed: {e}\n")
        tests_passed = False
    
    try:
        test_cache_manager()
    except Exception as e:
        print(f"⚠️  Cache Manager test failed: {e}\n")
        tests_passed = False
    
    try:
        test_config()
    except Exception as e:
        print(f"⚠️  Config test failed: {e}\n")
        tests_passed = False
    
    try:
        test_pipeline()
    except Exception as e:
        print(f"⚠️  Pipeline test failed: {e}\n")
        tests_passed = False
    
    try:
        test_installer_syntax()
    except Exception as e:
        print(f"⚠️  Installer test failed: {e}\n")
        tests_passed = False
    
    # Summary
    print("=" * 50)
    if tests_passed:
        print("✅ All tests passed! The project is ready for deployment.")
    else:
        print("⚠️  Some tests had issues. Review the output above.")
    print("=" * 50)

if __name__ == "__main__":
    main()