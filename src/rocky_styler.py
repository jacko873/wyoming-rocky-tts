import re
import logging
from typing import Dict, Optional
import os

logger = logging.getLogger(__name__)

class RockyStyler:
    def __init__(self, mode: str = "rules", config: Optional[object] = None):
        self.mode = mode
        self.config = config
        self.rules = self._load_rules()
        
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
    
    def _load_rules(self) -> Dict[str, str]:
        return {
            # Basic conversions
            "turned on": "on. Good good good",
            "turned off": "off. Good good good",
            "switching on": "on. Good good good",
            "switching off": "off. Good good good",
            "done": "Done. Good good good",
            "completed": "Complete. Good good good",
            "finished": "Finish. Good good good",
            
            # Negatives
            "i can't": "I no can",
            "i cannot": "I no can",
            "i couldn't": "I no could",
            "i don't": "I no",
            "i do not": "I no",
            "i didn't": "I no did",
            "i won't": "I no will",
            "i will not": "I no will",
            "it's not": "It no",
            "it is not": "It no",
            "that's not": "That no",
            "that is not": "That no",
            
            # Finding/seeing
            "couldn't find": "no see",
            "could not find": "no see",
            "can't find": "no find",
            "cannot find": "no find",
            "unable to find": "no find",
            "unable to locate": "no find",
            "not found": "no find",
            
            # Understanding
            "i couldn't understand": "I no understand. Try again, question",
            "i don't understand": "I no understand. Try again, question",
            "didn't understand": "no understand. Try again, question",
            "not sure what you mean": "No sure what mean, question",
            "what do you mean": "What mean, question",
            
            # Emotions
            "that's amazing": "That amaze amaze amaze",
            "that's great": "That good good good",
            "that's terrible": "That bad bad bad",
            "that's scary": "That scary scary scary",
            "i'm happy": "I happy happy happy",
            "sorry": "Sorry sorry sorry",
            
            # Common Home Assistant responses
            "the lights are": "Lights",
            "the light is": "Light",
            "has been turned": "now",
            "has been set": "now set",
            "successfully": "good good good ",
            "failed to": "no can",
            "unable to": "no can",
            
            # Requests
            "would you like": "You want",
            "do you want": "You want",
            "should i": "I should",
            "can you": "You can",
            "could you": "You could",
            "will you": "You will",
        }
    
    def apply_style(self, text: str) -> str:
        if self.mode == "off":
            return text
        
        if self.mode == "openai":
            return self._apply_openai_style(text)
        
        return self._apply_rules_style(text)
    
    def _apply_rules_style(self, text: str) -> str:
        styled = text.lower()
        
        # Apply transformation rules
        for pattern, replacement in self.rules.items():
            styled = styled.replace(pattern, replacement)
        
        # Handle questions - add ", question?" if it's a question
        question_starters = [
            "what", "why", "how", "when", "where", "who", 
            "would", "could", "should", "can", "will", "do you", 
            "are you", "is it", "is there", "is that"
        ]
        
        if any(styled.startswith(q) for q in question_starters):
            if not styled.endswith("?") and not styled.endswith("question"):
                styled = styled.rstrip(".!") + ", question?"
        
        # Simplify grammar patterns
        styled = self._simplify_grammar(styled)
        
        # Add emphasis through repetition for certain words
        styled = self._add_emphasis(styled)
        
        # Capitalize first letter
        if styled:
            styled = styled[0].upper() + styled[1:]
        
        return styled
    
    def _simplify_grammar(self, text: str) -> str:
        # Remove articles where it still makes sense
        text = re.sub(r'\b(the|a|an)\s+', '', text)
        
        # Simplify "is/are" constructions
        text = text.replace(" is now ", " now ")
        text = text.replace(" are now ", " now ")
        text = text.replace(" was ", " ")
        text = text.replace(" were ", " ")
        
        # Simplify verb forms
        text = text.replace("going to", "gonna")
        text = text.replace("want to", "wanna")
        
        return text
    
    def _add_emphasis(self, text: str) -> str:
        emphasis_words = {
            "good": "good good good",
            "bad": "bad bad bad",
            "happy": "happy happy happy",
            "sad": "sad sad sad",
            "scary": "scary scary scary",
            "amaze": "amaze amaze amaze",
            "wow": "wow wow wow",
            "yes": "yes yes yes",
            "no": "no no no"
        }
        
        for word, emphasized in emphasis_words.items():
            # Only emphasize standalone words, not parts of other words
            text = re.sub(r'\b' + word + r'\b(?! ' + word + r')', emphasized, text)
        
        return text
    
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