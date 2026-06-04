import yaml
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Config:
    # Wyoming settings
    wyoming_host: str = "0.0.0.0"
    wyoming_port: int = 10202
    
    # Web UI settings
    web_host: str = "0.0.0.0"
    web_port: int = 8088
    
    # Paths
    speaker_wav: str = str(Path.home() / ".rocky_tts" / "rocky_reference.wav")
    data_dir: str = str(Path.home() / ".rocky_tts")
    cache_dir: str = "/var/cache/wyoming-rocky"
    
    # TTS settings
    model_name: str = "tts_models/multilingual/multi-dataset/your_tts"
    cache_enabled: bool = True
    warmup_text: str = "System ready"
    
    # Style settings
    style_mode: str = "rules"  # off, rules, openai
    
    # OpenAI settings
    openai_model: str = "gpt-4o-mini"
    openai_api_key_env: str = "OPENAI_API_KEY"
    rocky_style_prompt: str = """Rewrite the assistant response below into the voice of a cheerful, loyal alien house companion (inspired by Rocky from Project Hail Mary, but never claim to be the copyrighted character).

Hard rules:
- Do not add facts. Do not remove important facts.
- Do not change device names, room names, numbers, times, or action results.
- Keep it short and easy to speak aloud. Output only the rewritten spoken text.

Voice rules:
- Short, clear sentences with simplified grammar. Drop articles like "the", "a", "an" when still clear.
- Repeat words for emphasis: "good good good", "bad bad bad", "amaze amaze amaze", "happy happy happy", "danger danger danger".
- Questions end with "question?"
- Simple emotional reactions: "Amaze!", "Good!", "Bad!", "Scary!", "Happy!"
- Warm, excited, loyal, practical. Excited when systems work.

Examples:
- "I do not understand" -> "I no understand."
- "What do you mean?" -> "What mean, question?"
- "That is really amazing" -> "That amaze amaze amaze."
- "The living room lights are now on" -> "Living room lights on. Good good good."
- "Would you like me to do that?" -> "You want me do this, question?"
- "I cannot see that device" -> "I no see that device."
- "Traffic is slow, leave earlier" -> "Traffic slow slow slow. Leave earlier.\""""
    
    # Audio settings
    audio_rate: int = 22050
    ffmpeg_filters: str = "highpass=f=80,lowpass=f=8000,compand,loudnorm=I=-16:TP=-1.5:LRA=11"
    
    # Processing settings
    max_text_length: int = 500
    normalize_numbers: bool = True
    normalize_units: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    @classmethod
    def load(cls, config_path: Path) -> "Config":
        config = cls()
        
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
                
                # Update config with loaded values
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
        
        # Override with environment variables
        env_mappings = {
            "ROCKY_WYOMING_HOST": "wyoming_host",
            "ROCKY_WYOMING_PORT": "wyoming_port",
            "ROCKY_WEB_HOST": "web_host",
            "ROCKY_WEB_PORT": "web_port",
            "ROCKY_STYLE_MODE": "style_mode",
            "ROCKY_SPEAKER_WAV": "speaker_wav",
            "ROCKY_CACHE_DIR": "cache_dir",
            "ROCKY_DATA_DIR": "data_dir",
        }
        
        for env_key, config_key in env_mappings.items():
            if env_value := os.getenv(env_key):
                if config_key.endswith("_port"):
                    setattr(config, config_key, int(env_value))
                else:
                    setattr(config, config_key, env_value)
        
        return config
    
    def save(self, config_path: Path):
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)