import re
import logging
from typing import Dict, Optional, List, Tuple
import os

logger = logging.getLogger(__name__)

class RockyStyler:
    def __init__(self, mode: str = "rules", config: Optional[object] = None):
        self.mode = mode
        self.config = config
        
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
            (r"able to\s+", "can "),
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
            (r"turned on", "on. Good good good"),
            (r"turned off", "off. Good good good"),
            (r"switching on", "on. Good good good"),
            (r"switching off", "off. Good good good"),
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
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai.OpenAI()
            else:
                logger.warning("OpenAI API key not found, falling back to rules mode")
                self.mode = "rules"
        except ImportError:
            logger.warning("OpenAI library not installed, falling back to rules mode")
            self.mode = "rules"
    
    def apply_style(self, text: str) -> str:
        if self.mode == "off":
            return text
        
        if self.mode == "openai":
            return self._apply_openai_style(text)
        
        return self._apply_rules_style(text)
    
    def _apply_rules_style(self, text: str) -> str:
        """Transform English text into Rocky's speech patterns."""
        if not text or not text.strip():
            return text

        # Work sentence by sentence
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
            
            for i, w in enumerate(words):
                # Extract punctuation
                lower = w.lower().rstrip('.,!?;:')
                punct = w[len(lower):] if len(w) > len(lower) else ''

                # Handle contractions
                if lower in self.contractions:
                    new_words.append(self.contractions[lower] + punct)
                # Handle emphasis words (tripling)
                elif lower in self.emphasis_map:
                    new_words.append(self.emphasis_map[lower] + punct)
                # Drop articles
                elif lower in self.articles:
                    continue
                # Drop auxiliaries (but keep at sentence start for some constructs)
                elif lower in self.auxiliaries and i > 0:
                    continue
                else:
                    new_words.append(w)

            s = ' '.join(new_words)

            # Clean up double spaces
            s = re.sub(r'\s+', ' ', s).strip()

            # Handle questions - must end with ", question?"
            if is_question and 'question' not in s.lower():
                s = s.rstrip('?.,!').strip() + ', question?'
            elif is_question:
                # Already has "question" - ensure it ends with ?
                s = s.rstrip('?').strip() + '?'

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
        if not hasattr(self, 'openai_client'):
            return self._apply_rules_style(text)
        
        try:
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
            logger.info(f"OpenAI style applied: {text[:50]}... -> {styled[:50]}...")
            return styled
            
        except Exception as e:
            logger.error(f"OpenAI styling failed: {e}, falling back to rules")
            return self._apply_rules_style(text)