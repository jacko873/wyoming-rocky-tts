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
        overrides_file = None
        if config and hasattr(config, 'overrides_file'):
            overrides_file = Path(config.overrides_file)
        elif config and hasattr(config, 'data_dir'):
            overrides_file = Path(config.data_dir) / "overrides.yaml"
        
        self.text_normalizer = TextNormalizer(overrides_file)
        
        # Articles and auxiliaries to strip
        self.articles = {'a', 'an', 'the'}
        self.auxiliaries = {'is', 'are', 'was', 'were', 'will', 'would', 'should', 'could',
                           'do', 'does', 'did', 'has', 'have', 'had', 'am', 'been', 'being'}
        
        # Contractions mapping
        self.contractions = {
            "i'm": "I",
            "i've": "I", 
            "i'll": "I",
            "i'd": "I",
            "you're": "you",
            "you've": "you",
            "you'll": "you",
            "we're": "we",
            "we've": "we",
            "we'll": "we",
            "they're": "they",
            "they've": "they",
            "they'll": "they",
            "he's": "he",
            "she's": "she",
            "it's": "it",
            "that's": "that",
            "there's": "there",
            "what's": "what",
            "don't": "no",
            "doesn't": "no",
            "didn't": "no",
            "can't": "no can",
            "cannot": "no can",
            "won't": "no will",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "haven't": "no have",
            "hasn't": "no have",
            "hadn't": "no have",
        }
        
        # Emphasis words that get tripled
        self.emphasis_map = {
            'amazing': 'amaze amaze amaze',
            'wonderful': 'amaze amaze amaze',
            'incredible': 'amaze amaze amaze',
            'fantastic': 'amaze amaze amaze',
            'excellent': 'good good good',
            'great': 'good good good',
            'perfect': 'good good good',
            'terrible': 'bad bad bad',
            'awful': 'bad bad bad',
            'horrible': 'bad bad bad',
            'happy': 'happy happy happy',
            'excited': 'happy happy happy',
            'sad': 'sad sad sad',
            'upset': 'sad sad sad',
            'sorry': 'sorry sorry sorry',
            'angry': 'angry angry angry',
            'furious': 'angry angry angry',
            'confused': 'confuse confuse confuse',
            'scared': 'scared scared scared',
            'afraid': 'scared scared scared',
            'dangerous': 'danger danger danger',
            'important': 'important important important',
            'interesting': 'interesting interesting interesting',
            'absolutely': 'yes yes yes',
            'definitely': 'yes yes yes',
            'certainly': 'yes yes yes',
            'impossible': 'no can. No no no',
            'unfortunately': 'sad sad sad',
            'good': 'good good good',
            'bad': 'bad bad bad',
        }
        
        # Common phrase replacements (applied first)
        self.phrase_patterns = [
            (r"i don'?t understand", "no understand"),
            (r"i do not understand", "no understand"),
            (r"i don'?t know", "I not know"),
            (r"what do you mean", "what mean"),
            (r"what does that mean", "what mean"),
            (r"what does .+ mean", "what mean"),
            (r"i need a word for", "need word"),
            (r"i'?m going to", "I"),
            (r"going to\s+", ""),
            (r"want to\s+", "want "),
            (r"need to\s+", "need "),
            (r"have to\s+", "must "),
            (r"try to\s+", "try "),
            (r"\bable to\s+", "can "),
            (r"in order to\s+", "to "),
            (r"because of\s+", "because "),
            (r"a lot of\s+", "many "),
            (r"lots of\s+", "many "),
            (r"kind of\s+", ""),
            (r"sort of\s+", ""),
            (r"right now", "now"),
            (r"at this point", "now"),
            (r"at the moment", "now"),
            (r"as well", "also"),
            (r"in addition", "also"),
            (r"however", "but"),
            (r"therefore", "so"),
            (r"nevertheless", "but"),
            (r"furthermore", "also"),
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
            self._init_openai()
    
    def _init_openai(self):
        try:
            import openai
            api_key = os.getenv(self.config.openai_api_key_env)
            logger.info(f"OpenAI initialization - looking for env var: {self.config.openai_api_key_env}")
            logger.info(f"OpenAI API key found: {'Yes' if api_key else 'No'}")
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai.OpenAI()
                logger.info("✅ OpenAI client initialized successfully")
            else:
                logger.warning(f"❌ OpenAI API key not found in environment variable '{self.config.openai_api_key_env}', falling back to rules mode")
                self.mode = "rules"
        except ImportError as e:
            logger.warning(f"❌ OpenAI library not installed: {e}, falling back to rules mode")
            self.mode = "rules"
    
    def apply_style(self, text: str) -> str:
        """Apply Rocky styling to text. 
        
        Both rules and OpenAI modes include text normalization 
        (numbers to words, temperature symbols, etc.)
        """
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

        # Step 2: Work sentence by sentence
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        result = []

        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue

            # Detect if it's a question
            is_question = (
                s.endswith('?') or
                any(s.lower().startswith(q) for q in ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'whose',
                                                       'would', 'could', 'should', 'can', 'will', 'do', 'does', 'did',
                                                       'are', 'is', 'was', 'were', 'have', 'has', 'may', 'might'])
            )

            # Apply phrase-level replacements first (case insensitive)
            for pattern, replacement in self.phrase_patterns:
                s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

            # Expand contractions and apply emphasis, drop articles and auxiliaries
            words = s.split()
            new_words = []
            
            # Track which words are part of existing tripled sequences
            skip_indices = set()
            
            # Pre-scan for existing tripled patterns to avoid re-tripling
            for i in range(len(words) - 2):
                word1 = words[i].lower().rstrip('.,!?;:')
                word2 = words[i+1].lower().rstrip('.,!?;:')
                word3 = words[i+2].lower().rstrip('.,!?;:')
                
                if word1 == word2 == word3:
                    # Mark all three as already tripled
                    skip_indices.update([i, i+1, i+2])
            
            for i, w in enumerate(words):
                # Extract punctuation
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
        logger.info(f"🤖 OpenAI styling requested for: {text[:50]}...")
        
        if not hasattr(self, 'openai_client'):
            logger.warning("❌ No OpenAI client available, using rules mode")
            return self._apply_rules_style(text)
        
        try:
            logger.info(f"📡 Calling OpenAI {self.config.openai_model} API...")
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": self.config.rocky_style_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            styled = response.choices[0].message.content.strip()
            logger.info(f"✅ OpenAI response: {text[:30]}... -> {styled[:50]}...")
            
            # Apply text normalization to OpenAI output (numbers to words, etc.)
            normalized = self.text_normalizer.normalize(styled)
            logger.info(f"🔧 Normalized: {styled[:30]}... -> {normalized[:50]}...")
            
            return normalized
            
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}, falling back to rules")
            return self._apply_rules_style(text)