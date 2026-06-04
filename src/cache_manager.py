import sqlite3
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    raw_text: str
    styled_text: str
    normalized_text: str
    wav_path: str
    created_at: float
    last_used_at: float
    hit_count: int
    synthesis_duration_ms: float
    style_duration_ms: float
    total_duration_ms: float
    cache_key: str

class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                raw_text TEXT,
                styled_text TEXT,
                normalized_text TEXT,
                wav_path TEXT,
                created_at REAL,
                last_used_at REAL,
                hit_count INTEGER,
                synthesis_duration_ms REAL,
                style_duration_ms REAL,
                total_duration_ms REAL
            )
        ''')
        conn.commit()
        conn.close()
        logger.info(f"Cache database initialized at {self.db_path}")
    
    def get_cache_key(self, text: str, style_mode: str, voice_hash: str, audio_rate: int = 0) -> str:
        key_data = f"{text}:{style_mode}:{voice_hash}:{audio_rate}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, cache_key: str) -> Optional[CacheEntry]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT * FROM cache WHERE cache_key = ?", (cache_key,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Update last_used_at and hit_count
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "UPDATE cache SET last_used_at = ?, hit_count = hit_count + 1 WHERE cache_key = ?",
                (time.time(), cache_key)
            )
            conn.commit()
            conn.close()
            
            return CacheEntry(
                cache_key=row[0],
                raw_text=row[1],
                styled_text=row[2],
                normalized_text=row[3],
                wav_path=row[4],
                created_at=row[5],
                last_used_at=row[6],
                hit_count=row[7],
                synthesis_duration_ms=row[8],
                style_duration_ms=row[9],
                total_duration_ms=row[10]
            )
        return None
    
    def put(self, entry: CacheEntry):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('''
            INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.cache_key,
            entry.raw_text,
            entry.styled_text,
            entry.normalized_text,
            entry.wav_path,
            entry.created_at,
            entry.last_used_at,
            entry.hit_count,
            entry.synthesis_duration_ms,
            entry.style_duration_ms,
            entry.total_duration_ms
        ))
        conn.commit()
        conn.close()
        logger.debug(f"Cached entry: {entry.cache_key}")
    
    def delete(self, cache_key: str) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT wav_path FROM cache WHERE cache_key = ?", (cache_key,)
        )
        row = cursor.fetchone()
        
        if row:
            wav_path = row[0]
            conn.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
            conn.commit()
            
            # Delete the WAV file
            try:
                Path(wav_path).unlink()
            except:
                pass
            
            conn.close()
            return True
        
        conn.close()
        return False
    
    def clear(self):
        conn = sqlite3.connect(str(self.db_path))
        
        # Get all WAV paths before clearing
        cursor = conn.execute("SELECT wav_path FROM cache")
        wav_paths = [row[0] for row in cursor.fetchall()]
        
        # Clear database
        conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
        
        # Remove WAV files
        for wav_path in wav_paths:
            try:
                Path(wav_path).unlink()
            except:
                pass
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        
        stats = {}
        
        # Total entries
        cursor = conn.execute("SELECT COUNT(*) FROM cache")
        stats['total_entries'] = cursor.fetchone()[0]
        
        # Total hits
        cursor = conn.execute("SELECT SUM(hit_count) FROM cache")
        stats['total_hits'] = cursor.fetchone()[0] or 0
        
        # Average synthesis time
        cursor = conn.execute("SELECT AVG(synthesis_duration_ms) FROM cache")
        stats['avg_synthesis_ms'] = cursor.fetchone()[0] or 0
        
        # Cache size
        cache_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.wav") if f.is_file())
        stats['cache_size_mb'] = cache_size / (1024 * 1024)
        
        conn.close()
        return stats
    
    def get_top_entries(self, limit: int = 10) -> List[dict]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute("""
            SELECT cache_key, raw_text, hit_count, created_at, last_used_at
            FROM cache 
            ORDER BY hit_count DESC 
            LIMIT ?
        """, (limit,))
        
        entries = []
        for row in cursor.fetchall():
            entries.append({
                'cache_key': row[0],
                'raw_text': row[1],
                'hit_count': row[2],
                'created_at': row[3],
                'last_used_at': row[4]
            })
        
        conn.close()
        return entries
    
    def cleanup_old(self, max_age_days: int = 30):
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        conn = sqlite3.connect(str(self.db_path))
        
        # Get old entries
        cursor = conn.execute(
            "SELECT cache_key, wav_path FROM cache WHERE last_used_at < ?",
            (cutoff_time,)
        )
        old_entries = cursor.fetchall()
        
        # Delete old entries
        conn.execute("DELETE FROM cache WHERE last_used_at < ?", (cutoff_time,))
        conn.commit()
        conn.close()
        
        # Delete old WAV files
        for cache_key, wav_path in old_entries:
            try:
                Path(wav_path).unlink()
            except:
                pass
        
        logger.info(f"Cleaned up {len(old_entries)} old cache entries")