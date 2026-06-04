#!/usr/bin/env python3

import asyncio
import io
import logging
import argparse
import os
import sys
import time
import tempfile
import subprocess
import wave
from functools import partial
from pathlib import Path
from typing import Optional
import threading

import torch
from TTS.api import TTS

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.server import AsyncServer, AsyncEventHandler
from wyoming.info import Describe, Info, Attribution, TtsProgram, TtsVoice
from wyoming.tts import Synthesize

from .text_normalizer import TextNormalizer
from .rocky_styler import RockyStyler
from .cache_manager import CacheManager, CacheEntry
from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RockyTTS:
    def __init__(self, config: Config):
        self.config = config
        self.speaker_wav = Path(config.speaker_wav)
        self.cache_dir = Path(config.cache_dir)
        self.data_dir = Path(config.data_dir)
        
        self.normalizer = TextNormalizer(self.data_dir / "overrides.yaml")
        self.styler = RockyStyler(config.style_mode, config)
        self.cache = CacheManager(self.cache_dir) if config.cache_enabled else None
        
        logger.info("Loading YourTTS model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = TTS(config.model_name).to(self.device)
        logger.info(f"Model loaded on {self.device}")
        
        self.synthesis_lock = threading.Lock()
        self.voice_hash = self._compute_voice_hash()
        
        self._warmup()
    
    def _compute_voice_hash(self) -> str:
        import hashlib
        if self.speaker_wav.exists():
            with open(self.speaker_wav, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        return "default"
    
    def _warmup(self):
        logger.info("Warming up model...")
        try:
            self.synthesize(self.config.warmup_text, use_cache=False)
            logger.info("Warmup complete")
        except Exception as e:
            logger.error(f"Warmup failed: {e}")
    
    def synthesize(self, text: str, use_cache: bool = True) -> bytes:
        start_time = time.time()
        
        style_start = time.time()
        styled_text = self.styler.apply_style(text)
        style_duration = (time.time() - style_start) * 1000
        
        normalized_text = self.normalizer.normalize(styled_text)
        
        cache_key = None
        if self.cache and use_cache:
            cache_key = self.cache.get_cache_key(text, self.config.style_mode, self.voice_hash)
            cached = self.cache.get(cache_key)
            if cached and Path(cached.wav_path).exists():
                logger.info(f"Cache hit for: {text[:50]}...")
                with open(cached.wav_path, 'rb') as f:
                    return f.read()
        
        logger.info(f"Synthesizing: {normalized_text[:100]}...")
        
        with self.synthesis_lock:
            synth_start = time.time()
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_raw:
                raw_path = tmp_raw.name
                
                self.tts.tts_to_file(
                    text=normalized_text,
                    file_path=raw_path,
                    speaker_wav=str(self.speaker_wav),
                    language="en"
                )
                
                synth_duration = (time.time() - synth_start) * 1000
        
        output_path = self.cache_dir / f"{cache_key}.wav" if cache_key else Path(tempfile.mktemp(suffix='.wav'))
        self._process_audio(raw_path, output_path)
        
        try:
            os.unlink(raw_path)
        except:
            pass
        
        with open(output_path, 'rb') as f:
            audio_data = f.read()
        
        if self.cache and use_cache and cache_key:
            entry = CacheEntry(
                raw_text=text,
                styled_text=styled_text,
                normalized_text=normalized_text,
                wav_path=str(output_path),
                created_at=time.time(),
                last_used_at=time.time(),
                hit_count=1,
                synthesis_duration_ms=synth_duration,
                style_duration_ms=style_duration,
                total_duration_ms=(time.time() - start_time) * 1000,
                cache_key=cache_key
            )
            self.cache.put(entry)
        
        logger.info(f"Synthesis complete in {(time.time() - start_time)*1000:.0f}ms")
        return audio_data
    
    def _process_audio(self, input_path: str, output_path: Path):
        try:
            cmd = [
                'ffmpeg', '-y', '-i', input_path,
                '-af', self.config.ffmpeg_filters,
                '-ar', str(self.config.audio_rate),
                '-ac', '1',
                '-c:a', 'pcm_s16le',
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"FFmpeg processing failed: {e}, using raw audio")
            # Copy raw audio as fallback
            import shutil
            shutil.copy2(input_path, output_path)

class RockyWyomingHandler(AsyncEventHandler):
    def __init__(self, wyoming_info: Info, tts: RockyTTS, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self.tts = tts

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            return True

        if Synthesize.is_type(event.type):
            synthesize = Synthesize.from_event(event)
            text = synthesize.text.strip()

            if not text:
                return True

            try:
                # Run blocking synthesis off the event loop
                loop = asyncio.get_running_loop()
                audio_data = await loop.run_in_executor(None, self.tts.synthesize, text)
            except Exception as e:
                logger.error(f"Synthesis error: {e}")
                return False

            # Stream the WAV back as Wyoming audio events
            with wave.open(io.BytesIO(audio_data), 'rb') as wav:
                rate = wav.getframerate()
                width = wav.getsampwidth()
                channels = wav.getnchannels()

                await self.write_event(
                    AudioStart(rate=rate, width=width, channels=channels).event()
                )

                frames = wav.readframes(1024)
                while frames:
                    await self.write_event(
                        AudioChunk(rate=rate, width=width, channels=channels, audio=frames).event()
                    )
                    frames = wav.readframes(1024)

            await self.write_event(AudioStop().event())
            return True

        return True

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path,
                       default=Path.home() / '.rocky_tts' / 'config.yaml')
    parser.add_argument('--host', default=None)
    parser.add_argument('--port', type=int, default=None)

    args = parser.parse_args()

    config = Config.load(args.config)

    if args.host:
        config.wyoming_host = args.host
    if args.port:
        config.wyoming_port = args.port

    tts = RockyTTS(config)

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="Rocky TTS",
                description="Rocky-style YourTTS voice",
                version="1.0",
                attribution=Attribution(
                    name="Rocky TTS",
                    url="https://github.com/jacko873/wyoming-rocky-tts"
                ),
                installed=True,
                voices=[
                    TtsVoice(
                        name="rocky",
                        description="Rocky alien helper voice",
                        version="1.0",
                        attribution=Attribution(
                            name="Rocky",
                            url="https://github.com/jacko873/wyoming-rocky-tts"
                        ),
                        installed=True,
                        languages=["en"]
                    )
                ]
            )
        ]
    )

    logger.info(f"Starting Wyoming server on {config.wyoming_host}:{config.wyoming_port}")
    server = AsyncServer.from_uri(f"tcp://{config.wyoming_host}:{config.wyoming_port}")

    await server.run(partial(RockyWyomingHandler, wyoming_info, tts))

if __name__ == '__main__':
    asyncio.run(main())