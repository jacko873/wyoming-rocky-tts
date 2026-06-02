#!/usr/bin/env python3
"""
Simple test without external dependencies
Tests core Rocky style transformations
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only modules without external dependencies
from src.rocky_styler import RockyStyler

def test_rocky_examples():
    """Test Rocky style with examples from the documentation"""
    
    print("=" * 60)
    print("ROCKY STYLE TRANSFORMATION TESTS")
    print("=" * 60)
    print()
    
    styler = RockyStyler(mode="rules")
    
    examples = [
        # Basic transformations
        ("The lights are turned on", "should contain 'on' and 'good'"),
        ("The lights are turned off", "should contain 'off' and 'good'"),
        ("Task is done", "should contain 'done' and 'good'"),
        
        # Negatives
        ("I can't do that", "should contain 'no can'"),
        ("I don't understand", "should contain 'no understand'"),
        ("I couldn't find it", "should contain 'no could' or 'no see'"),
        
        # Questions
        ("What do you mean?", "should end with 'question?'"),
        ("How does this work?", "should end with 'question?'"),
        ("Would you like me to continue?", "should contain 'You want'"),
        
        # Emotions
        ("That's amazing!", "should contain 'amaze'"),
        ("This is terrible", "should contain 'bad'"),
        ("I'm sorry about that", "should contain 'sorry'"),
        
        # Home Assistant responses
        ("The living room lights have been turned on", "should mention lights are on"),
        ("Successfully completed the automation", "should contain 'good'"),
        ("Unable to connect to the device", "should contain 'no can'"),
    ]
    
    print("Testing Rocky Style Transformations:")
    print("-" * 60)
    
    for original, description in examples:
        transformed = styler.apply_style(original)
        print(f"\n📝 Original:  {original}")
        print(f"🗿 Rocky:     {transformed}")
        print(f"   Expected:  {description}")
    
    print("\n" + "=" * 60)
    print("SAMPLE HOME ASSISTANT RESPONSES")
    print("=" * 60)
    
    ha_responses = [
        "The temperature is set to 72 degrees",
        "Turning on the living room lights",
        "I couldn't find a device named bedroom fan",
        "The garage door is now closed",
        "Would you like me to turn off all lights?",
        "The automation has been triggered successfully",
        "Sorry, I don't understand what you want me to do",
    ]
    
    print("\nHome Assistant → Rocky Style:\n")
    
    for response in ha_responses:
        rocky_response = styler.apply_style(response)
        print(f"HA:    {response}")
        print(f"Rocky: {rocky_response}")
        print()
    
    print("=" * 60)
    print("✅ Testing complete! Review the transformations above.")
    print("=" * 60)

if __name__ == "__main__":
    test_rocky_examples()