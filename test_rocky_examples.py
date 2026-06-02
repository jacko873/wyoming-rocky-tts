#!/usr/bin/env python3
"""Test Rocky transformations with specific examples"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rocky_styler import RockyStyler

def test_examples():
    styler = RockyStyler(mode="rules")
    
    test_cases = [
        # From the gist examples
        ("I don't understand", "No understand"),
        ("What do you mean?", "What mean, question?"),
        ("That's really amazing!", "That very amaze amaze amaze!"),
        ("This approach is terrible", "This approach bad bad bad"),
        ("Goodbye my friend", "See you later. But I no see you later my friend"),
        
        # Testing emphasis tripling
        ("That's good", "That good good good"),
        ("This is bad", "This bad bad bad"),
        ("I'm sorry", "I sorry sorry sorry"),
        ("I'm very sorry about that", "I very sorry sorry sorry about that"),
        
        # Testing questions
        ("How are you?", "How you, question?"),
        ("What do you want me to do?", "What you want me to do, question?"),
        ("Can you help me?", "Can you help me, question?"),
        ("Would you like some help?", "Would you like some help, question?"),
        
        # Home Assistant responses
        ("The lights have been turned on", "Lights on. Good good good"),
        ("I couldn't find that device", "I no see that device"),
        ("Unable to connect", "No can connect"),
        ("Task completed successfully", "Task completed good good good"),
        
        # Articles and auxiliaries
        ("The cat is on the mat", "Cat on mat"),
        ("A bird was singing", "Bird singing"),
        ("I will make a chain", "I make chain"),
        ("Grace should go home", "Grace go home"),
    ]
    
    print("=" * 60)
    print("ROCKY TRANSFORMATION TESTS")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    for input_text, expected in test_cases:
        result = styler.apply_style(input_text)
        
        # For some, we just check if key patterns are present
        if "..." in expected:
            # Partial match
            success = expected.replace("...", "") in result
        else:
            # Exact or close match
            success = result.lower() == expected.lower() or result == expected
        
        if success:
            print(f"✅ PASS")
            passed += 1
        else:
            print(f"❌ FAIL")
            failed += 1
        
        print(f"   Input:    {input_text}")
        print(f"   Expected: {expected}")
        print(f"   Got:      {result}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

if __name__ == "__main__":
    test_examples()