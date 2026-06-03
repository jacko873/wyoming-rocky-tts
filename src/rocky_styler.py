import re
import logging
from typing import Dict, Optional, List, Tuple
import os
from pathlib import Path
from .text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)

class RockyStyler:
    def __init__(self, mode: str = "rules", config: Optional[object] = None):
        self.mode = mode
        self.config = config
        
        # Initialize text normalizer
        self.text_normalizer = TextNormalizer()
        
        # Initialize OpenAI client to None
        self.openai_client = None
        self.openai_legacy = False
        
        # Contractions mapping (always drop these)
        self.contractions = {
            "i'm": "I",
            "you're": "you",
            "he's": "he",
            "she's": "she",
            "it's": "it",
            "we're": "we",
            "they're": "they",
            "i've": "I",
            "you've": "you",
            "we've": "we",
            "they've": "they",
            "i'd": "I",
            "you'd": "you",
            "he'd": "he",
            "she'd": "she",
            "we'd": "we",
            "they'd": "they",
            "i'll": "I will",
            "you'll": "you will",
            "he'll": "he will",
            "she'll": "she will",
            "we'll": "we will",
            "they'll": "they will",
            "isn't": "is no",
            "aren't": "are no",
            "wasn't": "was no",
            "weren't": "were no",
            "haven't": "have no",
            "hasn't": "has no",
            "hadn't": "had no",
            "doesn't": "does no",
            "don't": "no",
            "didn't": "did no",
            "won't": "will no",
            "wouldn't": "would no",
            "shouldn't": "should no",
            "couldn't": "could no",
            "can't": "can no",
            "cannot": "can no",
            "mustn't": "must no",
            "let's": "we",
            "that's": "that",
            "there's": "there is",
            "here's": "here is",
            "what's": "what",
            "where's": "where",
            "who's": "who",
            "how's": "how",
        }

        # Articles to drop
        self.articles = {"the", "a", "an"}

        # Auxiliary verbs to sometimes drop
        self.auxiliaries = {"is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did"}

        # Words that should be emphasized by tripling
        self.emphasis_map = {
            "amazing": "amaze amaze amaze",
            "awesome": "awesome awesome awesome",
            "terrible": "bad bad bad",
            "horrible": "bad bad bad",
            "excellent": "good good good",
            "fantastic": "good good good",
            "wonderful": "good good good",
            "great": "good good good",
            "perfect": "perfect perfect perfect",
            "beautiful": "pretty pretty pretty",
            "important": "important important important",
            "critical": "important important important",
            "essential": "important important important",
            "happy": "happy happy happy",
            "sad": "sad sad sad",
            "angry": "angry angry angry",
            "scared": "scared scared scared",
            "excited": "excite excite excite",
            "confused": "confuse confuse confuse",
            "worried": "worry worry worry",
        }

        # Common phrase replacements (before tripling)
        self.phrase_patterns = [
            # First handle compound phrases that include "successfully"
            (r"have been (turned|switched) (on|off) successfully", r"\2. Good good good"),
            (r"has been (turned|switched) (on|off) successfully", r"\2. Good good good"),
            (r"(turned|switched) (on|off) successfully", r"\2. Good good good"),
            
            # Simple replacements
            (r"hello there", "hello hello"),
            (r"thank you very much", "thank thank thank"),
            (r"thank you", "thank"),
            (r"please", ""),
            (r"excuse me", "sorry"),
            (r"i'm sorry", "sorry sorry"),
            (r"oh my god", "oh oh oh"),
            (r"oh my", "oh oh"),
            (r"what the hell", "what what"),
            (r"what on earth", "what what"),
            
            # Remove politeness markers
            (r"would you mind", "you"),
            (r"could you please", "you"),
            (r"could you", "you"),
            (r"would you", "you"),
            (r"may i", "I"),
            (r"might i", "I"),
            
            # Simplify complex phrases
            (r"in order to", "to"),
            (r"due to the fact that", "because"),
            (r"in the event that", "if"),
            (r"at this point in time", "now"),
            (r"at the present time", "now"),
            
            # Simplify formal language
            (r"utilize", "use"),
            (r"implement", "do"),
            (r"facilitate", "help"),
            (r"demonstrate", "show"),
            (r"indicate", "show"),
            (r"approximately", "about"),
            (r"regarding", "about"),
            (r"concerning", "about"),
            (r"it seems like", "maybe"),
            (r"it appears that", "maybe"),
            (r"i think that", "I think"),
            (r"i believe that", "I think"),
            (r"you know what", ""),
            (r"to be honest", ""),
            (r"basically", ""),
            (r"actually", ""),
            (r"literally", ""),
            (r"really", "very"),
            (r"extremely", "very very"),
            (r"incredibly", "very very"),
            (r"goodbye", "see you later. But I no see you later"),
            
            # Home Assistant specific
            (r"turned on successfully", "on. Good good good"),
            (r"turned off successfully", "off. Good good good"), 
            (r"switched on successfully", "on. Good good good"),
            (r"switched off successfully", "off. Good good good"),
            (r"turned on", "on"),
            (r"turned off", "off"),
            (r"switching on", "on"),
            (r"switching off", "off"),
            (r"has been turned", "now"),
            (r"has been set", "now set"),
            (r"successfully", "good good good"),
            (r"failed to", "no can"),
            (r"unable to", "no can"),
            (r"couldn't find", "no see"),
            (r"could not find", "no see"),
            (r"can't find", "no find"),
            (r"cannot find", "no find"),
            (r"not found", "no find"),
        ]
        
        if mode == "openai" and config:
            self._init_openai_safe()
    
    def _init_openai_safe(self):
        """Initialize OpenAI with better error handling"""
        try:
            import openai
        except ImportError as e:
            logger.warning(f"❌ OpenAI library not installed: {e}, falling back to rules mode")
            self.mode = "rules"
            return
        
        # Load .env file if it exists
        env_files = [
            Path.cwd() / '.env',
            Path(__file__).parent.parent / '.env',
            Path.home() / 'wyoming-rocky-tts' / '.env',
            Path('/home/rocky/wyoming-rocky-tts/.env')
        ]
        
        for env_file in env_files:
            if env_file.exists():
                logger.info(f"Loading .env file from: {env_file}")
                try:
                    with open(env_file) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                os.environ[key] = value
                                logger.info(f"Set environment variable: {key}")
                    break
                except Exception as e:
                    logger.warning(f"Error loading .env file: {e}")
        
        # Get API key
        api_key = os.getenv(self.config.openai_api_key_env if self.config else 'OPENAI_API_KEY')
        logger.info(f"OpenAI API key found: {'Yes' if api_key else 'No'}")
        
        if not api_key:
            logger.warning("❌ OpenAI API key not found, falling back to rules mode")
            self.mode = "rules"
            return
        
        # Try to initialize OpenAI client
        try:
            # Clear proxy environment variables temporarily
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                         'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy']
            saved_proxies = {}
            for var in proxy_vars:
                if var in os.environ:
                    saved_proxies[var] = os.environ[var]
                    del os.environ[var]
            
            try:
                # Try new client API without any proxy settings
                self.openai_client = openai.OpenAI(
                    api_key=api_key,
                    # Explicitly disable proxy
                    http_client=None
                )
                logger.info("✅ OpenAI client initialized (new API)")
                # Test it works
                test_response = self.openai_client.models.list()
                logger.info("✅ OpenAI client tested successfully")
            finally:
                # Restore proxy settings
                for var, value in saved_proxies.items():
                    os.environ[var] = value
                    
        except Exception as e:
            logger.info(f"Client initialization failed ({e}), setting up for fallback mode...")
            # Store the API key for fallback usage
            openai.api_key = api_key
            self.openai_legacy = True
            self.openai_client = None
            logger.info("✅ OpenAI configured for fallback mode (will create client per request)")
                
    def apply_style(self, text: str) -> str:
        """Apply Rocky styling to text."""
        if self.mode == "off":
            return text
        
        if self.mode == "openai":
            return self._apply_openai_style(text)
        
        return self._apply_rules_style(text)
    
    def _apply_rules_style(self, text: str) -> str:
        """Transform English text into Rocky's speech patterns."""
        if not text or not text.strip():
            return text
        
        # Step 1: Normalize text (numbers to words, temperatures, etc.)
        text = self.text_normalizer.normalize(text)
        
        # Step 2: Convert to lowercase for processing (preserve original for now)
        text_lower = text.lower()

        # Step 3: Apply phrase replacements
        for pattern, replacement in self.phrase_patterns:
            text_lower = re.sub(pattern, replacement, text_lower)

        # Step 4: Split into sentences and process each
        sentences = re.split(r'(?<=[.!?])\s+', text_lower)
        result = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            s = sentence.strip()
            
            # Check if this is a question
            is_question = s.endswith('?') or 'what' in s or 'where' in s or 'when' in s or 'who' in s or 'why' in s or 'how' in s

            # Process words
            words = s.split()
            new_words = []
            
            # Track which indices have been processed to avoid re-tripling
            skip_indices = set()

            for i, w in enumerate(words):
                # Clean up the word but preserve punctuation
                lower = w.lower().rstrip('.,!?;:')
                punct = w[len(lower):] if len(w) > len(lower) else ''

                # Skip if this word is already marked as part of a tripled sequence
                if i in skip_indices:
                    new_words.append(w)
                    continue

                # Handle contractions
                if lower in self.contractions:
                    new_words.append(self.contractions[lower] + punct)
                # Handle emphasis words (tripling) - only if not already tripled
                elif lower in self.emphasis_map:
                    new_words.append(self.emphasis_map[lower] + punct)
                    # Mark the added words as processed to avoid further tripling
                    added_words = self.emphasis_map[lower].split()
                    for j in range(1, len(added_words)):
                        if i + j < len(words):
                            skip_indices.add(i + j)
                # Drop articles (including at sentence start)
                elif lower in self.articles:
                    continue
                # Drop auxiliaries (but keep at sentence start and end for some constructs)
                elif lower in self.auxiliaries and i > 0 and i < len(words) - 1:
                    continue
                else:
                    new_words.append(w)

            s = ' '.join(new_words)

            # Clean up double spaces
            s = re.sub(r'\s+', ' ', s).strip()

            # Handle questions - must end with ", question?"
            if is_question:
                # Remove any existing question marks and "question" suffix to avoid duplication
                s = s.rstrip('?.,!').strip()
                if not s.lower().endswith('question'):
                    s = s + ', question?'
                else:
                    s = s + '?'

            # Capitalize first word
            if s:
                s = s[0].upper() + s[1:]

            result.append(s)

        output = ' '.join(result)

        # Final cleanup
        output = re.sub(r'\s+', ' ', output)
        output = re.sub(r'\s+([.,!?])', r'\1', output)
        output = re.sub(r'\.\.+', '.', output)

        return output.strip()
    
    def _apply_openai_style(self, text: str) -> str:
        """Apply OpenAI styling to text."""
        logger.info(f"🤖 OpenAI styling requested for: {text[:50]}...")
        
        # Check if OpenAI is available
        if not self.openai_client and not self.openai_legacy:
            logger.warning("❌ No OpenAI configuration available, using rules mode")
            return self._apply_rules_style(text)
        
        try:
            import openai
            
            if self.openai_legacy:
                # For versions where client initialization failed but we have API key
                # This means we have openai >= 1.0 but client init had issues
                # Create a temporary client just for this request
                logger.info("Using fallback OpenAI client creation...")
                
                # Clear proxies again for this request
                proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
                saved_proxies = {}
                for var in proxy_vars:
                    if var in os.environ:
                        saved_proxies[var] = os.environ.pop(var)
                
                try:
                    temp_client = openai.OpenAI(api_key=openai.api_key)
                    response = temp_client.chat.completions.create(
                        model=self.config.openai_model if self.config else "gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": self.config.rocky_style_prompt if self.config else "Transform text to sound like Rocky from Project Hail Mary"},
                            {"role": "user", "content": text}
                        ],
                        temperature=0.7,
                        max_tokens=150
                    )
                    styled = response.choices[0].message.content.strip()
                finally:
                    # Restore proxies
                    for var, value in saved_proxies.items():
                        os.environ[var] = value
            else:
                # Use new client API
                logger.info("Using new OpenAI client API...")
                response = self.openai_client.chat.completions.create(
                    model=self.config.openai_model if self.config else "gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": self.config.rocky_style_prompt if self.config else "Transform text to sound like Rocky from Project Hail Mary"},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                styled = response.choices[0].message.content.strip()
            
            logger.info(f"✅ OpenAI response: {styled[:50]}...")
            
            # Apply text normalization to OpenAI output
            normalized = self.text_normalizer.normalize(styled)
            return normalized
            
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}, falling back to rules")
            return self._apply_rules_style(text)