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
        
        # Step 8: Clean up hyphens in numbers for TTS
        text = self._clean_number_hyphens(text)
        
        # Step 9: Clean up extra spaces
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
            period = match.group(3)
            
            # Split period into individual letters for TTS
            if period:
                period_formatted = ' '.join(period.upper())
                
            if minute == "00":
                return f"{hour} {period_formatted}".strip() if period else hour
            else:
                return f"{hour} {minute} {period_formatted}".strip() if period else f"{hour} {minute}"
        
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
        # Use regex with word boundaries for safer replacement
        units = [
            (r'\bmph\b', 'miles per hour'),
            (r'\bkph\b', 'kilometers per hour'),
            (r'\bkmh\b', 'kilometers per hour'),
            (r'\bft\b', 'feet'),
            (r'\bm\b', 'meters'),
            (r'\bkm\b', 'kilometers'),
            (r'\bmi\b', 'miles'),
            (r'\bkg\b', 'kilograms'),
            (r'\blb\b', 'pounds'),
            (r'\blbs\b', 'pounds'),
            (r'\boz\b', 'ounces'),
            (r'\bml\b', 'milliliters'),
            (r'\bl\b', 'liters'),
            (r'\bgal\b', 'gallons'),
            (r'µg/m³', 'micrograms per cubic meter'),
            (r'mg/m³', 'milligrams per cubic meter')
        ]
        
        for pattern, replacement in units:
            text = re.sub(pattern, replacement, text)
        
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
    
    def _clean_number_hyphens(self, text: str) -> str:
        # Remove hyphens from number words for better TTS pronunciation
        number_words = [
            'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety',
            'hundred', 'thousand', 'million', 'billion'
        ]
        
        for word in number_words:
            # Replace hyphenated versions with spaced versions
            text = re.sub(f'{word}-', f'{word} ', text)
        
        return text