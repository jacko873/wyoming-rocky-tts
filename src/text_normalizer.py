import re
import logging
from pathlib import Path
from typing import Optional, Dict
import json
import yaml
from num2words import num2words

logger = logging.getLogger(__name__)

class TextNormalizer:
    def __init__(self, overrides_file: Optional[Path] = None):
        self.overrides = {}
        if overrides_file and overrides_file.exists():
            self.load_overrides(overrides_file)
    
    def load_overrides(self, file_path: Path):
        try:
            with open(file_path) as f:
                if file_path.suffix == '.yaml':
                    self.overrides = yaml.safe_load(f) or {}
                else:
                    self.overrides = json.load(f)
            logger.info(f"Loaded {len(self.overrides)} pronunciation overrides")
        except Exception as e:
            logger.error(f"Failed to load overrides: {e}")
    
    def normalize(self, text: str) -> str:
        # Step 1: Apply phrase overrides first
        for old, new in self.overrides.items():
            text = text.replace(old, new)
        
        # Step 2: Handle temperature symbols
        text = self._normalize_temperatures(text)
        
        # Step 3: Handle percentages
        text = re.sub(r'(\d+(?:\.\d+)?)%', r'\1 percent', text)
        
        # Step 4: Handle times
        text = self._normalize_times(text)
        
        # Step 5: Convert numbers to words
        text = self._numbers_to_words(text)
        
        # Step 6: Handle common units
        text = self._normalize_units(text)
        
        # Step 7: Clean up punctuation for TTS
        text = self._clean_punctuation(text)
        
        # Step 8: Clean up extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def _normalize_temperatures(self, text: str) -> str:
        # Handle various temperature formats
        text = re.sub(r'(\d+(?:\.\d+)?)\s*°\s*F\b', r'\1 degrees fahrenheit', text)
        text = re.sub(r'(\d+(?:\.\d+)?)\s*°F\b', r'\1 degrees fahrenheit', text)
        text = re.sub(r'(\d+(?:\.\d+)?)\s*°\s*C\b', r'\1 degrees celsius', text)
        text = re.sub(r'(\d+(?:\.\d+)?)\s*°C\b', r'\1 degrees celsius', text)
        text = re.sub(r'(\d+(?:\.\d+)?)\s*°', r'\1 degrees', text)
        return text
    
    def _normalize_times(self, text: str) -> str:
        # Handle time formats like 8:20 PM
        def format_time(match):
            hour = match.group(1)
            minute = match.group(2)
            period = match.group(3).upper() if match.group(3) else ""
            
            if minute == "00":
                return f"{hour} {period}".strip()
            else:
                return f"{hour} {minute} {period}".strip()
        
        text = re.sub(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?', format_time, text)
        return text
    
    def _numbers_to_words(self, text: str) -> str:
        def replace_number(match):
            num = match.group(0)
            try:
                if '.' in num:
                    parts = num.split('.')
                    if len(parts) == 2:
                        integer_part = num2words(int(parts[0])) if parts[0] else "zero"
                        decimal_digits = ' '.join(num2words(int(d)) for d in parts[1])
                        return f"{integer_part} point {decimal_digits}"
                else:
                    return num2words(int(num))
            except:
                return num
        
        # Replace numbers but preserve those already part of converted text
        text = re.sub(r'\b\d+\.?\d*\b', replace_number, text)
        return text
    
    def _normalize_units(self, text: str) -> str:
        units = {
            ' mph': ' miles per hour',
            ' kph': ' kilometers per hour',
            ' kmh': ' kilometers per hour',
            ' ft': ' feet',
            ' m ': ' meters ',
            ' m.': ' meters.',
            ' km': ' kilometers',
            ' mi': ' miles',
            ' kg': ' kilograms',
            ' lb': ' pounds',
            ' lbs': ' pounds',
            ' oz': ' ounces',
            ' ml': ' milliliters',
            ' l': ' liters',
            ' gal': ' gallons',
            'µg/m³': 'micrograms per cubic meter',
            'mg/m³': 'milligrams per cubic meter'
        }
        
        for abbr, full in units.items():
            text = text.replace(abbr, full)
        
        return text
    
    def _clean_punctuation(self, text: str) -> str:
        # Remove or replace problematic punctuation for TTS
        text = text.replace('&', ' and ')
        text = text.replace('@', ' at ')
        text = text.replace('#', ' number ')
        text = text.replace('*', ' ')
        text = text.replace('_', ' ')
        text = re.sub(r'[^\w\s\-\.,!?;:\']', ' ', text)
        return text