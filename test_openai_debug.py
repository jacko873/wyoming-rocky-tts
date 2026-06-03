#!/usr/bin/env python3
"""
Debug script for OpenAI integration in Rocky TTS
Run this to diagnose OpenAI API issues
"""

import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_env_file():
    """Test if .env file exists and can be loaded"""
    print("\n=== Testing .env file ===")
    
    env_files = [
        Path.cwd() / '.env',
        Path(__file__).parent / '.env',
        Path.home() / 'wyoming-rocky-tts' / '.env',
        Path('/home/rocky/wyoming-rocky-tts/.env')
    ]
    
    env_found = False
    for env_file in env_files:
        if env_file.exists():
            print(f"✅ Found .env file at: {env_file}")
            env_found = True
            
            # Check contents
            with open(env_file) as f:
                lines = f.readlines()
                has_key = False
                for line in lines:
                    if 'OPENAI_API_KEY' in line and '=' in line:
                        has_key = True
                        key_part = line.split('=')[1].strip()[:10] + "..."
                        print(f"✅ OPENAI_API_KEY found in file (starts with: {key_part})")
                        break
                
                if not has_key:
                    print("❌ No OPENAI_API_KEY found in .env file")
            break
    
    if not env_found:
        print("❌ No .env file found in any expected location")
        print("Expected locations:")
        for path in env_files:
            print(f"  - {path}")
    
    return env_found

def test_openai_import():
    """Test if OpenAI library can be imported"""
    print("\n=== Testing OpenAI Library ===")
    
    try:
        import openai
        print(f"✅ OpenAI library imported successfully")
        print(f"   Version: {openai.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import OpenAI library: {e}")
        print("   Run: pip install openai")
        return False

def test_rocky_styler():
    """Test RockyStyler with OpenAI mode"""
    print("\n=== Testing RockyStyler OpenAI Mode ===")
    
    try:
        from src.config import Config
        from src.rocky_styler import RockyStyler
        
        # Load config
        config_paths = [
            Path.home() / '.rocky_tts' / 'config.yaml',
            Path('/home/rocky/.rocky_tts/config.yaml'),
            Path.cwd() / 'config' / 'test_config.yaml'
        ]
        
        config = None
        for config_path in config_paths:
            if config_path.exists():
                print(f"Loading config from: {config_path}")
                config = Config.load(config_path)
                break
        
        if not config:
            print("❌ No config file found")
            return False
        
        print(f"Config loaded - OpenAI env var: {config.openai_api_key_env}")
        
        # Create styler with OpenAI mode
        print("\nInitializing RockyStyler with OpenAI mode...")
        styler = RockyStyler("openai", config)
        
        # Check if it fell back to rules mode
        if styler.mode == "rules":
            print("⚠️ Styler fell back to rules mode (OpenAI not available)")
            return False
        else:
            print(f"✅ Styler initialized in {styler.mode} mode")
        
        # Test the styling
        test_text = "The lights have been turned on successfully"
        print(f"\nTesting with text: '{test_text}'")
        
        try:
            result = styler.apply_style(test_text)
            print(f"✅ OpenAI styling successful!")
            print(f"   Result: '{result}'")
            return True
        except Exception as e:
            print(f"❌ OpenAI styling failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error testing RockyStyler: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openai_direct():
    """Test OpenAI API directly"""
    print("\n=== Testing OpenAI API Directly ===")
    
    if not test_openai_import():
        return False
    
    import openai
    
    # Load API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try loading .env file manually
        env_file = Path.cwd() / '.env'
        if not env_file.exists():
            env_file = Path(__file__).parent / '.env'
        
        if env_file.exists():
            print(f"Loading .env from: {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        os.environ[key] = value
            
            api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment")
        return False
    
    print(f"✅ API key found (length: {len(api_key)})")
    
    try:
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client created")
        
        # Test API connection
        print("\nTesting API connection...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Reply with just 'OK'."},
                {"role": "user", "content": "Test"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ API call successful! Response: '{result}'")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API call failed: {e}")
        
        # Check specific error types
        error_str = str(e)
        if "api_key" in error_str.lower():
            print("   Issue: Invalid API key")
            print("   Solution: Check your API key is correct and active")
        elif "rate" in error_str.lower():
            print("   Issue: Rate limit exceeded")
            print("   Solution: Wait a bit or upgrade your OpenAI plan")
        elif "model" in error_str.lower():
            print("   Issue: Model access issue")
            print("   Solution: Check you have access to the requested model")
        else:
            print(f"   Error details: {error_str}")
        
        return False

def main():
    print("="*60)
    print("Wyoming Rocky TTS - OpenAI Integration Diagnostics")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Environment file", test_env_file()))
    results.append(("OpenAI library", test_openai_import()))
    results.append(("OpenAI API direct", test_openai_direct()))
    results.append(("RockyStyler OpenAI", test_rocky_styler()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_pass = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if not passed:
            all_pass = False
    
    print("\n" + "="*60)
    
    if all_pass:
        print("✅ All tests passed! OpenAI integration should work.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("1. Create .env file with: OPENAI_API_KEY=sk-your-key-here")
        print("2. Install OpenAI library: pip install openai")
        print("3. Check your API key is valid at: https://platform.openai.com/api-keys")
        print("4. Ensure you have API credits/billing set up")
    
    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())